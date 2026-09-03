"""
audio_chunker.py
Backend 2 — VAD + sliding-window chunking for the streaming pipeline.

Takes raw 16kHz mono PCM audio arriving in small pieces (e.g. from a live
call), detects speech with WebRTC VAD, and yields fixed-length windows
(default 2s, matching the 1-4s range in the team plan) re-scored on a
sliding cadence (default 300ms, matching the 200-500ms re-scoring cadence).
"""

import collections
import webrtcvad
import numpy as np

SAMPLE_RATE = 16000          # Hz - matches Backend 1's model input
FRAME_DURATION_MS = 30       # webrtcvad requires 10, 20, or 30ms frames
BYTES_PER_SAMPLE = 2         # 16-bit PCM

# Fix Issue #28: Ensure float division before int conversion for accurate frame sample count
FRAME_SIZE = int(SAMPLE_RATE * (float(FRAME_DURATION_MS) / 1000.0)) * BYTES_PER_SAMPLE

WINDOW_SECONDS = 2.0          # length of each scored window (1-4s range in plan)
SLIDE_MS = 300                # how often we emit a new window (200-500ms range in plan)

VAD_AGGRESSIVENESS = 2        # 0 (least aggressive) to 3 (most aggressive filtering)


class StreamChunker:
    """
    Feed raw PCM bytes in with .add_audio(), and pull ready-to-score
    windows out with .get_ready_windows(). Call add_audio() as data
    arrives from your live call source (VoIP session / IVR / mock stream).
    """

    def __init__(self):
        self.vad = webrtcvad.Vad(VAD_AGGRESSIVENESS)
        self._byte_buffer = bytearray()
        self._pcm_history = collections.deque()   # (bytes frame, is_speech)
        self._bytes_since_last_window = 0
        self.window_size_bytes = int(WINDOW_SECONDS * SAMPLE_RATE) * BYTES_PER_SAMPLE
        
        # Fix Issue #28: Float arithmetic for accurate slide interval sizing
        self.slide_size_bytes = int(SAMPLE_RATE * (float(SLIDE_MS) / 1000.0)) * BYTES_PER_SAMPLE

    def add_audio(self, pcm_bytes: bytes):
        """Feed raw 16kHz 16-bit mono PCM bytes into the buffer."""
        self._byte_buffer.extend(pcm_bytes)
        self._process_complete_frames()

    def _process_complete_frames(self):
        while len(self._byte_buffer) >= FRAME_SIZE:
            frame = bytes(self._byte_buffer[:FRAME_SIZE])
            del self._byte_buffer[:FRAME_SIZE]
            try:
                is_speech = self.vad.is_speech(frame, SAMPLE_RATE)
            except Exception:
                is_speech = False
            self._pcm_history.append((frame, is_speech))
            self._bytes_since_last_window += FRAME_SIZE

    def get_ready_windows(self):
        """
        Returns a list of (audio_bytes, has_speech) tuples for any windows
        that are ready to be scored, based on the sliding cadence.
        Call this after add_audio() on every chunk of incoming data.
        """
        windows = []
        total_buffered = sum(len(f) for f, _ in self._pcm_history)

        while (total_buffered >= self.window_size_bytes
               and self._bytes_since_last_window >= self.slide_size_bytes):
            frames = list(self._pcm_history)[-int(self.window_size_bytes / FRAME_SIZE):]
            audio_bytes = b"".join(f for f, _ in frames)
            has_speech = any(is_speech for _, is_speech in frames)
            windows.append((audio_bytes, has_speech))

            self._bytes_since_last_window -= self.slide_size_bytes

            # cap history so memory doesn't grow unbounded on a long call
            max_history_bytes = self.window_size_bytes * 3
            while sum(len(f) for f, _ in self._pcm_history) > max_history_bytes:
                self._pcm_history.popleft()

            total_buffered = sum(len(f) for f, _ in self._pcm_history)

        return windows

    def pcm_to_wav_bytes(self, pcm_bytes: bytes) -> bytes:
        """
        Wraps raw PCM in a minimal WAV header so it can be sent to
        Backend 1's /detect endpoint, which expects a loadable audio file.
        """
        import io
        import wave
        buf = io.BytesIO()
        with wave.open(buf, "wb") as wf:
            wf.setnchannels(1)
            wf.setsampwidth(BYTES_PER_SAMPLE)
            wf.setframerate(SAMPLE_RATE)
            wf.writeframes(pcm_bytes)
        return buf.getvalue()