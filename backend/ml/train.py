#!/usr/bin/env python3
# =============================================================================
# Git-Fix Model Training Script
# =============================================================================
# Train fine-tuned models for code review
# =============================================================================

import os
import sys
import argparse
import json
import logging
from pathlib import Path

# Add parent directory to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.models import (
    ModelConfig,
    CodeReviewModelTrainer,
    CodeReviewModelServer,
    PRETRAINED_CONFIGS,
    prepare_training_data,
    create_training_samples_from_findings,
)

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def parse_args():
    parser = argparse.ArgumentParser(description="Train Git-Fix code review model")
    
    parser.add_argument(
        "--model",
        type=str,
        default="codebert-base",
        choices=list(PRETRAINED_CONFIGS.keys()),
        help="Pre-trained model to fine-tune",
    )
    parser.add_argument(
        "--data-dir",
        type=str,
        default="./data/training",
        help="Directory containing training data",
    )
    parser.add_argument(
        "--output-dir",
        type=str,
        default="./models/code-review-finetuned",
        help="Output directory for trained model",
    )
    parser.add_argument(
        "--epochs",
        type=int,
        default=3,
        help="Number of training epochs",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Training batch size",
    )
    parser.add_argument(
        "--learning-rate",
        type=float,
        default=2e-5,
        help="Learning rate",
    )
    parser.add_argument(
        "--max-length",
        type=int,
        default=512,
        help="Maximum sequence length",
    )
    parser.add_argument(
        "--batch-size",
        type=int,
        default=16,
        help="Training batch size",
    )
    parser.add_argument(
        "--test-size",
        type=float,
        default=0.2,
        help="Test split ratio",
    )
    parser.add_argument(
        "--seed",
        type=int,
        default=42,
        help="Random seed",
    )
    parser.add_argument(
        "--findings-file",
        type=str,
        help="Path to Git-Fix findings JSON file to create training data",
    )
    parser.add_argument(
        "--serve",
        action="store_true",
        help="Start model server after training",
    )
    parser.add_argument(
        "--port",
        type=int,
        default=8000,
        help="Port for model server",
    )
    
    return parser.parse_args()


def main():
    args = parse_args()
    
    # Set random seeds
    import random
    import numpy as np
    import torch
    
    random.seed(42)
    np.random.seed(42)
    torch.manual_seed(42)
    if torch.cuda.is_available():
        torch.cuda.manual_seed_all(42)
    
    # Load configuration
    config = PRETRAINED_CONFIGS[args.model]
    config.num_epochs = args.epochs
    config.batch_size = args.batch_size
    config.learning_rate = args.learning_rate
    config.max_length = args.max_length
    config.output_dir = args.output_dir
    config.seed = args.seed
    
    # Prepare data
    if args.findings_file:
        print(f"Loading findings from {args.findings_file}")
        with open(args.findings_file, "r") as f:
            findings = json.load(f)
        
        from ml.models import create_training_samples_from_findings
        samples = create_training_samples_from_findings(findings)
        print(f"Created {len(samples)} training samples from findings")
    else:
        print(f"Loading training data from {args.data_dir}")
        train_samples, eval_samples = prepare_training_data(
            args.data_dir,
            test_size=args.test_size,
        )
    
    # Split data
    import numpy as np
    np.random.shuffle(samples)
    split_idx = int(len(samples) * 0.8)
    train_samples = samples[:split_idx]
    eval_samples = samples[split_idx:]
    
    print(f"Training samples: {len(train_samples)}")
    print(f"Eval samples: {len(eval_samples)}")
    
    # Initialize trainer
    trainer = CodeReviewModelTrainer(config)
    trainer.load_model()
    
    # Prepare datasets
    train_dataset, eval_dataset = trainer.prepare_data(train_samples, eval_samples)
    
    # Train
    print("Starting training...")
    trainer.train(train_dataset, eval_dataset, args.output_dir)
    
    # Save model
    trainer.save_model(args.output_dir)
    print(f"Model saved to {args.output_dir}")
    
    # Evaluate
    print("Evaluating model...")
    results = trainer.trainer.evaluate()
    print(f"Evaluation results: {results}")
    
    # Save metrics
    with open(os.path.join(args.output_dir, "eval_results.json"), "w") as f:
        json.dump(results, f, indent=2)
    
    # Start server if requested
    if args.serve:
        print(f"Starting model server on port {args.port}...")
        server = CodeReviewModelServer(args.output_dir)
        
        # Simple HTTP server
        from http.server import HTTPServer, BaseHTTPRequestHandler
        import json
        
        class ModelHandler(BaseHTTPRequestHandler):
            server_instance = None
            
            def do_POST(self):
                if self.path == "/predict":
                    content_length = int(self.headers['Content-Length'])
                    post_data = self.rfile.read(content_length)
                    request = json.loads(post_data.decode())
                    
                    code = request.get("code", "")
                    language = request.get("language", "python")
                    
                    if not code:
                        self.send_response(400)
                        self.end_headers()
                        self.wfile.write(json.dumps({"error": "No code provided"}).encode())
                        return
                    
                    result = self.server.model_server.predict(
                        code, request.get("language", "python")
                    )
                    
                    self.send_response(200)
                    self.send_header("Content-Type", "application/json")
                    self.end_headers()
                    self.wfile.write(json.dumps(result).encode())
                else:
                    self.send_response(404)
                    self.end_headers()
            
            def log_message(self, format, *args):
                pass
        
        ModelHandler.model_server = CodeReviewModelServer(args.output_dir)
        
        server = HTTPServer(("0.0.0.0", args.port), lambda *args, **kwargs: ModelHandler(*args, **kwargs, model_server=CodeReviewModelServer(args.output_dir)))
        print(f"Model server running on http://localhost:{args.port}")
        server.serve_forever()


if __name__ == "__main__":
    import os
    import json
    main()