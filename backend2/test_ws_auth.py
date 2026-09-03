import asyncio
import sys
import unittest
from unittest.mock import MagicMock, patch

# Mock webrtcvad if not installed locally
if 'webrtcvad' not in sys.modules:
    mock_vad = MagicMock()
    sys.modules['webrtcvad'] = mock_vad

from fastapi.testclient import TestClient
from fastapi.websockets import WebSocketDisconnect

import backend2_service
from backend2_service import app, WS_AUTH_TOKEN, rate_limiter

class TestWebSocketAuthAndRateLimit(unittest.TestCase):

    def setUp(self):
        self.client = TestClient(app)
        # Enable auth required for test suite
        backend2_service.WS_AUTH_REQUIRED = True
        # Reset rate limiter state before each test
        rate_limiter.active_connections.clear()
        rate_limiter.connection_history.clear()

        # Mock score_chunk so ML service doesn't need to be running
        self.patcher = patch('backend2_service.score_chunk', new_callable=MagicMock)
        self.mock_score = self.patcher.start()
        async def mock_score_func(wav_bytes):
            return {
                "decision": "real",
                "fused_score": 0.05,
                "explanation": "Speech is authentic.",
                "branch_scores": {"rawnet2": 0.05, "spectrogram": 0.04, "ssl": 0.06}
            }
        self.mock_score.side_effect = mock_score_func

    def tearDown(self):
        self.patcher.stop()

    def test_missing_token_rejected(self):
        """WebSocket connection without token should be rejected when WS_AUTH_REQUIRED=True."""
        with self.assertRaises((WebSocketDisconnect, Exception)):
            with self.client.websocket_connect("/ws/risk-stream"):
                pass

    def test_invalid_token_rejected(self):
        """WebSocket connection with invalid token should be rejected when WS_AUTH_REQUIRED=True."""
        with self.assertRaises((WebSocketDisconnect, Exception)):
            with self.client.websocket_connect("/ws/risk-stream?token=wrong-token"):
                pass

    def test_valid_token_query_param_success(self):
        """WebSocket connection with valid query param token should succeed."""
        with self.client.websocket_connect(f"/ws/risk-stream?token={WS_AUTH_TOKEN}") as websocket:
            data = websocket.receive_json()
            self.assertIn("decision", data)
            self.assertIn("fused_score", data)
            self.assertIn("log_hash", data)

    def test_valid_header_auth_success(self):
        """WebSocket connection with valid X-API-Key header should succeed."""
        headers = {"x-api-key": WS_AUTH_TOKEN}
        with self.client.websocket_connect("/ws/risk-stream", headers=headers) as websocket:
            data = websocket.receive_json()
            self.assertIn("decision", data)

    def test_rate_limit_exceeded(self):
        """Exceeding max connections frequency per IP should be blocked."""
        test_ip = "testclient"
        import time
        # Set max_per_minute to 5
        rate_limiter.max_per_minute = 5
        rate_limiter.connection_history[test_ip] = [time.time()] * 5

        # 6th connection attempt should be rate limited
        with self.assertRaises((WebSocketDisconnect, Exception)):
            with self.client.websocket_connect(f"/ws/risk-stream?token={WS_AUTH_TOKEN}"):
                pass

    def test_demo_mode_permissive(self):
        """When WS_AUTH_REQUIRED=False (demo mode), unauthenticated connections succeed."""
        backend2_service.WS_AUTH_REQUIRED = False
        with self.client.websocket_connect("/ws/risk-stream") as websocket:
            data = websocket.receive_json()
            self.assertIn("decision", data)


if __name__ == "__main__":
    unittest.main()
