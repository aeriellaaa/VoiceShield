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
from pathlib import Path
import logging

from ml.training.train_fusion_real import MultiViewModel
from ml.datasets.multiview_real_dataset import feature_extractor, ssl_model, FIXED_LEN, N_MFCC

app = FastAPI(title="VoiceShield Detection Service")

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

# --- Real model loading (restored - this was dropped in a recent merge) ---
MODEL_PATH = "ml/export/fusion_model_real.pt"
CONFIDENCE_THRESHOLD = 0.65

model = MultiViewModel()
model.load_state_dict(torch.load(MODEL_PATH))
model.eval()


def extract_views(waveform):
    fixed = librosa.util.fix_length(waveform, size=FIXED_LEN) if len(waveform) < FIXED_LEN else waveform[:FIXED_LEN]
    raw_tensor = torch.tensor(fixed, dtype=torch.float32).unsqueeze(0).unsqueeze(0)

    lfcc = librosa.feature.mfcc(y=waveform, sr=16000, n_mfcc=N_MFCC)
    lfcc_tensor = torch.tensor(lfcc.mean(axis=1), dtype=torch.float32).unsqueeze(0)

    inputs = feature_extractor(waveform, sampling_rate=16000, return_tensors="pt")
    with torch.no_grad():
        ssl_out = ssl_model(**inputs)
    ssl_tensor = ssl_out.last_hidden_state.mean(dim=1)

    return raw_tensor, lfcc_tensor, ssl_tensor


@app.post("/detect")
async def detect(file: UploadFile = File(...)):
    """
    Restored real-model detection endpoint. Matches the team's shared
    decision-object contract (minus fields Backend 2/3 add later).
    """
    audio_bytes = await file.read()

    waveform, sr = librosa.load(io.BytesIO(audio_bytes), sr=16000)

    raw, lfcc, ssl = extract_views(waveform)
    with torch.no_grad():
        logits, attn_weights = model(raw, lfcc, ssl)
        probs = torch.softmax(logits, dim=-1)
        confidence, predicted_class = torch.max(probs, dim=-1)

    confidence_val = confidence.item()
    if confidence_val < CONFIDENCE_THRESHOLD:
        decision = "unverified"
    elif predicted_class.item() == 0:
        decision = "real"
    else:
        decision = "suspected_clone"

    # attn_weights: per-branch attention weights (how much each branch
    # contributed to this decision), per Backend 1's note - not per-branch
    # spoof probabilities.
    branch_scores = {"rawnet2": None, "spectrogram": None, "ssl": None}
    try:
        weights = attn_weights.squeeze().tolist()
        if isinstance(weights, list) and len(weights) == 3:
            branch_scores = {
                "rawnet2": weights[0],
                "spectrogram": weights[1],
                "ssl": weights[2],
            }
    except Exception:
        pass  # fall back to nulls if attn_weights shape is unexpected

    return {
        "branch_scores": branch_scores,
        "fused_score": probs[0, 1].item(),
        "decision": decision,
        "explanation": f"Model confidence: {confidence_val:.2%}",
    }


# --- Existing WebSocket demo-fallback stream (kept from the recent merge) ---
EXPECTED_API_TOKEN = os.getenv("WS_AUTH_TOKEN", "voiceshield_demo_token_2026")
MAX_REQUESTS_PER_MINUTE = 60
CONNECTION_LIMIT = 10
active_connections = 0
DEMO_NUMBER = "+91 98765 43210"


@app.websocket("/ws/risk-stream")
async def websocket_risk_stream(websocket: WebSocket, token: Optional[str] = Query(None)):
    global active_connections
    await websocket.accept()

    if token != EXPECTED_API_TOKEN:
        logger.warning(f"Unauthorized WebSocket connection attempt with token: {token}")
        await websocket.close(code=status.WS_1008_POLICY_VIOLATION, reason="Invalid authentication token")
        return

    if active_connections >= CONNECTION_LIMIT:
        logger.warning("WebSocket connection rejected: server capacity reached.")
        await websocket.close(code=status.WS_1013_TRY_AGAIN_LATER, reason="Connection limit reached")
        return

    active_connections += 1
    logger.info(f"Client connected. Active connections: {active_connections}")
    request_times = []

    try:
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
                await websocket.send_json({"error": "Rate limit exceeded. Slow down stream cadence."})
                continue
            request_times.append(now)

            payload = json.loads(data)
            scenario = payload.get("scenario", "safe")

            if scenario == "clone":
                response = {
                    "number": DEMO_NUMBER, "fused_score": 0.79, "decision": "suspected_clone",
                    "explanation": "Spectrogram branch flagged unnatural harmonic structure in the 2–4kHz band.",
                    "branch_scores": {"rawnet2": 0.82, "spectrogram": 0.75, "ssl": 0.79},
                    "challenge_type": "vocalization"
                }
            else:
                response = {
                    "number": DEMO_NUMBER, "fused_score": 0.12, "decision": "real",
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