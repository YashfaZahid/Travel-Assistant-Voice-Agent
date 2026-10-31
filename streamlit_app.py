"""Cute animated Streamlit UI for the realtime voice agent (Recenter-inspired)."""

from __future__ import annotations

import html
import os
import threading
from collections import deque
from dataclasses import dataclass, field

import streamlit as st

st.set_page_config(
    page_title="Travel Assistant · Voice Agent",
    page_icon=":material/spa:",
    layout="centered",
    initial_sidebar_state="collapsed",
)

# Shared page chrome (API key gate + main app)
st.html(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Nunito:wght@500;700;800&family=Caveat:wght@600&display=swap');

html, body, [data-testid="stAppViewContainer"] {
  background:
    linear-gradient(180deg, #E8F6EF 0%, #F4FBF7 45%, #EEF7F8 100%) !important;
}
[data-testid="stAppViewContainer"]::before {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background-image:
    linear-gradient(rgba(45,106,79,0.045) 1px, transparent 1px),
    linear-gradient(90deg, rgba(45,106,79,0.045) 1px, transparent 1px);
  background-size: 28px 28px;
  z-index: 0;
}
.block-container {
  padding-top: 1.5rem !important;
  max-width: 720px !important;
  position: relative;
  z-index: 1;
}
[data-testid="stHeader"] { background: transparent; }
h1.recenter-title {
  font-family: 'Nunito', sans-serif !important;
  font-weight: 800 !important;
  font-size: 2.6rem !important;
  letter-spacing: -0.03em;
  margin: 0.2rem 0 0.15rem 0 !important;
  color: #12241F !important;
}
.recenter-tag {
  font-family: 'Nunito', sans-serif;
  color: #5B746A;
  font-size: 1.05rem;
  margin-bottom: 1.1rem;
}
.api-card {
  border-radius: 28px;
  padding: 1.5rem 1.35rem 1.25rem;
  background: rgba(255,255,255,0.78);
  border: 1px solid rgba(255,255,255,0.95);
  box-shadow: 0 18px 40px rgba(27,67,50,0.12);
  backdrop-filter: blur(10px);
}
.api-blob {
  width: 96px; height: 96px; margin: 0 auto 0.75rem;
  border-radius: 50%;
  background: radial-gradient(circle at 35% 30%, #C8F5A8, #5BB83A);
  box-shadow: 0 12px 28px rgba(45,106,79,0.22);
  animation: floaty 3s ease-in-out infinite;
}
@keyframes floaty {
  0%, 100% { transform: translateY(0); }
  50% { transform: translateY(-8px); }
}
.stack-card {
  border-radius: 22px;
  padding: 0.85rem 1rem;
  margin: 0.55rem 0;
  box-shadow: 0 10px 28px rgba(27,67,50,0.08);
  border: 1px solid rgba(255,255,255,0.7);
}
.stack-yellow { background: linear-gradient(135deg, #FBF0C9, #F7E7A1); }
.stack-blue { background: linear-gradient(135deg, #D6E4F0, #C5D8EC); color: #2A3F55; }
.stack-label {
  font-family: 'Caveat', cursive;
  font-size: 1.15rem;
  opacity: 0.85;
}
.msg {
  border-radius: 18px;
  padding: 0.7rem 0.9rem;
  margin: 0.4rem 0;
  font-family: 'Nunito', sans-serif;
  font-size: 0.95rem;
  line-height: 1.45;
}
.msg-you {
  background: rgba(255,255,255,0.75);
  border: 1px solid #D8EDE1;
}
.msg-assistant {
  background: #D8F3DC;
  border: 1px solid #B7E4C7;
}
.msg-role {
  font-size: 0.72rem;
  font-weight: 800;
  text-transform: uppercase;
  letter-spacing: 0.04em;
  opacity: 0.65;
  margin-bottom: 0.2rem;
}
</style>
"""
)


def _api_key_page() -> None:
    st.markdown('<h1 class="recenter-title">Travel Assistant</h1>', unsafe_allow_html=True)
    st.markdown(
        '<div class="recenter-tag">Enter your OpenAI API key to start the voice agent</div>',
        unsafe_allow_html=True,
    )
    st.html('<div class="api-card"><div class="api-blob"></div></div>')

    with st.form("api_key_form", clear_on_submit=False):
        key = st.text_input(
            "OpenAI API key",
            type="password",
            placeholder="sk-...",
            help="Stored only in this browser session — never written to disk.",
        )
        submitted = st.form_submit_button(
            ":material/lock_open: Continue",
            type="primary",
            use_container_width=True,
        )

    if submitted:
        cleaned = (key or "").strip()
        if not cleaned:
            st.error("Please paste your OpenAI API key.")
        elif not cleaned.startswith("sk-"):
            st.error("That doesn't look like an OpenAI API key (expected to start with sk-).")
        else:
            st.session_state["openai_api_key"] = cleaned
            os.environ["OPENAI_API_KEY"] = cleaned
            st.rerun()

    st.caption("Get a key at [platform.openai.com/api-keys](https://platform.openai.com/api-keys).")


# ---------------------------------------------------------------------------
# API key gate — app only runs after a key is provided
# ---------------------------------------------------------------------------
if "openai_api_key" not in st.session_state:
    env_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if env_key.startswith("sk-"):
        st.session_state["openai_api_key"] = env_key
    else:
        _api_key_page()
        st.stop()

os.environ["OPENAI_API_KEY"] = st.session_state["openai_api_key"]

from realtime_core import SessionCallbacks, build_agent, start_session_thread  # noqa: E402

# ---------------------------------------------------------------------------
# Animated companion (Custom Components v2)
# ---------------------------------------------------------------------------
_COMPANION = st.components.v2.component(
    name="recenter_companion",
    html="""
    <div class="stage" id="stage">
      <div class="status-pill" id="status-pill">
        <span class="dot" id="dot"></span>
        <span id="status-label">Ready</span>
      </div>
      <div class="card">
        <div class="glow"></div>
        <div class="sparkles" aria-hidden="true">
          <span></span><span></span><span></span><span></span><span></span>
        </div>
        <div class="blob-wrap" id="blob-wrap">
          <svg class="blob" viewBox="0 0 220 220" xmlns="http://www.w3.org/2000/svg">
            <defs>
              <radialGradient id="g" cx="35%" cy="30%" r="70%">
                <stop offset="0%" stop-color="#C8F5A8"/>
                <stop offset="55%" stop-color="#8FD96A"/>
                <stop offset="100%" stop-color="#5BB83A"/>
              </radialGradient>
              <filter id="soft" x="-20%" y="-20%" width="140%" height="140%">
                <feGaussianBlur in="SourceAlpha" stdDeviation="2" result="b"/>
                <feOffset dy="4" result="o"/>
                <feMerge><feMergeNode in="o"/><feMergeNode in="SourceGraphic"/></feMerge>
              </filter>
            </defs>
            <ellipse cx="110" cy="118" rx="78" ry="72" fill="url(#g)" filter="url(#soft)"/>
            <ellipse cx="88" cy="78" rx="22" ry="14" fill="#E8FFD4" opacity="0.45"/>
            <ellipse class="eye" cx="88" cy="108" rx="7" ry="11" fill="#1A2E28"/>
            <ellipse class="eye" cx="132" cy="108" rx="7" ry="11" fill="#1A2E28"/>
            <path class="smile" d="M92 132 Q110 148 128 132" fill="none"
                  stroke="#1A2E28" stroke-width="4" stroke-linecap="round"/>
          </svg>
        </div>
        <div class="chip chip-left">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#1B4332"
               stroke-width="1.8"><path d="M12 3c-2 3-6 5-6 10a6 6 0 0012 0c0-5-4-7-6-10z"/>
          </svg>
          Think Clearer
        </div>
        <div class="chip chip-right">
          <svg width="16" height="16" viewBox="0 0 24 24" fill="none" stroke="#1B4332"
               stroke-width="1.8"><path d="M3 12h4l2-5 4 10 2-5h6"/></svg>
          Better Habits
        </div>
        <div class="note note-left">A calmer you</div>
        <div class="note note-right">Feel in control</div>
      </div>
    </div>
    """,
    css="""
    @import url('https://fonts.googleapis.com/css2?family=Nunito:wght@500;700;800&family=Caveat:wght@600&display=swap');

    :host, .stage {
      font-family: 'Nunito', system-ui, sans-serif;
      color: #1A2E28;
      width: 100%;
      display: block;
    }

    .stage { position: relative; padding: 0.25rem 0 0.5rem; }

    .status-pill {
      display: inline-flex;
      align-items: center;
      gap: 0.45rem;
      background: rgba(255,255,255,0.72);
      backdrop-filter: blur(10px);
      border: 1px solid rgba(255,255,255,0.9);
      border-radius: 999px;
      padding: 0.35rem 0.75rem;
      font-size: 0.82rem;
      font-weight: 700;
      box-shadow: 0 6px 18px rgba(27,67,50,0.08);
      margin-bottom: 0.75rem;
    }
    .dot {
      width: 8px; height: 8px; border-radius: 50%;
      background: #95A5A0;
      box-shadow: 0 0 0 0 rgba(45,106,79,0.4);
    }
    .stage[data-state="listening"] .dot,
    .stage[data-state="speaking"] .dot,
    .stage[data-state="connecting"] .dot {
      background: #2D6A4F;
      animation: pulse-dot 1.6s ease-out infinite;
    }
    .stage[data-state="error"] .dot { background: #C0392B; }
    .stage[data-state="stopped"] .dot,
    .stage[data-state="idle"] .dot { background: #95A5A0; animation: none; }

    .card {
      position: relative;
      border-radius: 28px;
      overflow: hidden;
      min-height: 320px;
      background:
        radial-gradient(ellipse at 50% 35%, #DDF7C5 0%, #BFE8A8 42%, #9ED68A 100%);
      box-shadow:
        0 20px 50px rgba(45,106,79,0.16),
        inset 0 1px 0 rgba(255,255,255,0.55);
      display: grid;
      place-items: center;
    }

    .glow {
      position: absolute; inset: 18% 22%;
      background: radial-gradient(circle, rgba(255,255,255,0.55), transparent 70%);
      filter: blur(8px);
      pointer-events: none;
    }

    .blob-wrap {
      width: min(220px, 58vw);
      z-index: 2;
      animation: floaty 3.4s ease-in-out infinite;
      transform-origin: 50% 60%;
    }
    .stage[data-state="listening"] .blob-wrap {
      animation: floaty 3.4s ease-in-out infinite, breathe 1.8s ease-in-out infinite;
    }
    .stage[data-state="speaking"] .blob-wrap {
      animation: talk 0.55s ease-in-out infinite;
    }
    .stage[data-state="connecting"] .blob-wrap {
      animation: floaty 2s ease-in-out infinite, wobble 1.2s ease-in-out infinite;
    }

    .eye { transform-origin: center; animation: blink 5.5s infinite; }

    .sparkles span {
      position: absolute;
      width: 10px; height: 10px;
      background: white;
      clip-path: polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%);
      opacity: 0.85;
      animation: twinkle 2.8s ease-in-out infinite;
      z-index: 3;
    }
    .sparkles span:nth-child(1) { top: 18%; left: 22%; animation-delay: 0s; }
    .sparkles span:nth-child(2) { top: 28%; right: 18%; animation-delay: 0.4s; }
    .sparkles span:nth-child(3) { bottom: 26%; left: 18%; animation-delay: 0.9s; }
    .sparkles span:nth-child(4) { top: 14%; right: 34%; animation-delay: 1.3s; width: 7px; height: 7px; }
    .sparkles span:nth-child(5) { bottom: 20%; right: 26%; animation-delay: 1.7s; width: 8px; height: 8px; }

    .chip {
      position: absolute;
      z-index: 4;
      display: inline-flex;
      align-items: center;
      gap: 0.4rem;
      padding: 0.45rem 0.75rem;
      border-radius: 999px;
      background: rgba(255,255,255,0.55);
      backdrop-filter: blur(12px);
      border: 1px solid rgba(255,255,255,0.75);
      font-size: 0.78rem;
      font-weight: 700;
      box-shadow: 0 8px 20px rgba(27,67,50,0.1);
      animation: chip-float 4s ease-in-out infinite;
    }
    .chip-left { left: 6%; top: 38%; animation-delay: 0.2s; }
    .chip-right { right: 5%; top: 48%; animation-delay: 0.8s; }

    .note {
      position: absolute;
      z-index: 4;
      font-family: 'Caveat', cursive;
      font-size: 1.25rem;
      color: #2D6A4F;
      opacity: 0.9;
    }
    .note-left { left: 8%; bottom: 14%; transform: rotate(-6deg); }
    .note-right { right: 8%; bottom: 18%; transform: rotate(5deg); }

    @keyframes floaty {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-10px); }
    }
    @keyframes breathe {
      0%, 100% { transform: translateY(0) scale(1); }
      50% { transform: translateY(-8px) scale(1.04); }
    }
    @keyframes talk {
      0%, 100% { transform: translateY(0) scale(1, 1); }
      50% { transform: translateY(-4px) scale(1.05, 0.96); }
    }
    @keyframes wobble {
      0%, 100% { transform: rotate(-2deg); }
      50% { transform: rotate(2deg); }
    }
    @keyframes blink {
      0%, 46%, 50%, 100% { transform: scaleY(1); }
      48% { transform: scaleY(0.1); }
    }
    @keyframes twinkle {
      0%, 100% { opacity: 0.25; transform: scale(0.7) rotate(0deg); }
      50% { opacity: 1; transform: scale(1.15) rotate(20deg); }
    }
    @keyframes chip-float {
      0%, 100% { transform: translateY(0); }
      50% { transform: translateY(-6px); }
    }
    @keyframes pulse-dot {
      0% { box-shadow: 0 0 0 0 rgba(45,106,79,0.45); }
      70% { box-shadow: 0 0 0 8px rgba(45,106,79,0); }
      100% { box-shadow: 0 0 0 0 rgba(45,106,79,0); }
    }

    @media (max-width: 520px) {
      .chip { display: none; }
      .note { font-size: 1.05rem; }
      .card { min-height: 280px; }
    }
    """,
    js="""
export default function (component) {
  const { data, parentElement } = component;
  const stage = parentElement.querySelector('#stage');
  const label = parentElement.querySelector('#status-label');
  if (!stage) return;

  const state = (data && data.state) || 'idle';
  const labels = {
    idle: 'Ready when you are',
    connecting: 'Waking up…',
    listening: 'Active now',
    speaking: 'Talking…',
    stopped: 'Paused',
    error: 'Something went wrong',
  };
  stage.setAttribute('data-state', state);
  if (label) label.textContent = labels[state] || state;
}
""",
)


def companion(state: str = "idle", *, key: str | None = None) -> None:
    _COMPANION(data={"state": state}, key=key, height="auto")


# ---------------------------------------------------------------------------
# Shared runtime state (survives Streamlit reruns via session_state)
# ---------------------------------------------------------------------------
@dataclass
class VoiceRuntime:
    status: str = "idle"
    stop_event: threading.Event | None = None
    thread: threading.Thread | None = None
    lock: threading.Lock = field(default_factory=threading.Lock)
    lines: deque[tuple[str, str]] = field(default_factory=lambda: deque(maxlen=40))
    error: str | None = None


def _get_runtime() -> VoiceRuntime:
    if "voice_runtime" not in st.session_state:
        st.session_state.voice_runtime = VoiceRuntime()
    return st.session_state.voice_runtime


def _start_voice() -> None:
    rt = _get_runtime()
    if rt.thread and rt.thread.is_alive():
        return

    rt.error = None
    rt.status = "connecting"

    def on_status(status: str) -> None:
        with rt.lock:
            rt.status = status

    def on_transcript(text: str) -> None:
        with rt.lock:
            if rt.lines and rt.lines[-1][0] == "assistant":
                rt.lines[-1] = ("assistant", text)
            else:
                rt.lines.append(("assistant", text))

    def on_user_transcript(text: str) -> None:
        with rt.lock:
            rt.lines.append(("you", text))

    def on_error(err: object) -> None:
        with rt.lock:
            rt.error = str(err)
            rt.status = "error"

    agent = build_agent(
        name="Travel Assistant",
        instructions=(
            "You are a friendly travel assistant and calming companion. "
            "Give short, enthusiastic destination tips and gentle conversation. "
            "Keep spoken answers to 1-3 sentences."
        ),
    )
    thread, stop_event = start_session_thread(
        agent,
        SessionCallbacks(
            on_status=on_status,
            on_transcript=on_transcript,
            on_user_transcript=on_user_transcript,
            on_error=on_error,
        ),
    )
    rt.thread = thread
    rt.stop_event = stop_event


def _stop_voice() -> None:
    rt = _get_runtime()
    if rt.stop_event is not None:
        rt.stop_event.set()
    with rt.lock:
        rt.status = "stopped"


# ---------------------------------------------------------------------------
# Main voice app
# ---------------------------------------------------------------------------
top_l, top_r = st.columns([4, 1])
with top_l:
    st.markdown('<h1 class="recenter-title">Travel Assistant</h1>', unsafe_allow_html=True)
    st.markdown(
        '<div class="recenter-tag">Your calm travel voice companion</div>',
        unsafe_allow_html=True,
    )
with top_r:
    if st.button(":material/key: Key", help="Change API key", use_container_width=True):
        if "voice_runtime" in st.session_state:
            _stop_voice()
        st.session_state.pop("openai_api_key", None)
        st.rerun()

@st.fragment(run_every="1s")
def companion_panel() -> None:
    rt = _get_runtime()
    with rt.lock:
        status = rt.status
    companion(status, key="companion_blob")


companion_panel()

col_a, col_b = st.columns(2)
with col_a:
    st.html(
        '<div class="stack-card stack-yellow">'
        '<div class="stack-label">Build better days</div>'
        "<div>Soft check-ins and gentle travel daydreams.</div></div>"
    )
with col_b:
    st.html(
        '<div class="stack-card stack-blue">'
        '<div class="stack-label">Feel in control</div>'
        "<div>Noise-hardened listening — speaks when you do.</div></div>"
    )


@st.fragment(run_every="1s")
def controls_and_chat() -> None:
    rt = _get_runtime()
    alive = bool(rt.thread and rt.thread.is_alive())
    with rt.lock:
        lines = list(rt.lines)
        err = rt.error
        status = rt.status

    # If the worker exited without a clean Pause, reset status so Start works.
    if not alive and status in ("listening", "speaking", "connecting"):
        with rt.lock:
            if rt.status in ("listening", "speaking", "connecting"):
                rt.status = "stopped" if rt.error is None else "error"

    btn_l, btn_r = st.columns([1, 1])
    with btn_l:
        start = st.button(
            ":material/mic: Get started",
            type="primary",
            use_container_width=True,
            disabled=alive,
            key="start_btn",
        )
    with btn_r:
        stop = st.button(
            ":material/stop_circle: Pause",
            use_container_width=True,
            disabled=not alive,
            key="stop_btn",
        )

    if start:
        _start_voice()
        st.rerun()
    if stop:
        _stop_voice()
        st.rerun()

    if err:
        st.error(err)

    st.subheader("Conversation")
    if not lines:
        st.caption("Press **Get started**, then talk — your companion is listening.")
        return

    for role, text in lines[-12:]:
        css = "msg-you" if role == "you" else "msg-assistant"
        label = "You" if role == "you" else "Assistant"
        safe = html.escape(text)
        st.html(
            f'<div class="msg {css}"><div class="msg-role">{label}</div>{safe}</div>'
        )


controls_and_chat()
