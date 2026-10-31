"""Browser-mic voice turns (Streamlit Cloud safe — no PortAudio / sounddevice)."""

from __future__ import annotations

import asyncio
import io
import wave
from typing import Any

import numpy as np
from agents import Agent
from agents.voice import (
    AudioInput,
    SingleAgentVoiceWorkflow,
    TTSModelSettings,
    VoicePipeline,
    VoicePipelineConfig,
)

SAMPLE_RATE = 24_000

INSTRUCTIONS = (
    "You are a friendly travel assistant and calming companion. "
    "Give short, enthusiastic destination tips and gentle conversation. "
    "Keep spoken answers to 1-3 sentences."
)


def wav_file_to_pcm16(file_obj: Any, *, target_rate: int = SAMPLE_RATE) -> np.ndarray:
    """Decode a WAV upload (e.g. st.audio_input) to mono int16 PCM."""
    raw = file_obj.read() if hasattr(file_obj, "read") else file_obj
    if hasattr(file_obj, "seek"):
        try:
            file_obj.seek(0)
        except Exception:  # noqa: BLE001
            pass

    with wave.open(io.BytesIO(raw), "rb") as wf:
        channels = wf.getnchannels()
        sampwidth = wf.getsampwidth()
        rate = wf.getframerate()
        frames = wf.readframes(wf.getnframes())

    if sampwidth != 2:
        raise ValueError(f"Expected 16-bit WAV, got sample width {sampwidth}")

    samples = np.frombuffer(frames, dtype=np.int16)
    if channels > 1:
        samples = samples.reshape(-1, channels).mean(axis=1).astype(np.int16)

    if rate != target_rate and samples.size:
        # Linear resample — good enough for speech turns.
        duration = samples.shape[0] / float(rate)
        new_len = max(1, int(duration * target_rate))
        x_old = np.linspace(0.0, 1.0, num=samples.shape[0], endpoint=False)
        x_new = np.linspace(0.0, 1.0, num=new_len, endpoint=False)
        samples = np.interp(x_new, x_old, samples.astype(np.float32)).astype(np.int16)

    return samples


def pcm16_to_wav_bytes(pcm: np.ndarray | bytes, *, rate: int = SAMPLE_RATE) -> bytes:
    if isinstance(pcm, np.ndarray):
        data = pcm.astype(np.int16).tobytes()
    else:
        data = pcm
    buf = io.BytesIO()
    with wave.open(buf, "wb") as wf:
        wf.setnchannels(1)
        wf.setsampwidth(2)
        wf.setframerate(rate)
        wf.writeframes(data)
    return buf.getvalue()


def build_voice_pipeline() -> VoicePipeline:
    agent = Agent(
        name="Travel Assistant",
        instructions=INSTRUCTIONS,
        model="gpt-4o-mini",
    )
    return VoicePipeline(
        workflow=SingleAgentVoiceWorkflow(agent),
        config=VoicePipelineConfig(
            tts_settings=TTSModelSettings(voice="coral"),
            trace_include_sensitive_audio_data=False,
        ),
    )


async def run_voice_turn_async(pcm: np.ndarray) -> tuple[str, bytes]:
    """Run one STT → agent → TTS turn. Returns (assistant_text, wav_bytes)."""
    pipeline = build_voice_pipeline()
    result = await pipeline.run(AudioInput(buffer=pcm.astype(np.int16)))

    chunks: list[np.ndarray] = []
    async for event in result.stream():
        if event.type == "voice_stream_event_audio" and event.data is not None:
            data = event.data
            if isinstance(data, np.ndarray):
                chunks.append(data.reshape(-1))
            else:
                chunks.append(np.frombuffer(data, dtype=np.int16))

    if chunks:
        audio = np.concatenate(chunks).astype(np.int16)
    else:
        audio = np.zeros(0, dtype=np.int16)

    text = (getattr(result, "total_output_text", None) or "").strip()
    return text, pcm16_to_wav_bytes(audio)


def run_voice_turn(pcm: np.ndarray) -> tuple[str, bytes]:
    return asyncio.run(run_voice_turn_async(pcm))
