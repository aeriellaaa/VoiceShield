"""
backend2_service.py
Backend 2 — the actual FastAPI service exposing the pipeline to the outside
world: a WebSocket endpoint Frontend connects to (per useRiskStream.js),
streaming decision objects that match the team's shared contract exactly.

Runs on port 8002 (Backend 1's detection service owns 8000 - don't collide).
Frontend's SOCKET_URL should point to ws://localhost:8002/ws/risk-stream.

log_decision() below is a MOCK standing in for Backend 3's tamper-evident
hash-chain log, which hasn't been built yet - it returns a fake log_hash
so the contract shape is complete for Frontend/demo purposes. Swap this
for a real call to Backend 3's log-write API once it exists; nothing else
in this file needs to change.
"""

import asyncio
import hashlib
import os
import time
import wave
from collections import defaultdict
from datetime import datetime, timezone

from fastapi import FastAPI, WebSocket, WebSocketDisconnect

from audio_chunker import StreamChunker
from model_client import score_chunk
from risk_router import RiskRouter, Action
from challenge_engine import ChallengeEngine

app = FastAPI(title="VoiceShield Backend 2 - Real-Time Pipeline")

DEMO_CALL_ID = "demo-001"
DEMO_NUMBER = "+91 98765 43210"

WS_AUTH_REQUIRED = os.getenv("WS_AUTH_REQUIRED", "false").lower() == "true"
WS_AUTH_TOKEN = os.getenv("WS_AUTH_TOKEN", "dev-ws-token-voiceshield")
ALLOWED_ORIGINS = [
    o.strip() for o in os.getenv(
        "ALLOWED_ORIGINS",
        "http://localhost:5173,http://127.0.0.1:5173,http://localhost:3000,http://127.0.0.1:3000,*"
    ).split(",") if o.strip()
]


class WSRateLimiter:
    """Rate limiter for WebSocket connections per client IP."""

    def __init__(self, max_concurrent: int = 10, max_per_minute: int = 20):
        self.max_concurrent = max_concurrent
        self.max_per_minute = max_per_minute
        self.active_connections: dict[str, int] = defaultdict(int)
        self.connection_history: dict[str, list[float]] = defaultdict(list)

    def is_rate_limited(self, client_ip: str) -> tuple[bool, str]:
        now = time.time()
        # Clean up timestamps older than 60 seconds
        self.connection_history[client_ip] = [
            t for t in self.connection_history[client_ip] if now - t < 60
        ]

        if self.active_connections[client_ip] >= self.max_concurrent:
            return True, f"Max concurrent connections limit ({self.max_concurrent}) reached."

        if len(self.connection_history[client_ip]) >= self.max_per_minute:
            return True, f"Connection frequency limit ({self.max_per_minute}/min) exceeded."

        return False, ""

    def add_connection(self, client_ip: str):
        self.active_connections[client_ip] += 1
        self.connection_history[client_ip].append(time.time())

    def remove_connection(self, client_ip: str):
        if self.active_connections[client_ip] > 0:
            self.active_connections[client_ip] -= 1


rate_limiter = WSRateLimiter()


def verify_ws_auth(websocket: WebSocket) -> bool:
    """
    Verifies WebSocket auth token. By default, WS_AUTH_REQUIRED=false for demo safety.
    """
    if not WS_AUTH_REQUIRED:
        return True

    # 1. Check query param: ?token=...
    token = websocket.query_params.get("token")
    if token == WS_AUTH_TOKEN:
        return True

    # 2. Check X-API-Key header
    api_key = websocket.headers.get("x-api-key")
    if api_key == WS_AUTH_TOKEN:
        return True

    # 3. Check Authorization header: Bearer <token>
    auth_header = websocket.headers.get("authorization", "")
    if auth_header.startswith("Bearer ") and auth_header[7:].strip() == WS_AUTH_TOKEN:
        return True

    return False


def verify_origin(websocket: WebSocket) -> bool:
    """Validates the Origin header against ALLOWED_ORIGINS."""
    if "*" in ALLOWED_ORIGINS:
        return True
    origin = websocket.headers.get("origin")
    if not origin:
        return True  # Non-browser clients might not set Origin
    return origin in ALLOWED_ORIGINS


def log_decision(decision_obj: dict) -> str:
    """
    MOCK for Backend 3's hash-chain log. Real version should POST this
    decision object to Backend 3's log-write API and return the real hash.
    This fake version just hashes the decision content so it's at least
    deterministic and unique per decision, not a random placeholder string.
    """
    raw = f"{decision_obj['call_id']}{decision_obj['timestamp']}{decision_obj['fused_score']}"
    return "0x" + hashlib.sha256(raw.encode()).hexdigest()[:12]


def build_decision_object(call_id, number, model_result, challenge_type="none",
                           challenge_result="not_triggered") -> dict:
    """Assembles a full decision object matching the team's Section 2 contract."""
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
    # 1. Authentication check
    if not verify_ws_auth(websocket):
        await websocket.close(code=1008, reason="Unauthorized: Invalid or missing token")
        return

    # 2. Origin check
    if not verify_origin(websocket):
        await websocket.close(code=1008, reason="Forbidden: Disallowed Origin")
        return

    # 3. Rate limiting check
    client_ip = websocket.client.host if websocket.client else "127.0.0.1"
    is_limited, reason = rate_limiter.is_rate_limited(client_ip)
    if is_limited:
        await websocket.close(code=1008, reason=f"Rate limited: {reason}")
        return

    rate_limiter.add_connection(client_ip)
    await websocket.accept()

    chunker = StreamChunker()
    router = RiskRouter(call_id=DEMO_CALL_ID)
    challenges = ChallengeEngine()
    pending_challenge_type = "none"
    pending_challenge_result = "not_triggered"

    try:
        if os.path.exists("test_sample.wav"):
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
        else:
            # Fallback for presentation when test_sample.wav is not present on disk
            sample_rate = 16000
            dummy_pcm = b"\x00\x00" * int(sample_rate * 0.1)
            while True:
                chunker.add_audio(dummy_pcm)
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
    finally:
        rate_limiter.remove_connection(client_ip)



@app.get("/health")
async def health():
    return {"status": "ok", "service": "backend2-realtime-pipeline"}