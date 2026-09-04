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

DEMO_NUMBER = "+91 98765 43210"


@app.websocket("/ws/risk-stream")
async def websocket_risk_stream(
    websocket: WebSocket,
    token: Optional[str] = Query(None)
):
    global active_connections

    # Must accept() first — closing pre-accept drops the connection
    # abruptly instead of sending a proper rejection code to the client.
    await websocket.accept()

    # 1. Token Authentication Check (after accept)
    if token != EXPECTED_API_TOKEN:
        logger.warning(f"Unauthorized WebSocket connection attempt with token: {token}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid authentication token")
        return

    # 2. Max Connection Threshold Guard
    if active_connections >= CONNECTION_LIMIT:
        logger.warning("WebSocket connection rejected: server capacity reached.")
        await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER, reason="Connection limit reached")
        return

    active_connections += 1
    logger.info(f"Client connected. Active connections: {active_connections}")

    # Rate limiting trackers per connection
    request_times = []

    try:
        # Initial baseline state emission — field names must match CallScreen.jsx
        await websocket.send_json({
            "number": DEMO_NUMBER,
            "fused_score": 0.12,
            "decision": "real",
            "explanation": "Voice characteristics closely match the verified speaker across waveform, spectrogram, and SSL branches.",
            "branch_scores": {"rawnet2": 0.10, "spectrogram": 0.14, "ssl": 0.12},
            "challenge_type": "vocalization"
        })

        while True:
            data = await websocket.receive_text()

            now = time.time()
            request_times = [t for t in request_times if now - t < 60]
            if len(request_times) >= MAX_REQUESTS_PER_MINUTE:
                await websocket.send_json({
                    "error": "Rate limit exceeded. Slow down stream cadence."
                })
                continue
            request_times.append(now)

            payload = json.loads(data)
            scenario = payload.get("scenario", "safe")

            if scenario == "clone":
                response = {
                    "number": DEMO_NUMBER,
                    "fused_score": 0.79,
                    "decision": "suspected_clone",
                    "explanation": "Spectrogram branch flagged unnatural harmonic structure in the 2–4kHz band.",
                    "branch_scores": {"rawnet2": 0.82, "spectrogram": 0.75, "ssl": 0.79},
                    "challenge_type": "vocalization"
                }
            else:
                response = {
                    "number": DEMO_NUMBER,
                    "fused_score": 0.12,
                    "decision": "real",
                    "explanation": "Voice characteristics closely match the verified speaker across waveform, spectrogram, and SSL branches.",
                    "branch_scores": {"rawnet2": 0.10, "spectrogram": 0.14, "ssl": 0.12},
                    "challenge_type": "vocalization"
                }

            await websocket.send_json(response)

    except WebSocketDisconnect:
        logger.info("Client disconnected from risk stream WebSocket")
    except Exception as e:
        logger.exception(f"WebSocket error: {e}")
    finally:
        active_connections = max(0, active_connections - 1)
        logger.info(f"Connection closed. Active connections remaining: {active_connections}")


@app.get("/health")
async def health():
    return {"status": "ok"}