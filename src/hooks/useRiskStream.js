import { useState, useEffect, useRef } from "react";

import {
  mockDecision,
  demoRealDecision,
  demoCloneDecision
} from "../fixtures/decisions";

const USE_MOCK = false;
const AUTH_TOKEN = "voiceshield_demo_token_2026";
const SOCKET_URL = `ws://127.0.0.1:8000/ws/risk-stream?token=${AUTH_TOKEN}`;
const ANALYZE_URL = "http://127.0.0.1:8002/analyze";

export function useRiskStream() {
  const [decision, setDecision] = useState(mockDecision);
  const [status, setStatus] = useState(
    USE_MOCK ? "mock" : "connecting"
  );
  const [isAnalyzing, setIsAnalyzing] = useState(false);

  const wsRef = useRef(null);

  useEffect(() => {
    if (USE_MOCK) {
      return;
    }

    const ws = new WebSocket(SOCKET_URL);
    wsRef.current = ws;

    ws.onopen = () => {
      setStatus("connected");
    };

    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);
        if (data.error) {
          console.warn("Server rate limit warning:", data.error);
          return;
        }
        setDecision(data);
      } catch (err) {
        console.error("Failed to parse risk stream message:", err);
      }
    };

    ws.onerror = () => {
      setStatus("error");
    };

    ws.onclose = () => {
      setStatus("error");
    };

    return () => {
      if (ws.readyState === WebSocket.OPEN || ws.readyState === WebSocket.CONNECTING) {
        ws.close();
      }
    };
  }, []);

  // ===============================
  // DEMO CONTROLS
  // ===============================

  const setDemoScenario = (scenario) => {
    // 1. Send live scenario trigger payload to FastAPI backend over WebSocket
    if (wsRef.current && wsRef.current.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify({ scenario }));
    }

    // 2. Optimistically update local state as fallback
    if (scenario === "real") {
      setDecision({
        ...demoRealDecision,
        timestamp: new Date().toISOString()
      });
    } else if (scenario === "clone") {
      setDecision({
        ...demoCloneDecision,
        timestamp: new Date().toISOString()
      });
    }
  };

  // ===============================
  // REAL AUDIO UPLOAD (Backend 2 /analyze)
  // ===============================

  const analyzeUploadedFile = async (file) => {
    setIsAnalyzing(true);
    try {
      const formData = new FormData();
      formData.append("file", file);

      const response = await fetch(ANALYZE_URL, {
        method: "POST",
        body: formData,
      });

      if (!response.ok) {
        const err = await response.json();
        throw new Error(err.detail || "Analysis failed");
      }

      const { windows } = await response.json();

      // Play back the real per-window results like a live stream,
      // matching the same ~300ms cadence as the WebSocket.
      for (const windowResult of windows) {
        setDecision({ ...windowResult, timestamp: new Date().toISOString() });
        await new Promise((resolve) => setTimeout(resolve, 300));
      }
    } catch (err) {
      console.error("Failed to analyze uploaded file:", err);
    } finally {
      setIsAnalyzing(false);
    }
  };

  return {
    decision,
    status,
    setDemoScenario,
    analyzeUploadedFile,
    isAnalyzing
  };
}