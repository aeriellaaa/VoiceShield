import { useState, useEffect, useRef } from "react";

import {
  mockDecision,
  demoRealDecision,
  demoCloneDecision
} from "../fixtures/decisions";

const USE_MOCK = false;
const WS_TOKEN = import.meta.env.VITE_WS_TOKEN || "dev-ws-token-voiceshield";
const SOCKET_URL = `ws://127.0.0.1:8002/ws/risk-stream?token=${WS_TOKEN}`;


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

    const ws = new WebSocket('ws://127.0.0.1:8000/ws/risk-stream');

    wsRef.current = ws;


    ws.onopen = () => {
      setStatus("connected");
    };


    ws.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data);

        setDecision(data);

      } catch (err) {
        console.error(
          "Failed to parse risk stream message:",
          err
        );
      }
    };


    ws.onerror = () => {
      setStatus("error");
    };


    ws.onclose = () => {
      setStatus("error");
    };


    return () => ws.close();

  }, []);


  // ===============================
  // DEMO CONTROLS
  // ===============================

  const setDemoScenario = (scenario) => {

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