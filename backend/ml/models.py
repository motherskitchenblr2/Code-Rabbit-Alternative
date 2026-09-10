# =============================================================================
# Git-Fix ML Models - Fine-tuned Code Review Models
# =============================================================================
# Custom ML models for code review using fine-tuned transformers
# =============================================================================

import os
import json
import logging
from typing import Optional, List, Dict, Any, Tuple
from dataclasses import dataclass, field
from pathlib import Path
import torch
import torch.nn as nn
from torch.utils.data import Dataset, DataLoader
from transformers import (
    AutoModel,
    AutoTokenizer,
    AutoModelForSequenceClassification,
    AutoModelForTokenClassification,
    Trainer,
    TrainingArguments,
    EarlyStoppingCallback,
)
from transformers.modeling_outputs import SequenceClassifierOutput, TokenClassifierOutput
import numpy as np
from sklearn.metrics import accuracy_score, precision_recall_fscore_support, roc_auc_score

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for fine-tuned models."""
    model_name: str = "microsoft/codebert-base"
    max_length: int = 512
    num_labels: int = 5  # critical, high, medium, low, info
    learning_rate: float = 2e-5
    batch_size: int = 16
    num_epochs: int = 3
    warmup_steps: int = 500
    weight_decay: float = 0.01
    gradient_accumulation_steps: int = 4
    fp16: bool = True
    output_dir: str = "./models/code-review"
    logging_steps: int = 100
    eval_steps: int = 500
    save_steps: int = 1000
    eval_strategy: str = "steps"
    save_strategy: str = "steps"
    load_best_model_at_end: bool = True
    metric_for_best_model: str = "f1"
    greater_is_better: bool = True
    seed: int = 42
    dataloader_num_workers: int = 4
    remove_unused_columns: bool = False


@dataclass
class CodeSample:
    """Represents a code sample for training/inference."""
    code: str
    language: str
    file_path: str
    labels: Optional[List[Dict[str, Any]]] = None  # For training
    vulnerability_type: Optional[str] = None
    severity: Optional[str] = None
    line_start: Optional[int] = None
    line_end: Optional[int] = None
    suggested_fix: Optional[str] = None
    confidence: Optional[float] = None


class CodeReviewDataset(Dataset):
    """Dataset for code review training."""
    
    def __init__(
        self,
        samples: List[CodeSample],
        tokenizer,
        max_length: int = 512,
        label2id: Optional[Dict[str, int]] = None,
    ):
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_length = max_length
        self.label2id = label2id or {
            "critical": 0,
            "high": 1,
            "medium": 2,
            "low": 3,
            "info": 4,
        }
        self.id2label = {v: k for k, v in self.label2id.items()}
    
    def __len__(self) -> int:
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        sample = self.samples[idx]
        
        # Create input text with context
        text = self._prepare_input(sample)
        
        encoding = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
        )
        
        item = {key: val.squeeze(0) for key, val in encoding.items()}
        
        # Add labels if available
        if sample.labels:
            # For sequence classification - use highest severity
            max_severity = max(sample.labels, key=lambda x: self._severity_weight(x.get("severity", "info")))
            label = self.label2id.get(max_severity.get("severity", "info"), 4)
            item["labels"] = torch.tensor(label, dtype=torch.long)
        elif sample.severity:
            item["labels"] = torch.tensor(
                self.label2id.get(sample.severity, 4),
                dtype=torch.long,
            )
        
        return item
    
    def _prepare_input(self, sample: CodeSample) -> str:
        """Prepare input text with context."""
        parts = []
        
        if sample.language:
            parts.append(f"Language: {sample.language}")
        
        if sample.file_path:
            parts.append(f"File: {sample.file_path}")
        
        if sample.vulnerability_type:
            parts.append(f"Type: {sample.vulnerability_type}")
        
        parts.append(f"Code:\n{sample.code}")
        
        return "\n\n".join(parts)
    
    def _severity_weight(self, severity: str) -> int:
        weights = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
        return weights.get(severity.lower(), 1)


class VulnerabilityDetectionDataset(Dataset):
    """Dataset for token-level vulnerability detection."""
    
    def __init__(
        self,
        samples: List[CodeSample],
        tokenizer,
        max_length: int = 512,
    ):
        self.samples = samples
        self.tokenizer = tokenizer
        self.max_length = max_length
    
    def __len__(self) -> int:
        return len(self.samples)
    
    def __getitem__(self, idx: int) -> Dict[str, torch.Tensor]:
        sample = self.samples[idx]
        
        text = sample.code
        
        encoding = self.tokenizer(
            text,
            truncation=True,
            max_length=self.max_length,
            padding="max_length",
            return_tensors="pt",
            return_offsets_mapping=True,
        )
        
        item = {key: val.squeeze(0) for key, val in encoding.items()}
        item.pop("offset_mapping")  # Remove offsets mapping
        
        # Create token-level labels if available
        if sample.labels:
            labels = self._create_token_labels(sample, encoding["offset_mapping"][0])
            item["labels"] = torch.tensor(labels, dtype=torch.long)
        
        return item
    
    def _create_token_labels(self, sample: CodeSample, offset_mapping) -> List[int]:
        """Create token-level labels for vulnerability spans."""
        labels = [0] * len(offset_mapping)  # 0 = no vulnerability
        
        if not sample.labels:
            return labels
        
        for label in sample.labels:
            start_line = label.get("line_start", 0)
            end_line = label.get("line_end", 0)
            severity = label.get("severity", "info")
            
            # Map severity to label
            severity_map = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
            label_id = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}.get(
                label.get("severity", "info").lower(), 1
            )
            
            # Find token positions corresponding to vulnerable lines
            # This is simplified - in practice you'd need more sophisticated mapping
            pass
        
        return [0] * len(offset_mapping)  # Placeholder


class CodeReviewClassifier(nn.Module):
    """Code review classification model."""
    
    def __init__(self, config: ModelConfig):
        super().__init__()
        self.config = config
        self.num_labels = config.num_labels
        
        # Load pre-trained model
        self.encoder = AutoModel.from_pretrained(config.model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(config.model_name)
        
        # Classification head
        self.dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(self.encoder.config.hidden_size, config.num_labels)
        
        # Loss function
        self.loss_fct = nn.CrossEntropyLoss()
    
    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        labels: Optional[torch.Tensor] = None,
    ) -> SequenceClassifierOutput:
        outputs = self.encoder(
            input_ids=input_ids,
            attention_mask=attention_mask,
        )
        
        # Use [CLS] token representation
        pooled_output = outputs.last_hidden_state[:, 0]
        pooled_output = self.dropout(pooled_output)
        logits = self.classifier(pooled_output)
        
        loss = None
        if labels is not None:
            loss = self.loss_fct(logits.view(-1, self.num_labels), labels.view(-1))
        
        return SequenceClassifierOutput(
            loss=loss,
            logits=logits,
            hidden_states=outputs.hidden_states,
            attentions=outputs.attentions,
        )
    
    def predict(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Run inference on code."""
        self.eval()
        with torch.no_grad():
            # Prepare input
            text = f"Language: {language}\n\nCode:\n{code}"
            encoding = self.tokenizer(
                text,
                truncation=True,
                max_length=self.config.max_length,
                padding="max_length",
                return_tensors="pt",
            )
            
            outputs = self.forward(
                input_ids=encoding["input_ids"],
                attention_mask=encoding["attention_mask"],
            )
            
            probs = torch.softmax(outputs.logits, dim=-1)
            pred_id = torch.argmax(probs, dim=-1).item()
            
            id2label = {0: "critical", 1: "high", 2: "medium", 3: "low", 4: "info"}
            
            return {
                "severity": id2label.get(pred_id, "info"),
                "confidence": probs[0][pred_id].item(),
                "probabilities": {
                    id2label[i]: probs[0][i].item() 
                    for i in range(self.num_labels)
                },
            }


class VulnerabilityDetector(nn.Module):
    """Token-level vulnerability detection model."""
    
    def __init__(self, config: ModelConfig):
        super().__init__()
        self.config = config
        
        # Load pre-trained model
        self.encoder = AutoModel.from_pretrained(config.model_name)
        self.tokenizer = AutoTokenizer.from_pretrained(config.model_name)
        
        # Token classification head
        self.dropout = nn.Dropout(0.1)
        self.classifier = nn.Linear(self.encoder.config.hidden_size, 6)  # 0=none, 1-5 severity
        
        self.loss_fct = nn.CrossEntropyLoss(ignore_index=-100)
    
    def forward(
        self,
        input_ids: torch.Tensor,
        attention_mask: Optional[torch.Tensor] = None,
        labels: Optional[torch.Tensor] = None,
    ) -> TokenClassifierOutput:
        outputs = self.encoder(
            input_ids=input_ids,
            attention_mask=attention_mask,
        )
        
        sequence_output = outputs.last_hidden_state
        sequence_output = self.dropout(sequence_output)
        logits = self.classifier(sequence_output)
        
        loss = None
        if labels is not None:
            loss = self.loss_fct(logits.view(-1, 6), labels.view(-1))
        
        return TokenClassifierOutput(
            loss=loss,
            logits=logits,
            hidden_states=outputs.hidden_states,
            attentions=outputs.attentions,
        )


class CodeReviewModelTrainer:
    """Trainer for fine-tuning code review models."""
    
    def __init__(self, config: ModelConfig):
        self.config = config
        self.model = None
        self.tokenizer = None
        self.trainer = None
    
    def load_model(self, model_path: Optional[str] = None):
        """Load pre-trained or fine-tuned model."""
        model_name = model_path or self.config.model_name
        
        self.tokenizer = AutoTokenizer.from_pretrained(self.config.model_name)
        if self.tokenizer.pad_token is None:
            self.tokenizer.pad_token = self.tokenizer.eos_token
        
        self.model = CodeReviewClassifier(self.config)
        
        if model_path and os.path.exists(model_path):
            self.model.load_state_dict(torch.load(os.path.join(model_path, "pytorch_model.bin")))
            logger.info(f"Loaded model from {model_path}")
    
    def prepare_data(
        self,
        train_samples: List[CodeSample],
        eval_samples: List[CodeSample],
    ) -> Tuple[Dataset, Dataset]:
        """Prepare training and evaluation datasets."""
        train_dataset = CodeReviewDataset(train_samples, self.tokenizer, self.config.max_length)
        eval_dataset = CodeReviewDataset(eval_samples, self.tokenizer, self.config.max_length)
        
        return train_dataset, eval_dataset
    
    def compute_metrics(self, eval_pred):
        """Compute metrics for evaluation."""
        logits, labels = eval_pred
        predictions = np.argmax(logits, axis=-1)
        
        accuracy = accuracy_score(labels, predictions)
        precision, recall, f1, _ = precision_recall_fscore_support(
            labels, predictions, average="weighted"
        )
        
        return {
            "accuracy": accuracy,
            "precision": precision,
            "recall": recall,
            "f1": f1,
        }
    
    def train(
        self,
        train_dataset: Dataset,
        eval_dataset: Dataset,
        output_dir: Optional[str] = None,
    ) -> Trainer:
        """Train the model."""
        output_dir = output_dir or self.config.output_dir
        
        training_args = TrainingArguments(
            output_dir=output_dir,
            learning_rate=self.config.learning_rate,
            per_device_train_batch_size=self.config.batch_size,
            per_device_eval_batch_size=self.config.batch_size,
            num_train_epochs=self.config.num_epochs,
            warmup_steps=self.config.warmup_steps,
            weight_decay=self.config.weight_decay,
            gradient_accumulation_steps=self.config.gradient_accumulation_steps,
            fp16=self.config.fp16,
            logging_steps=self.config.logging_steps,
            eval_strategy=self.config.eval_strategy,
            eval_steps=self.config.eval_steps,
            save_strategy=self.config.save_strategy,
            save_steps=self.config.save_steps,
            load_best_model_at_end=self.config.load_best_model_at_end,
            metric_for_best_model=self.config.metric_for_best_model,
            greater_is_better=self.config.greater_is_better,
            seed=self.config.seed,
            dataloader_num_workers=self.config.dataloader_num_workers,
            remove_unused_columns=self.config.remove_unused_columns,
            report_to="tensorboard",
            save_total_limit=3,
        )
        
        self.trainer = Trainer(
            model=self.model,
            args=training_args,
            train_dataset=train_dataset,
            eval_dataset=eval_dataset,
            tokenizer=self.tokenizer,
            compute_metrics=self.compute_metrics,
            callbacks=[EarlyStoppingCallback(early_stopping_patience=3)],
        )
        
        self.trainer.train()
        return self.trainer
    
    def save_model(self, output_dir: str):
        """Save model and tokenizer."""
        self.model.save_pretrained(output_dir)
        self.tokenizer.save_pretrained(output_dir)
        
        # Save config
        config_path = os.path.join(output_dir, "model_config.json")
        with open(config_path, "w") as f:
            json.dump(self.config.__dict__, f, indent=2)


# Pre-trained model loader
class CodeReviewModelRegistry:
    """Registry for pre-trained and fine-tuned models."""
    
    _models = {}
    
    @classmethod
    def register(cls, name: str):
        def decorator(cls_impl):
            cls._models[name] = cls_impl
            return cls_impl
        return decorator
    
    @classmethod
    def get(cls, name: str) -> Optional[type]:
        return cls._models.get(name)
    
    @classmethod
    def load(cls, name: str, **kwargs) -> nn.Module:
        model_class = cls.get(name)
        if not model_class:
            raise ValueError(f"Model {name} not registered")
        return model_class(**kwargs)
    
    @classmethod
    def list_models(cls) -> List[str]:
        return list(cls._models.keys())


# Pre-trained model configurations
PRETRAINED_CONFIGS = {
    "codebert-base": ModelConfig(
        model_name="microsoft/codebert-base",
        num_labels=5,
        max_length=512,
    ),
    "codebert-java": ModelConfig(
        model_name="microsoft/codebert-base",
        num_labels=5,
        max_length=512,
    ),
    "graphcodebert": ModelConfig(
        model_name="microsoft/graphcodebert-base",
        num_labels=5,
        max_length=512,
    ),
    "codet5-base": ModelConfig(
        model_name="Salesforce/codet5-base",
        num_labels=5,
        max_length=512,
    ),
    "codet5-large": ModelConfig(
        model_name="Salesforce/codet5-large",
        num_labels=5,
        max_length=512,
    ),
    "plbart": ModelConfig(
        model_name="uclanlp/plbart-base",
        num_labels=5,
        max_length=512,
    ),
    "unixcoder": ModelConfig(
        model_name="microsoft/unixcoder-base",
        num_labels=5,
        max_length=512,
    ),
}


# Data preparation utilities
def prepare_training_data(
    data_dir: str,
    test_size: float = 0.2,
) -> Tuple[List[CodeSample], List[CodeSample]]:
    """Prepare training data from directory."""
    samples = []
    
    for file_path in Path(data_dir).rglob("*.json"):
        with open(file_path, "r") as f:
            data = json.load(f)
        
        if isinstance(data, list):
            for item in data:
                samples.append(CodeSample(**item))
        else:
            samples.append(CodeSample(**data))
    
    # Split
    np.random.shuffle(samples)
    split_idx = int(len(samples) * (1 - test_size))
    
    return samples[:split_idx], samples[split_idx:]


def create_training_samples_from_findings(findings: List[Dict]) -> List[CodeSample]:
    """Create training samples from Git-Fix findings."""
    samples = []
    
    for finding in findings:
        sample = CodeSample(
            code=finding.get("code_snippet", ""),
            language=finding.get("language", "python"),
            file_path=finding.get("file_path", ""),
            vulnerability_type=finding.get("category", ""),
            severity=finding.get("severity", "info"),
            line_start=finding.get("line_start"),
            line_end=finding.get("line_end"),
            suggested_fix=finding.get("suggested_fix"),
            confidence=finding.get("confidence", 0.5),
            labels=[{
                "severity": finding.get("severity", "info"),
                "category": finding.get("category", "style"),
                "line_start": finding.get("line_start"),
                "line_end": finding.get("line_end"),
            }],
        )
        samples.append(sample)
    
    return samples


# Model serving
class CodeReviewModelServer:
    """Production model server for code review."""
    
    def __init__(
        self,
        model_path: str,
        device: str = "cuda" if torch.cuda.is_available() else "cpu",
    ):
        self.device = device
        self.model = None
        self.tokenizer = None
        self._load_model(model_path)
    
    def _load_model(self, model_path: str):
        self.tokenizer = AutoTokenizer.from_pretrained(model_path)
        self.model = AutoModelForSequenceClassification.from_pretrained(model_path)
        self.model.to(self.device)
        self.model.eval()
    
    def predict(self, code: str, language: str = "python") -> Dict[str, Any]:
        """Run inference on code."""
        # Prepare input
        text = f"Language: {language}\n\nCode:\n{code}"
        
        inputs = self.tokenizer(
            code,
            truncation=True,
            max_length=512,
            padding="max_length",
            return_tensors="pt",
        ).to(self.device)
        
        with torch.no_grad():
            outputs = self.model(**inputs)
            logits = outputs.logits
            probs = torch.softmax(logits, dim=-1)
            pred_id = torch.argmax(probs, dim=-1).item()
            
            id2label = {0: "critical", 1: "high", 2: "medium", 3: "low", 4: "info"}
            
            return {
                "severity": ["critical", "high", "medium", "low", "info"][pred_id],
                "confidence": probs[0][pred_id].item(),
                "probabilities": {
                    ["critical", "high", "medium", "low", "info"][i]: probs[0][i].item()
                    for i in range(5)
                },
            }
    
    def batch_predict(self, codes: List[str], language: str = "python") -> List[Dict]:
        """Batch prediction for multiple code snippets."""
        results = []
        for code in codes:
            results.append(self.predict(code, language))
        return results


# Export
__all__ = [
    "ModelConfig",
    "CodeSample",
    "CodeReviewDataset",
    "VulnerabilityDetectionDataset",
    "CodeReviewClassifier",
    "VulnerabilityDetector",
    "CodeReviewModelTrainer",
    "CodeReviewModelRegistry",
    "PRETRAINED_CONFIGS",
    "prepare_training_data",
    "create_training_samples_from_findings",
    "CodeReviewModelServer",
]