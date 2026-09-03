import { useState, useEffect, useRef } from "react";

import {
  mockDecision,
  demoRealDecision,
  demoCloneDecision
} from "../fixtures/decisions";

const USE_MOCK = false;
const AUTH_TOKEN = "voiceshield_demo_token_2026";
const SOCKET_URL = `ws://127.0.0.1:8000/ws/risk-stream?token=${AUTH_TOKEN}`;

export function useRiskStream() {
  const [decision, setDecision] = useState(mockDecision);
  const [status, setStatus] = useState(
    USE_MOCK ? "mock" : "connecting"
  );

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

  return {
    decision,
    status,
    setDemoScenario
  };
}