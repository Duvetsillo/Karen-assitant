"""One neural Spanish utterance through Edge TTS; audio stays in pipes."""
import asyncio
import base64
import json
import sys

import edge_tts


async def synthesize(text):
    speaker = edge_tts.Communicate(
        text, voice="es-MX-DaliaNeural", rate="+8%", pitch="+0Hz",
        connect_timeout=10, receive_timeout=25,
    )
    chunks = []
    async for item in speaker.stream():
        if item["type"] == "audio":
            chunks.append(item["data"])
    return b"".join(chunks)


def main():
    request = json.loads(sys.stdin.read())
    text = request.get("text")
    if not isinstance(text, str) or not text.strip() or len(text) > 4096:
        raise ValueError("Invalid speech text")
    audio = asyncio.run(synthesize(text))
    if not audio or len(audio) > 24_000_000:
        raise ValueError("Invalid neural audio")
    sys.stdout.write(base64.b64encode(audio).decode("ascii"))


if __name__ == "__main__":
    main()
