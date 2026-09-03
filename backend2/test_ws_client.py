"""
test_ws_client.py
Connects to Backend 2's WebSocket stream like Frontend's useRiskStream.js
would, and prints each decision object as it arrives - proving the
contract shape and live streaming both work.
"""

import asyncio
import json
import websockets

WS_URL = "ws://localhost:8002/ws/risk-stream?token=dev-ws-token-voiceshield"


async def main():
    async with websockets.connect(WS_URL) as ws:
        print(f"Connected to {WS_URL}\n")
        count = 0
        async for message in ws:
            data = json.loads(message)
            count += 1
            print(f"[{count}] decision={data['decision']:15s} "
                  f"fused_score={data['fused_score']:.3f} "
                  f"challenge_type={data['challenge_type']:10s} "
                  f"log_hash={data['log_hash']}")
            if count >= 8:
                print("\nReceived 8 messages - contract shape confirmed. Closing.")
                break

asyncio.run(main())