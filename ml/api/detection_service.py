from fastapi import FastAPI, UploadFile, File, Form, HTTPException, WebSocket, WebSocketDisconnect, status, Query
from typing import Optional
import torch
import torch.nn as nn
import librosa
import io
import json
import time
import os
import numpy as np
import onnxruntime as ort
from pathlib import Path
import logging

app = FastAPI(title="VoiceShield Detection Service")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# Security and Rate Limiting Configuration
EXPECTED_API_TOKEN = os.getenv("WS_AUTH_TOKEN", "voiceshield_demo_token_2026")
MAX_REQUESTS_PER_MINUTE = 60
CONNECTION_LIMIT = 10

active_connections = 0

@app.websocket("/ws/risk-stream")
async def websocket_risk_stream(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    global active_connections

    # 1. Token Authentication Check
    if token != EXPECTED_API_TOKEN:
        logger.warning(f"Unauthorized WebSocket connection attempt with token: {token}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid authentication token")
        return

    # 2. Max Connection Threshold Guard
    if active_connections >= CONNECTION_LIMIT:
        logger.warning("WebSocket connection rejected: server capacity reached.")
        await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER, reason="Connection limit reached")
        return

    await websocket.accept()
    active_connections += 1
    logger.info(f"Client connected. Active connections: {active_connections}")
    
    # Rate limiting trackers per connection
    request_times = []

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

            # 3. Simple Sliding-Window Rate Limiting Check
            now = time.time()
            request_times = [t for t in request_times if now - t < 60]
            if len(request_times) >= MAX_REQUESTS_PER_MINUTE:
                await websocket.send_json({
                    "error": "Rate limit exceeded. Slow down stream cadence."
                })
                continue
            request_times.append(now)

            payload = json.loads(data)

            # Process incoming frame or simulation trigger
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
    finally:
        active_connections = max(0, active_connections - 1)
        logger.info(f"Connection closed. Active connections remaining: {active_connections}")