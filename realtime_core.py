"""Shared realtime voice session helpers with noise-hardened VAD settings.

Local-only continuous mic/speaker path. Streamlit Cloud uses `voice_browser.py`
instead (browser mic via st.audio_input — no PortAudio required).
"""

from __future__ import annotations

import asyncio
import queue
import threading
from collections.abc import Callable
from dataclasses import dataclass, field
from typing import Any

import numpy as np
from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=True)

from agents.realtime import (
    RealtimeAgent,
    RealtimeInputAudioNoiseReductionConfig,
    RealtimeInputAudioTranscriptionConfig,
    RealtimeModelConfig,
    RealtimePlaybackTracker,
    RealtimeRunner,
    RealtimeSessionModelSettings,
    RealtimeTurnDetectionConfig,
)
from agents.realtime.items import AssistantMessageItem, UserMessageItem

try:
    import sounddevice as sd

    HAS_SOUNDDEVICE = True
except Exception:  # noqa: BLE001 — PortAudio missing on Streamlit Cloud
    sd = None  # type: ignore[assignment]
    HAS_SOUNDDEVICE = False


def _extract_message_text(item: Any) -> tuple[str | None, str]:
    """Return (role, text) from a history message item, if any."""
    role = getattr(item, "role", None)
    if role not in ("user", "assistant"):
        return None, ""
    parts: list[str] = []
    for entry in getattr(item, "content", []) or []:
        text = getattr(entry, "transcript", None) or getattr(entry, "text", None)
        if text:
            parts.append(str(text))
    return role, "".join(parts).strip()


SAMPLE_RATE = 24_000
MIC_RMS_THRESHOLD = 450
VAD_THRESHOLD = 0.72
VAD_SILENCE_MS = 850
VAD_PREFIX_PADDING_MS = 300


def build_agent(
    name: str = "Travel Advisor",
    instructions: str | None = None,
) -> RealtimeAgent:
    return RealtimeAgent(
        name=name,
        instructions=instructions
        or (
            "You are a friendly travel advisor. "
            "Give short, enthusiastic destination recommendations. "
            "Keep answers brief and conversational."
        ),
    )


def build_model_config(
    playback_tracker: RealtimePlaybackTracker,
    *,
    voice: str = "ash",
) -> RealtimeModelConfig:
    """Realtime config tuned to ignore ambient noise better than defaults."""
    return RealtimeModelConfig(
        initial_model_settings=RealtimeSessionModelSettings(
            model_name="gpt-realtime",
            voice=voice,
            input_audio_transcription=RealtimeInputAudioTranscriptionConfig(
                model="gpt-4o-mini-transcribe"
            ),
            input_audio_noise_reduction=RealtimeInputAudioNoiseReductionConfig(
                type="far_field"
            ),
            turn_detection=RealtimeTurnDetectionConfig(
                type="server_vad",
                threshold=VAD_THRESHOLD,
                prefix_padding_ms=VAD_PREFIX_PADDING_MS,
                silence_duration_ms=VAD_SILENCE_MS,
                interrupt_response=True,
                create_response=True,
            ),
        ),
        playback_tracker=playback_tracker,
    )


def _rms_int16(indata: np.ndarray) -> float:
    samples = indata.astype(np.float32).reshape(-1)
    if samples.size == 0:
        return 0.0
    return float(np.sqrt(np.mean(samples * samples)))


@dataclass
class SessionCallbacks:
    on_transcript: Callable[[str], None] = field(default=lambda _t: None)
    on_agent_end: Callable[[], None] = field(default=lambda: None)
    on_user_transcript: Callable[[str], None] = field(default=lambda _t: None)
    on_status: Callable[[str], None] = field(default=lambda _s: None)
    on_error: Callable[[Any], None] = field(default=lambda _e: None)
    should_stop: Callable[[], bool] = field(default=lambda: False)


async def run_realtime_session(
    agent: RealtimeAgent,
    callbacks: SessionCallbacks | None = None,
) -> None:
    """Open mic + speaker streams and run until stop or fatal error."""
    if not HAS_SOUNDDEVICE or sd is None:
        raise RuntimeError(
            "PortAudio / sounddevice is not available. "
            "Use the Streamlit browser-mic UI (streamlit_app.py) instead."
        )

    cb = callbacks or SessionCallbacks()
    loop = asyncio.get_running_loop()
    playback_tracker = RealtimePlaybackTracker()

    audio_queue: queue.Queue = queue.Queue()
    interrupt_event = threading.Event()
    current: dict[str, Any] = {"chunk": None, "pos": 0}

    def output_callback(outdata, frames, time, status):  # noqa: ARG001
        if interrupt_event.is_set():
            while not audio_queue.empty():
                try:
                    audio_queue.get_nowait()
                except queue.Empty:
                    break
            current["chunk"] = None
            current["pos"] = 0
            interrupt_event.clear()
            outdata.fill(0)
            return

        outdata.fill(0)
        filled = 0
        while filled < frames:
            if current["chunk"] is None:
                try:
                    current["chunk"] = audio_queue.get_nowait()
                    current["pos"] = 0
                except queue.Empty:
                    break
            samples, item_id, content_index = current["chunk"]
            pos = current["pos"]
            n = min(frames - filled, len(samples) - pos)
            outdata[filled : filled + n, 0] = samples[pos : pos + n]
            playback_tracker.on_play_bytes(
                item_id=item_id,
                item_content_index=content_index,
                bytes=samples[pos : pos + n].tobytes(),
            )
            filled += n
            current["pos"] = pos + n
            if current["pos"] >= len(samples):
                current["chunk"] = None

    model_config = build_model_config(playback_tracker)
    cb.on_status("connecting")

    async with await RealtimeRunner(agent).run(model_config=model_config) as session:
        cb.on_status("listening")
        emitted: dict[str, str] = {}

        def mic_callback(indata, frames, time, status):  # noqa: ARG001
            if _rms_int16(indata) < MIC_RMS_THRESHOLD:
                payload = np.zeros_like(indata).tobytes()
            else:
                payload = indata.tobytes()
            asyncio.run_coroutine_threadsafe(session.send_audio(payload), loop)

        def _emit_history_items(items: list[Any]) -> None:
            for item in items:
                if not isinstance(item, (UserMessageItem, AssistantMessageItem)):
                    continue
                role, text = _extract_message_text(item)
                item_id = getattr(item, "item_id", None) or id(item)
                if not text or emitted.get(str(item_id)) == text:
                    continue
                emitted[str(item_id)] = text
                if role == "user":
                    cb.on_user_transcript(text)
                elif role == "assistant":
                    cb.on_transcript(text)

        chunk_size = int(SAMPLE_RATE * 0.04)
        with sd.OutputStream(
            samplerate=SAMPLE_RATE,
            channels=1,
            dtype=np.int16,
            callback=output_callback,
            blocksize=chunk_size,
        ):
            with sd.InputStream(
                samplerate=SAMPLE_RATE,
                channels=1,
                dtype="int16",
                callback=mic_callback,
            ):
                async for event in session:
                    if cb.should_stop():
                        cb.on_status("stopped")
                        break

                    if event.type == "audio":
                        cb.on_status("speaking")
                        samples = np.frombuffer(event.audio.data, dtype=np.int16)
                        audio_queue.put(
                            (samples, event.audio.item_id, event.audio.content_index)
                        )
                    elif event.type == "audio_interrupted":
                        interrupt_event.set()
                        cb.on_status("listening")
                    elif event.type == "audio_end":
                        cb.on_status("listening")
                    elif event.type == "history_added":
                        _emit_history_items([event.item])
                    elif event.type == "history_updated":
                        _emit_history_items(list(event.history or []))
                    elif event.type == "agent_end":
                        cb.on_agent_end()
                        cb.on_status("listening")
                    elif event.type == "error":
                        cb.on_error(event.error)
                        cb.on_status("error")
                        break


def start_session_thread(
    agent: RealtimeAgent,
    callbacks: SessionCallbacks,
) -> tuple[threading.Thread, threading.Event]:
    """Run `run_realtime_session` on a daemon thread with its own event loop."""
    stop_event = threading.Event()
    original_stop = callbacks.should_stop
    callbacks.should_stop = lambda: stop_event.is_set() or original_stop()

    def _target() -> None:
        try:
            asyncio.run(run_realtime_session(agent, callbacks))
        except Exception as exc:  # noqa: BLE001
            callbacks.on_error(exc)
            callbacks.on_status("error")

    thread = threading.Thread(target=_target, name="realtime-voice", daemon=True)
    thread.start()
    return thread, stop_event
