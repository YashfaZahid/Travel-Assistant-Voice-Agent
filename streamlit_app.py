"""Cute animated Streamlit travel voice agent — continuous browser mic."""

from __future__ import annotations

import html
import os
import time
from collections import deque

import streamlit as st

st.set_page_config(
    page_title="Travel Assistant · Voice Agent",
    page_icon=":material/spa:",
    layout="centered",
    initial_sidebar_state="collapsed",
)

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


if "openai_api_key" not in st.session_state:
    env_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if env_key.startswith("sk-"):
        st.session_state["openai_api_key"] = env_key
    else:
        _api_key_page()
        st.stop()

os.environ["OPENAI_API_KEY"] = st.session_state["openai_api_key"]

from voice_browser import (  # noqa: E402
    SAMPLE_RATE,
    b64_wav_to_pcm16,
    run_voice_turn,
)

# ---------------------------------------------------------------------------
# Animated companion
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
    :host, .stage { font-family: 'Nunito', system-ui, sans-serif; color: #1A2E28; width: 100%; display: block; }
    .stage { position: relative; padding: 0.25rem 0 0.5rem; }
    .status-pill {
      display: inline-flex; align-items: center; gap: 0.45rem;
      background: rgba(255,255,255,0.72); backdrop-filter: blur(10px);
      border: 1px solid rgba(255,255,255,0.9); border-radius: 999px;
      padding: 0.35rem 0.75rem; font-size: 0.82rem; font-weight: 700;
      box-shadow: 0 6px 18px rgba(27,67,50,0.08); margin-bottom: 0.75rem;
    }
    .dot { width: 8px; height: 8px; border-radius: 50%; background: #95A5A0; }
    .stage[data-state="listening"] .dot,
    .stage[data-state="speaking"] .dot,
    .stage[data-state="connecting"] .dot {
      background: #2D6A4F; animation: pulse-dot 1.6s ease-out infinite;
    }
    .stage[data-state="error"] .dot { background: #C0392B; }
    .card {
      position: relative; border-radius: 28px; overflow: hidden; min-height: 320px;
      background: radial-gradient(ellipse at 50% 35%, #DDF7C5 0%, #BFE8A8 42%, #9ED68A 100%);
      box-shadow: 0 20px 50px rgba(45,106,79,0.16), inset 0 1px 0 rgba(255,255,255,0.55);
      display: grid; place-items: center;
    }
    .glow {
      position: absolute; inset: 18% 22%;
      background: radial-gradient(circle, rgba(255,255,255,0.55), transparent 70%);
      filter: blur(8px); pointer-events: none;
    }
    .blob-wrap {
      width: min(220px, 58vw); z-index: 2;
      animation: floaty 3.4s ease-in-out infinite; transform-origin: 50% 60%;
    }
    .stage[data-state="listening"] .blob-wrap {
      animation: floaty 3.4s ease-in-out infinite, breathe 1.8s ease-in-out infinite;
    }
    .stage[data-state="speaking"] .blob-wrap { animation: talk 0.55s ease-in-out infinite; }
    .stage[data-state="connecting"] .blob-wrap {
      animation: floaty 2s ease-in-out infinite, wobble 1.2s ease-in-out infinite;
    }
    .eye { transform-origin: center; animation: blink 5.5s infinite; }
    .sparkles span {
      position: absolute; width: 10px; height: 10px; background: white;
      clip-path: polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%);
      opacity: 0.85; animation: twinkle 2.8s ease-in-out infinite; z-index: 3;
    }
    .sparkles span:nth-child(1) { top: 18%; left: 22%; }
    .sparkles span:nth-child(2) { top: 28%; right: 18%; animation-delay: 0.4s; }
    .sparkles span:nth-child(3) { bottom: 26%; left: 18%; animation-delay: 0.9s; }
    .sparkles span:nth-child(4) { top: 14%; right: 34%; animation-delay: 1.3s; width: 7px; height: 7px; }
    .sparkles span:nth-child(5) { bottom: 20%; right: 26%; animation-delay: 1.7s; width: 8px; height: 8px; }
    .chip {
      position: absolute; z-index: 4; display: inline-flex; align-items: center; gap: 0.4rem;
      padding: 0.45rem 0.75rem; border-radius: 999px; background: rgba(255,255,255,0.55);
      backdrop-filter: blur(12px); border: 1px solid rgba(255,255,255,0.75);
      font-size: 0.78rem; font-weight: 700; box-shadow: 0 8px 20px rgba(27,67,50,0.1);
      animation: chip-float 4s ease-in-out infinite;
    }
    .chip-left { left: 6%; top: 38%; }
    .chip-right { right: 5%; top: 48%; animation-delay: 0.8s; }
    .note {
      position: absolute; z-index: 4; font-family: 'Caveat', cursive;
      font-size: 1.25rem; color: #2D6A4F; opacity: 0.9;
    }
    .note-left { left: 8%; bottom: 14%; transform: rotate(-6deg); }
    .note-right { right: 8%; bottom: 18%; transform: rotate(5deg); }
    @keyframes floaty { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-10px); } }
    @keyframes breathe {
      0%, 100% { transform: translateY(0) scale(1); }
      50% { transform: translateY(-8px) scale(1.04); }
    }
    @keyframes talk {
      0%, 100% { transform: translateY(0) scale(1, 1); }
      50% { transform: translateY(-4px) scale(1.05, 0.96); }
    }
    @keyframes wobble { 0%, 100% { transform: rotate(-2deg); } 50% { transform: rotate(2deg); } }
    @keyframes blink { 0%, 46%, 50%, 100% { transform: scaleY(1); } 48% { transform: scaleY(0.1); } }
    @keyframes twinkle {
      0%, 100% { opacity: 0.25; transform: scale(0.7) rotate(0deg); }
      50% { opacity: 1; transform: scale(1.15) rotate(20deg); }
    }
    @keyframes chip-float { 0%, 100% { transform: translateY(0); } 50% { transform: translateY(-6px); } }
    @keyframes pulse-dot {
      0% { box-shadow: 0 0 0 0 rgba(45,106,79,0.45); }
      70% { box-shadow: 0 0 0 8px rgba(45,106,79,0); }
    }
    @media (max-width: 520px) {
      .chip { display: none; }
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
    connecting: 'Thinking…',
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
# Continuous browser mic — auto-sends when you stop speaking
# ---------------------------------------------------------------------------
_MIC = st.components.v2.component(
    name="continuous_browser_mic",
    html="""
    <div class="mic-wrap" id="mic-wrap">
      <div class="mic-status" id="mic-status">Mic idle</div>
    </div>
    """,
    css="""
    .mic-wrap { min-height: 0.5rem; }
    .mic-status {
      font-family: Nunito, system-ui, sans-serif;
      font-size: 0.85rem;
      color: #5B746A;
      text-align: center;
      padding: 0.25rem 0 0.5rem;
    }
    """,
    js="""
export default function (component) {
  const { data, parentElement, setTriggerValue, setStateValue } = component;
  const statusEl = parentElement.querySelector('#mic-status');
  const active = !!(data && data.active);
  const paused = !!(data && data.paused);
  const speechThreshold = (data && data.speechThreshold) || 0.02;
  const silenceMs = (data && data.silenceMs) || 850;
  const minSpeechMs = (data && data.minSpeechMs) || 450;

  if (!parentElement.__mic) {
    parentElement.__mic = {
      started: false,
      stream: null,
      ctx: null,
      processor: null,
      source: null,
      buffers: [],
      speaking: false,
      speechStartedAt: 0,
      silenceStartedAt: 0,
      emitting: false,
    };
  }
  const mic = parentElement.__mic;
  mic.active = active;
  mic.paused = paused;

  function setStatus(text) {
    if (statusEl) statusEl.textContent = text;
  }

  function floatTo16BitPCM(float32Array) {
    const out = new Int16Array(float32Array.length);
    for (let i = 0; i < float32Array.length; i++) {
      let s = Math.max(-1, Math.min(1, float32Array[i]));
      out[i] = s < 0 ? s * 0x8000 : s * 0x7fff;
    }
    return out;
  }

  function encodeWav(floatChunks, sampleRate) {
    let length = 0;
    for (const c of floatChunks) length += c.length;
    const pcm = new Int16Array(length);
    let offset = 0;
    for (const c of floatChunks) {
      pcm.set(floatTo16BitPCM(c), offset);
      offset += c.length;
    }
    const buffer = new ArrayBuffer(44 + pcm.length * 2);
    const view = new DataView(buffer);
    const writeStr = (o, s) => { for (let i = 0; i < s.length; i++) view.setUint8(o + i, s.charCodeAt(i)); };
    writeStr(0, 'RIFF');
    view.setUint32(4, 36 + pcm.length * 2, true);
    writeStr(8, 'WAVE');
    writeStr(12, 'fmt ');
    view.setUint32(16, 16, true);
    view.setUint16(20, 1, true);
    view.setUint16(22, 1, true);
    view.setUint32(24, sampleRate, true);
    view.setUint32(28, sampleRate * 2, true);
    view.setUint16(32, 2, true);
    view.setUint16(34, 16, true);
    writeStr(36, 'data');
    view.setUint32(40, pcm.length * 2, true);
    let idx = 44;
    for (let i = 0; i < pcm.length; i++, idx += 2) view.setInt16(idx, pcm[i], true);
    const bytes = new Uint8Array(buffer);
    let binary = '';
    for (let i = 0; i < bytes.length; i++) binary += String.fromCharCode(bytes[i]);
    return btoa(binary);
  }

  function stopMic() {
    try { mic.processor && mic.processor.disconnect(); } catch (e) {}
    try { mic.source && mic.source.disconnect(); } catch (e) {}
    try { mic.ctx && mic.ctx.close(); } catch (e) {}
    if (mic.stream) mic.stream.getTracks().forEach((t) => t.stop());
    mic.started = false;
    mic.stream = null;
    mic.ctx = null;
    mic.processor = null;
    mic.source = null;
    mic.buffers = [];
    mic.speaking = false;
    setStatus('Mic idle');
    setStateValue('listening', false);
  }

  async function startMic() {
    if (mic.started) return;
    try {
      const stream = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, channelCount: 1 },
        video: false,
      });
      const ctx = new (window.AudioContext || window.webkitAudioContext)({ sampleRate: 24000 });
      if (ctx.state === 'suspended') await ctx.resume();
      const source = ctx.createMediaStreamSource(stream);
      const processor = ctx.createScriptProcessor(4096, 1, 1);
      mic.stream = stream;
      mic.ctx = ctx;
      mic.source = source;
      mic.processor = processor;
      mic.started = true;
      mic.buffers = [];
      mic.speaking = false;
      mic.emitting = false;
      setStateValue('listening', true);
      setStatus('Listening — speak naturally');

      processor.onaudioprocess = (event) => {
        if (!mic.active || mic.paused || mic.emitting) return;
        const input = event.inputBuffer.getChannelData(0);
        let sum = 0;
        for (let i = 0; i < input.length; i++) sum += input[i] * input[i];
        const rms = Math.sqrt(sum / input.length);
        const now = Date.now();

        if (rms >= speechThreshold) {
          if (!mic.speaking) {
            mic.speaking = true;
            mic.speechStartedAt = now;
            mic.buffers = [];
            setStatus('Hearing you…');
            setStateValue('phase', 'speech');
          }
          mic.silenceStartedAt = 0;
          mic.buffers.push(new Float32Array(input));
          return;
        }

        if (mic.speaking) {
          mic.buffers.push(new Float32Array(input));
          if (!mic.silenceStartedAt) mic.silenceStartedAt = now;
          if (now - mic.silenceStartedAt >= silenceMs) {
            const spokeLongEnough = (now - mic.speechStartedAt) >= minSpeechMs;
            const chunks = mic.buffers.slice();
            mic.buffers = [];
            mic.speaking = false;
            mic.silenceStartedAt = 0;
            if (!spokeLongEnough || chunks.length === 0) {
              setStatus('Listening — speak naturally');
              setStateValue('phase', 'listen');
              return;
            }
            mic.emitting = true;
            setStatus('Got it — thinking…');
            setStateValue('phase', 'processing');
            const b64 = encodeWav(chunks, ctx.sampleRate || 24000);
            setTriggerValue('utterance', b64);
            // Keep paused until Python clears busy; allow next turn after.
            setTimeout(() => { mic.emitting = false; }, 300);
          }
        }
      };

      // Keep the graph alive without playing the mic back into the speakers.
      const mute = ctx.createGain();
      mute.gain.value = 0;
      source.connect(processor);
      processor.connect(mute);
      mute.connect(ctx.destination);
    } catch (err) {
      setStatus('Mic permission denied');
      setTriggerValue('error', String(err && err.message ? err.message : err));
      stopMic();
    }
  }

  if (active && !mic.started) startMic();
  if (!active && mic.started) stopMic();
  if (active && mic.started && paused) setStatus('Paused while assistant speaks');
  if (active && mic.started && !paused && !mic.speaking && !mic.emitting) {
    setStatus('Listening — speak naturally');
  }
}
""",
)


MIC_KEY = "continuous_mic"


def mount_continuous_mic(*, active: bool, paused: bool):
    return _MIC(
        key=MIC_KEY,
        data={
            "active": active,
            "paused": paused,
            "speechThreshold": 0.02,
            "silenceMs": 850,
            "minSpeechMs": 450,
            "sampleRate": SAMPLE_RATE,
        },
        default={"listening": False, "phase": "idle"},
        on_listening_change=lambda: None,
        on_phase_change=lambda: None,
        on_utterance_change=_on_utterance,
        on_error_change=_on_mic_error,
        height="auto",
    )


def _on_mic_error() -> None:
    err = st.session_state.get(MIC_KEY, {}).get("error")
    if err:
        st.session_state.agent_status = "error"
        st.session_state.last_error = str(err)


def _on_utterance() -> None:
    payload = st.session_state.get(MIC_KEY, {}).get("utterance")
    if not payload or st.session_state.get("busy"):
        return

    st.session_state.busy = True
    st.session_state.agent_status = "connecting"
    st.session_state.chat_lines.append(("you", "🎤 Voice message"))

    try:
        pcm = b64_wav_to_pcm16(payload, target_rate=SAMPLE_RATE)
        if pcm.size < SAMPLE_RATE // 5:
            st.session_state.chat_lines.append(
                ("assistant", "I barely caught that — try speaking a little longer.")
            )
            st.session_state.agent_status = "listening"
            return

        text, wav_bytes = run_voice_turn(pcm)
        st.session_state.reply_wav = wav_bytes
        # Keep mic paused while the reply plays (approx. from PCM size @ 24kHz).
        approx_sec = max(1.5, (len(wav_bytes) - 44) / 2 / SAMPLE_RATE)
        st.session_state.pause_until = time.time() + approx_sec + 0.5
        st.session_state.chat_lines.append(("assistant", text or "(spoken reply)"))
        st.session_state.agent_status = "speaking"
    except Exception as exc:  # noqa: BLE001
        st.session_state.agent_status = "error"
        st.session_state.last_error = str(exc)
        st.session_state.chat_lines.append(("assistant", f"Sorry — {exc}"))
        st.session_state.pause_until = 0
    finally:
        st.session_state.busy = False


# ---------------------------------------------------------------------------
# Session state
# ---------------------------------------------------------------------------
st.session_state.setdefault("session_active", False)
st.session_state.setdefault("busy", False)
st.session_state.setdefault("agent_status", "idle")
st.session_state.setdefault("chat_lines", deque(maxlen=40))
st.session_state.setdefault("reply_wav", None)
st.session_state.setdefault("last_error", None)
st.session_state.setdefault("pause_until", 0.0)

top_l, top_r = st.columns([4, 1])
with top_l:
    st.markdown('<h1 class="recenter-title">Travel Assistant</h1>', unsafe_allow_html=True)
    st.markdown(
        '<div class="recenter-tag">Your calm travel voice companion</div>',
        unsafe_allow_html=True,
    )
with top_r:
    if st.button(":material/key: Key", help="Change API key", use_container_width=True):
        st.session_state.session_active = False
        st.session_state.pop("openai_api_key", None)
        st.rerun()


@st.fragment(run_every="1s")
def companion_panel() -> None:
    paused = (
        st.session_state.busy
        or time.time() < float(st.session_state.pause_until or 0)
    )
    status = st.session_state.agent_status
    if st.session_state.session_active and not paused and status == "speaking":
        status = "listening"
        st.session_state.agent_status = "listening"
    elif st.session_state.session_active and paused and status == "listening":
        status = "speaking" if st.session_state.reply_wav else "connecting"
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
        "<div>Speak freely — it answers when you stop talking.</div></div>"
    )

btn_l, btn_r = st.columns([1, 1])
with btn_l:
    start = st.button(
        ":material/mic: Get started",
        type="primary",
        use_container_width=True,
        disabled=st.session_state.session_active,
        key="start_btn",
    )
with btn_r:
    stop = st.button(
        ":material/stop_circle: Pause",
        use_container_width=True,
        disabled=not st.session_state.session_active,
        key="stop_btn",
    )

if start:
    st.session_state.session_active = True
    st.session_state.agent_status = "listening"
    st.session_state.last_error = None
    st.rerun()
if stop:
    st.session_state.session_active = False
    st.session_state.agent_status = "stopped"
    st.session_state.busy = False
    st.rerun()

mic_paused = (
    st.session_state.busy
    or time.time() < float(st.session_state.pause_until or 0)
)

if (
    st.session_state.session_active
    and st.session_state.agent_status == "speaking"
    and not mic_paused
    and not st.session_state.busy
):
    st.session_state.agent_status = "listening"

# Keep mic mounted outside fragments so the AudioContext stays alive.
mount_continuous_mic(
    active=st.session_state.session_active,
    paused=mic_paused,
)

if st.session_state.last_error:
    st.error(st.session_state.last_error)

if st.session_state.reply_wav:
    st.audio(st.session_state.reply_wav, format="audio/wav", autoplay=True)

st.subheader("Conversation")
lines = list(st.session_state.chat_lines)
if not lines:
    st.caption("Press **Get started**, allow the mic, then just talk — it replies when you stop.")
else:
    for role, text in lines[-12:]:
        css = "msg-you" if role == "you" else "msg-assistant"
        label = "You" if role == "you" else "Assistant"
        st.html(
            f'<div class="msg {css}"><div class="msg-role">{label}</div>{html.escape(text)}</div>'
        )
