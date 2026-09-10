#!/usr/bin/env python3
# =============================================================================
# Git-Fix Model Serving API
# =============================================================================
# FastAPI server for serving fine-tuned code review models
# =============================================================================

import os
import json
import logging
from typing import List, Optional, Dict, Any
from pathlib import Path

from fastapi import FastAPI, HTTPException, BackgroundTasks
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
import uvicorn

import sys
sys.path.insert(0, str(Path(__file__).parent.parent))

from ml.models import CodeReviewModelServer, CodeReviewModelServer

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

app = FastAPI(
    title="Git-Fix Model API",
    description="Fine-tuned code review model serving API",
    version="1.0.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Request/Response models
class PredictionRequest(BaseModel):
    code: str = Field(..., description="Code to analyze")
    language: str = Field(default="python", description="Programming language")
    model: Optional[str] = Field(default=None, description="Specific model to use")


class BatchPredictionRequest(BaseModel):
    codes: List[str] = Field(..., description="List of code snippets to analyze")
    language: str = Field(default="python", description="Programming language")
    model: Optional[str] = Field(default=None, description="Specific model to use")


class PredictionResponse(BaseModel):
    severity: str = Field(..., description="Predicted severity level")
    confidence: float = Field(..., description="Prediction confidence")
    probabilities: Dict[str, float] = Field(..., description="Probabilities for each severity level")


class BatchPredictionResponse(BaseModel):
    predictions: List[dict] = Field(..., description="List of predictions")
    total: int = Field(..., description="Total predictions")
    model: str = Field(..., description="Model used for prediction")


class ModelInfo(BaseModel):
    name: str
    path: str
    loaded: bool
    device: str
    num_labels: int
    labels: List[str]


class HealthResponse(BaseModel):
    status: str
    models_loaded: int
    device: str
    cuda_available: bool


# Global model registry
model_servers: Dict[str, CodeReviewModelServer] = {}
DEFAULT_MODEL = "codebert-base"


@app.on_event("startup")
async def startup_event():
    """Load default model on startup."""
    global model_servers
    
    model_dir = os.getenv("MODEL_DIR", "./models")
    
    # Load default model if exists
    default_path = Path("./models") / DEFAULT_MODEL
    if default_path.exists():
        try:
            model_servers[DEFAULT_MODEL] = CodeReviewModelServer(str(default_path))
            logger.info(f"Loaded default model: {DEFAULT_MODEL}")
        except Exception as e:
            logger.warning(f"Failed to load default model: {e}")


def get_model_server(model_name: str = DEFAULT_MODEL) -> CodeReviewModelServer:
    """Get or load model server."""
    if model_name not in model_servers:
        model_path = Path("./models") / model_name
        if not model_path.exists():
            raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
        model_servers[model_name] = CodeReviewModelServer(str(Path("./models") / model_name))
    return model_servers[model_name]


@app.get("/health", response_model=HealthResponse)
async def health_check():
    """Health check endpoint."""
    import torch
    
    return HealthResponse(
        status="healthy",
        models_loaded=len(model_servers),
        device="cuda" if torch.cuda.is_available() else "cpu",
        cuda_available=torch.cuda.is_available(),
    )


@app.get("/models", response_model=List[ModelInfo])
async def list_models():
    """List available models."""
    models = []
    models_dir = Path("./models")
    if models_dir.exists():
        for model_dir in models_dir.iterdir():
            if model_dir.is_dir():
                try:
                    server = CodeReviewModelServer(str(model_dir))
                    models.append(ModelInfo(
                        name=model_dir.name,
                        path=str(model_dir),
                        loaded=model_dir.name in model_servers,
                        device="cuda" if server.model.device.type == "cuda" else "cpu",
                        num_labels=server.model.config.num_labels,
                        labels=["critical", "high", "medium", "low", "info"],
                    ))
                except:
                    pass
    return models


@app.post("/models/{model_name}/load")
async def load_model(model_name: str):
    """Load a model into memory."""
    global model_servers
    
    model_path = Path("./models") / model_name
    if not model_path.exists():
        raise HTTPException(status_code=404, detail=f"Model {model_name} not found")
    
    try:
        model_servers[model_name] = CodeReviewModelServer(str(Path("./models") / model_name))
        return {"status": "loaded", "model": model_name}
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Failed to load model: {str(e)}")


@app.post("/models/{model_name}/unload")
async def unload_model(model_name: str):
    """Unload a model from memory."""
    global model_servers
    
    if model_name in model_servers:
        del model_servers[model_name]
        import torch
        torch.cuda.empty_cache()
        return {"status": "unloaded", "model": model_name}
    raise HTTPException(status_code=404, detail=f"Model {model_name} not loaded")


@app.post("/predict", response_model=PredictionResponse)
async def predict(request: PredictionRequest):
    """Single code prediction."""
    try:
        model_name = request.model or DEFAULT_MODEL
        server = get_model_server(model_name)
        
        result = server.predict(request.code, request.language)
        result["model"] = model_name
        
        return result
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/predict/batch", response_model=BatchPredictionResponse)
async def predict_batch(request: BatchPredictionRequest):
    """Batch prediction for multiple code snippets."""
    try:
        model_name = request.model or DEFAULT_MODEL
        server = get_model_server(model_name)
        
        predictions = []
        for code in request.codes:
            result = server.predict(code, request.language)
            predictions.append({**result, "code_preview": code[:100]})
        
        return BatchPredictionResponse(
            predictions=predictions,
            total=len(predictions),
            model=request.model or DEFAULT_MODEL,
        )
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/models/{model_name}/predict", response_model=PredictionResponse)
async def predict_with_model(model_name: str, request: PredictionRequest):
    """Predict using specific model."""
    try:
        server = get_model_server(model_name)
        result = server.predict(request.code, request.language)
        result["model"] = model_name
        return result
    except Exception as e:
        logger.error(f"Prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.post("/models/{model_name}/predict/batch", response_model=BatchPredictionResponse)
async def predict_batch_with_model(model_name: str, request: BatchPredictionRequest):
    """Batch prediction with specific model."""
    try:
        server = get_model_server(model_name)
        
        predictions = []
        for code in request.codes:
            result = server.predict(code, request.language)
            predictions.append({**result, "code_preview": code[:100]})
        
        return BatchPredictionResponse(
            predictions=predictions,
            total=len(predictions),
            model=model_name,
        )
    except Exception as e:
        logger.error(f"Batch prediction error: {e}")
        raise HTTPException(status_code=500, detail=str(e))


@app.get("/models/{model_name}/info", response_model=ModelInfo)
async def model_info(model_name: str):
    """Get model information."""
    server = get_model_server(model_name)
    
    return ModelInfo(
        name=model_name,
        path=str(Path("./models") / model_name),
        loaded=True,
        device=str(server.model.device),
        num_labels=server.model.config.num_labels,
        labels=["critical", "high", "medium", "low", "info"],
    )


@app.post("/models/{model_name}/unload")
async def unload_model(model_name: str):
    """Unload a model from memory."""
    global model_servers
    
    if model_name in model_servers:
        del model_servers[model_name]
        import torch
        torch.cuda.empty_cache()
        return {"status": "unloaded", "model": model_name}
    
    raise HTTPException(status_code=404, detail=f"Model {model_name} not loaded")


@app.get("/metrics")
async def metrics():
    """Prometheus-style metrics."""
    import torch
    
    return {
        "models_loaded": len(model_servers),
        "cuda_available": torch.cuda.is_available(),
        "cuda_memory_allocated": torch.cuda.memory_allocated() if torch.cuda.is_available() else 0,
        "cuda_memory_reserved": torch.cuda.memory_reserved() if torch.cuda.is_available() else 0,
        "models": list(model_servers.keys()),
    }


# CLI entry point
def main():
    import argparse
    
    parser = argparse.ArgumentParser(description="Git-Fix Model Serving API")
    parser.add_argument("--host", default="0.0.0.0", help="Host to bind")
    parser.add_argument("--port", type=int, default=8000, help="Port to bind")
    parser.add_argument("--workers", type=int, default=1, help="Number of workers")
    parser.add_argument("--reload", action="store_true", help="Enable auto-reload")
    
    args = parser.parse_args()
    
    uvicorn.run(
        "ml.serve:app",
        host=args.host,
        port=args.port,
        workers=args.workers,
        reload=args.reload,
    )


if __name__ == "__main__":
    import os
    main()