from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect
from typing import Optional
import torch
import torch.nn as nn
import librosa
import io
import json
import numpy as np
import onnxruntime as ort
from pathlib import Path
import logging

app = FastAPI(title="VoiceShield Detection Service")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)
# ... [Keep your existing model loading, /enroll, /detect code here] ...

@app.websocket("/ws/risk-stream")
async def websocket_risk_stream(websocket: WebSocket):
    await websocket.accept()
    logger.info("Client connected to risk stream WebSocket")
    
    try:
        # Initial baseline state emission
        await websocket.send_json({
            "risk_score": 0.12,
            "decision": "real",
            "branch_scores": {"rawnet2": 0.33, "spectrogram": 0.33, "ssl": 0.34}
        })

        while True:
            # Receive audio frame chunks or stream triggers from client
            data = await websocket.receive_text()
            payload = json.loads(data)

            # Process incoming frame or simulation trigger
            # Example: calculate risk dynamically or mirror scenario state
            scenario = payload.get("scenario", "safe")
            
            if scenario == "clone":
                response = {
                    "risk_score": 0.94,
                    "decision": "suspected_clone",
                    "branch_scores": {"rawnet2": 0.88, "spectrogram": 0.92, "ssl": 0.96}
                }
            else:
                response = {
                    "risk_score": 0.08,
                    "decision": "real",
                    "branch_scores": {"rawnet2": 0.10, "spectrogram": 0.05, "ssl": 0.09}
                }

            await websocket.send_json(response)

    except WebSocketDisconnect:
        logger.info("Client disconnected from risk stream WebSocket")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
        await websocket.close()