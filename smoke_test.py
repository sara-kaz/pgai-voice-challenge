"""
Local smoke test: connects to our own /media-stream endpoint the same way
Twilio would, without making a real phone call. Costs a few seconds of
OpenAI Realtime usage (cents) instead of a full Twilio call — useful for
verifying the bridge server works before spending money on a real call.

Usage: start the server (`uvicorn app.server:app --port 8000`), then run
`python smoke_test.py` in another terminal.
"""
import asyncio
import base64
import json

import websockets

CALL_SID = "SMOKETEST123"
URL = f"ws://localhost:8000/media-stream/{CALL_SID}"


async def main():
    async with websockets.connect(URL) as ws:
        await ws.send(json.dumps({
            "event": "start",
            "start": {"streamSid": "MZsmoketest"},
        }))

        # ~1s of silent mu-law audio (0xFF is silence in u-law) so the
        # server's media-handling path gets exercised even with no mic.
        silence = base64.b64encode(b"\xff" * 800).decode()
        for _ in range(5):
            await ws.send(json.dumps({
                "event": "media",
                "media": {"payload": silence},
            }))
            await asyncio.sleep(0.2)

        got_audio_back = False
        try:
            # Wait long enough for the model to finish its full opening
            # line (not just the first chunk) so the transcript's "done"
            # event has time to fire before we cut the call short.
            for _ in range(40):
                raw = await asyncio.wait_for(ws.recv(), timeout=1)
                msg = json.loads(raw)
                if msg.get("event") == "media":
                    got_audio_back = True
        except asyncio.TimeoutError:
            pass

        print("got_audio_back:", got_audio_back)
        await ws.send(json.dumps({"event": "stop"}))


if __name__ == "__main__":
    asyncio.run(main())
