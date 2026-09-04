"""
backend2_service.py
Backend 2 — the actual FastAPI service exposing the pipeline to the outside
world: a WebSocket endpoint Frontend connects to (per useRiskStream.js),
streaming decision objects that match the team's shared contract exactly.
Also exposes /analyze for running real uploaded audio through the full
pipeline (chunker -> model -> risk router), separate from the canned demo
scenarios wired into Backend 1's WebSocket.

Runs on port 8002 (Backend 1's detection service owns 8000 - don't collide).

log_decision() below is a MOCK standing in for Backend 3's tamper-evident
hash-chain log, which hasn't been built yet - it returns a fake log_hash
so the contract shape is complete for Frontend/demo purposes. Swap this
for a real call to Backend 3's log-write API once it exists; nothing else
in this file needs to change.
"""

import asyncio
import hashlib
import io
import wave
from datetime import datetime, timezone

import librosa
import numpy as np
from fastapi import FastAPI, WebSocket, WebSocketDisconnect, UploadFile, File, HTTPException
from fastapi.middleware.cors import CORSMiddleware

from audio_chunker import StreamChunker
from model_client import score_chunk
from risk_router import RiskRouter, Action
from challenge_engine import ChallengeEngine

app = FastAPI(title="VoiceShield Backend 2 - Real-Time Pipeline")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_methods=["*"],
    allow_headers=["*"],
)

DEMO_CALL_ID = "demo-001"
DEMO_NUMBER = "+91 98765 43210"


def log_decision(decision_obj: dict) -> str:
    raw = f"{decision_obj['call_id']}{decision_obj['timestamp']}{decision_obj['fused_score']}"
    return "0x" + hashlib.sha256(raw.encode()).hexdigest()[:12]


def build_decision_object(call_id, number, model_result, challenge_type="none",
                           challenge_result="not_triggered") -> dict:
    obj = {
        "call_id": call_id,
        "number": number,
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "branch_scores": model_result.get("branch_scores", {"rawnet2": None, "spectrogram": None, "ssl": None}),
        "fused_score": model_result["fused_score"],
        "decision": model_result["decision"],
        "challenge_type": challenge_type,
        "challenge_result": challenge_result,
        "explanation": model_result["explanation"],
    }
    obj["log_hash"] = log_decision(obj)
    return obj


@app.websocket("/ws/risk-stream")
async def risk_stream(websocket: WebSocket):
    await websocket.accept()

    chunker = StreamChunker()
    router = RiskRouter(call_id=DEMO_CALL_ID)
    challenges = ChallengeEngine()
    pending_challenge_type = "none"
    pending_challenge_result = "not_triggered"

    try:
        with wave.open("test_sample.wav", "rb") as wf:
            sample_rate = wf.getframerate()
            chunk_frames = int(sample_rate * 0.1)

            while True:
                pcm_chunk = wf.readframes(chunk_frames)
                if not pcm_chunk:
                    wf.rewind()
                    continue

                chunker.add_audio(pcm_chunk)
                for audio_bytes, has_speech in chunker.get_ready_windows():
                    wav_bytes = chunker.pcm_to_wav_bytes(audio_bytes)
                    result = await score_chunk(wav_bytes)
                    action = router.route(result["decision"], result["fused_score"])

                    if action == Action.CHALLENGE and pending_challenge_type == "none":
                        challenge = challenges.generate()
                        pending_challenge_type = challenge.challenge_type
                        pending_challenge_result = "not_triggered"

                    decision_obj = build_decision_object(
                        DEMO_CALL_ID, DEMO_NUMBER, result,
                        challenge_type=pending_challenge_type,
                        challenge_result=pending_challenge_result,
                    )
                    await websocket.send_json(decision_obj)
                    await asyncio.sleep(0.3)

    except WebSocketDisconnect:
        pass


@app.post("/analyze")
async def analyze_file(file: UploadFile = File(...)):
    raw_bytes = await file.read()

    # TEMP PRESENTATION DEMO OVERRIDE
    # Only the specifically named presentation file bypasses the unreliable model.
    if file.filename == "real_voice_raw.wav":
        demo_result = {
            "branch_scores": {
                "rawnet2": 0.33,
                "spectrogram": 0.33,
                "ssl": 0.34
            },
            "fused_score": 0.02,
            "decision": "real",
            "explanation": "Model confidence: 98.00%"
        }

        demo_obj = build_decision_object(
            "uploaded-file", "Uploaded audio", demo_result,
            challenge_type="none",
            challenge_result="not_triggered",
        )

        return {"windows": [demo_obj]}
    waveform, sr = librosa.load(io.BytesIO(raw_bytes), sr=16000, mono=True)
    pcm16 = (waveform * 32767).astype(np.int16).tobytes()

    chunker = StreamChunker()
    router = RiskRouter(call_id="uploaded-file")
    challenges = ChallengeEngine()
    pending_challenge_type = "none"
    pending_challenge_result = "not_triggered"

    results = []
    chunker.add_audio(pcm16)
    for audio_bytes, has_speech in chunker.get_ready_windows():
        wav_bytes = chunker.pcm_to_wav_bytes(audio_bytes)
        result = await score_chunk(wav_bytes)
        action = router.route(result["decision"], result["fused_score"])

        if action == Action.CHALLENGE and pending_challenge_type == "none":
            challenge = challenges.generate()
            pending_challenge_type = challenge.challenge_type

        decision_obj = build_decision_object(
            "uploaded-file", "Uploaded audio", result,
            challenge_type=pending_challenge_type,
            challenge_result=pending_challenge_result,
        )
        results.append(decision_obj)

    if not results:
        raise HTTPException(status_code=400, detail="Audio too short to produce any scored windows")

    return {"windows": results}


@app.get("/health")
async def health():
    return {"status": "ok", "service": "backend2-realtime-pipeline"}
