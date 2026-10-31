"""Mint short-lived OpenAI Realtime client secrets for browser WebRTC."""

from __future__ import annotations

import json
import urllib.error
import urllib.request

INSTRUCTIONS = (
    "You are an expert travel voice companion — warm, witty, and highly conversational, "
    "like chatting with a knowledgeable friend. "
    "You are great at destinations, itineraries, food, visas, budgets, and packing. "
    "Also joke, banter, and occasionally sing a short playful travel jingle when it fits. "
    "Keep spoken turns natural and concise unless the user wants depth. "
    "Always respond; never go silent after the user speaks."
)

SESSION_BODY = {
    "expires_after": {"anchor": "created_at", "seconds": 3600},
    "session": {
        "type": "realtime",
        "model": "gpt-realtime",
        "instructions": INSTRUCTIONS,
        "audio": {
            "input": {
                "noise_reduction": {"type": "far_field", "strength": 0.9},
                "transcription": {"model": "gpt-4o-mini-transcribe"},
                "turn_detection": {
                    "type": "server_vad",
                    "threshold": 0.65,
                    "prefix_padding_ms": 300,
                    "silence_duration_ms": 650,
                    "create_response": True,
                    "interrupt_response": True,
                },
            },
            "output": {"voice": "coral"},
        },
    },
}


def mint_realtime_client_secret(api_key: str) -> str:
    """Return an ephemeral `ek_...` token for browser WebRTC."""
    req = urllib.request.Request(
        "https://api.openai.com/v1/realtime/client_secrets",
        data=json.dumps(SESSION_BODY).encode("utf-8"),
        headers={
            "Authorization": f"Bearer {api_key}",
            "Content-Type": "application/json",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=30) as resp:
            payload = json.loads(resp.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        detail = exc.read().decode("utf-8", errors="replace")
        raise RuntimeError(f"Failed to mint realtime token ({exc.code}): {detail}") from exc

    value = payload.get("value")
    if not value:
        raise RuntimeError(f"Unexpected client_secrets response: {payload}")
    return str(value)
