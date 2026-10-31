"""Travel Assistant — live WebRTC voice with Dola-style charcoal UI."""

from __future__ import annotations

import os

import streamlit as st

st.set_page_config(
    page_title="Dola · AI Assistant",
    page_icon=":material/auto_awesome:",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.html(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
  background: #0A0A0B !important;
  color: #FFFFFF !important;
  font-family: 'Inter', system-ui, sans-serif !important;
}
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stToolbar"] { display: none !important; }
#MainMenu, footer, [data-testid="stDecoration"] { visibility: hidden; display: none !important; }
.block-container {
  padding-top: 0.6rem !important;
  padding-bottom: 1rem !important;
  max-width: 430px !important;
}
div[data-testid="stTextInput"] input {
  background: #161618 !important;
  color: #F5F5F7 !important;
  border: 1px solid #2A2A2E !important;
  border-radius: 999px !important;
}
.stButton > button {
  background: #1C1C1F !important;
  color: #F5F5F7 !important;
  border: 1px solid #2A2A2E !important;
  border-radius: 999px !important;
}
</style>
"""
)


def _api_key_page() -> None:
    st.markdown(
        """
        <div style="text-align:center;padding:3rem 0 1.25rem;font-family:Inter,sans-serif;">
          <div style="width:72px;height:72px;margin:0 auto 1.4rem;border-radius:50%;
            background:radial-gradient(circle at 35% 30%, #FF9F6B, #A855F7 45%, #3B82F6);
            box-shadow:0 0 40px rgba(168,85,247,0.35);"></div>
          <div style="font-size:1.15rem;color:#9A9AA0;font-weight:500;">Hi, I'm Dola!</div>
          <div style="margin-top:0.35rem;font-size:1.55rem;font-weight:700;color:#fff;
            letter-spacing:-0.03em;line-height:1.25;">Enter your API key<br>to get started</div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    with st.form("api_key_form"):
        key = st.text_input("API key", type="password", placeholder="sk-...", label_visibility="collapsed")
        go = st.form_submit_button("Continue", type="primary", use_container_width=True)
    if go:
        cleaned = (key or "").strip()
        if not cleaned.startswith("sk-"):
            st.error("Paste a valid OpenAI API key (sk-…).")
        else:
            st.session_state["openai_api_key"] = cleaned
            os.environ["OPENAI_API_KEY"] = cleaned
            st.rerun()


if "openai_api_key" not in st.session_state:
    env_key = (os.environ.get("OPENAI_API_KEY") or "").strip()
    if env_key.startswith("sk-"):
        st.session_state["openai_api_key"] = env_key
    else:
        _api_key_page()
        st.stop()

os.environ["OPENAI_API_KEY"] = st.session_state["openai_api_key"]

from ephemeral import mint_realtime_client_secret  # noqa: E402

_VOICE = st.components.v2.component(
    name="dola_live_voice",
    html="""
    <div class="app">
      <header class="top">
        <button class="icon-btn" id="btn-menu" type="button" aria-label="Menu" title="Change API key">
          <svg width="18" height="18" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2">
            <path d="M4 7h16M4 12h16M4 17h16"/>
          </svg>
        </button>
        <div class="brand-pill">
          <span class="star" aria-hidden="true"></span>
          <span class="brand-text">
            <span class="name">Dola</span>
            <span class="sub">AI Assistant</span>
          </span>
        </div>
        <button class="icon-btn" id="btn-mute" type="button" aria-label="Mute">
          <svg id="icon-speaker" width="18" height="18" viewBox="0 0 24 24" fill="none"
               stroke="currentColor" stroke-width="2" stroke-linecap="round" stroke-linejoin="round">
            <polygon points="11 5 6 9 2 9 2 15 6 15 11 19 11 5"/>
            <path d="M15.5 8.5a5 5 0 0 1 0 7"/>
            <path d="M18.5 5.5a9 9 0 0 1 0 13"/>
          </svg>
        </button>
      </header>

      <main class="stage">
        <button class="orb-hit" id="orb" type="button" aria-label="Toggle voice">
          <canvas id="orb-canvas" width="560" height="560"></canvas>
        </button>
        <div class="copy" id="copy">
          <div class="hello" id="hello">Hi, I'm Dola!</div>
          <div class="prompt" id="prompt">How can I help<br>you today?</div>
        </div>
        <div class="status" id="status"></div>
        <div class="chat" id="chat"></div>
      </main>
    </div>
    """,
    css="""
    @import url('https://fonts.googleapis.com/css2?family=Inter:wght@400;500;600;700&display=swap');

    :host, .app {
      font-family: 'Inter', system-ui, -apple-system, sans-serif;
      color: #fff;
      width: 100%;
      display: block;
      background: #0A0A0B;
    }
    .app {
      min-height: 78vh;
      padding: 0.35rem 0.35rem 1.25rem;
      box-sizing: border-box;
    }
    .top {
      display: flex;
      align-items: center;
      justify-content: space-between;
      gap: 0.6rem;
      margin-bottom: 0.75rem;
    }
    .icon-btn {
      width: 42px;
      height: 42px;
      border-radius: 50%;
      border: 1px solid rgba(255,255,255,0.06);
      background: #161618;
      color: #F3F3F5;
      display: grid;
      place-items: center;
      cursor: pointer;
      flex: 0 0 auto;
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
    }
    .icon-btn:hover { background: #1C1C1F; }
    .icon-btn.muted { color: #888; }
    .brand-pill {
      flex: 1 1 auto;
      min-width: 0;
      display: flex;
      align-items: center;
      gap: 0.65rem;
      height: 46px;
      padding: 0 1rem 0 0.7rem;
      border-radius: 999px;
      background: #161618;
      border: 1px solid rgba(255,255,255,0.06);
      box-shadow: inset 0 1px 0 rgba(255,255,255,0.04);
    }
    .star {
      width: 22px;
      height: 22px;
      flex: 0 0 auto;
      background: linear-gradient(135deg, #FF7A59 0%, #C084FC 45%, #60A5FA 100%);
      clip-path: polygon(50% 0%, 61% 35%, 98% 35%, 68% 57%, 79% 91%, 50% 70%, 21% 91%, 32% 57%, 2% 35%, 39% 35%);
      filter: drop-shadow(0 0 8px rgba(192,132,252,0.55));
    }
    .brand-text { display: flex; flex-direction: column; line-height: 1.1; min-width: 0; }
    .name { font-size: 0.95rem; font-weight: 600; color: #fff; }
    .sub { font-size: 0.72rem; color: #8B8B93; font-weight: 500; margin-top: 1px; }

    .stage {
      display: flex;
      flex-direction: column;
      align-items: center;
      padding-top: 1.25rem;
    }
    .orb-hit {
      border: 0;
      background: transparent;
      padding: 0;
      cursor: pointer;
      width: min(280px, 72vw);
      height: min(280px, 72vw);
      border-radius: 50%;
    }
    #orb-canvas {
      width: 100%;
      height: 100%;
      display: block;
      filter: drop-shadow(0 0 28px rgba(124, 58, 237, 0.28));
    }
    .copy {
      text-align: center;
      margin-top: 1.6rem;
      transition: opacity 0.25s ease;
    }
    .copy.hidden { opacity: 0; height: 0; margin: 0; overflow: hidden; }
    .hello {
      color: #9A9AA0;
      font-size: 1.05rem;
      font-weight: 500;
      margin-bottom: 0.45rem;
    }
    .prompt {
      color: #FFFFFF;
      font-size: clamp(1.65rem, 6.2vw, 2.05rem);
      font-weight: 700;
      letter-spacing: -0.035em;
      line-height: 1.18;
    }
    .status {
      margin-top: 0.75rem;
      min-height: 1.1rem;
      color: #8B8B93;
      font-size: 0.82rem;
      font-weight: 500;
      text-align: center;
    }
    .chat {
      width: 100%;
      margin-top: 1rem;
      display: flex;
      flex-direction: column;
      gap: 0.55rem;
      max-height: 34vh;
      overflow-y: auto;
      padding: 0 0.15rem;
    }
    .bubble {
      max-width: 92%;
      padding: 0.75rem 0.9rem;
      border-radius: 16px;
      font-size: 0.9rem;
      line-height: 1.45;
      background: #161618;
      border: 1px solid rgba(255,255,255,0.06);
      color: #F0F0F2;
    }
    .bubble.user {
      align-self: flex-end;
      background: linear-gradient(135deg, rgba(124,58,237,0.35), rgba(37,99,235,0.28));
    }
    .bubble.assistant { align-self: flex-start; }
    .role {
      font-size: 0.65rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: #8B8B93;
      margin-bottom: 0.2rem;
      font-weight: 600;
    }
    """,
    js="""
export default function (component) {
  const { data, parentElement, setStateValue, setTriggerValue } = component;
  const orbBtn = parentElement.querySelector('#orb');
  const canvas = parentElement.querySelector('#orb-canvas');
  const statusEl = parentElement.querySelector('#status');
  const chat = parentElement.querySelector('#chat');
  const copy = parentElement.querySelector('#copy');
  const btnMenu = parentElement.querySelector('#btn-menu');
  const btnMute = parentElement.querySelector('#btn-mute');
  if (!orbBtn || !canvas || !statusEl || !chat) return;

  if (!parentElement.__dola) {
    parentElement.__dola = {
      pc: null, dc: null, stream: null, audioEl: null,
      connected: false, connecting: false, muted: false,
      lines: [], assistantBuf: '', userBuf: '',
      anim: 0, energy: 0.15, targetEnergy: 0.15, raf: 0,
      particles: null,
    };
    initParticles(parentElement.__dola, canvas);
    loop(parentElement.__dola, canvas);
  }
  const v = parentElement.__dola;
  const ephemeralKey = data && data.ephemeralKey;
  const wantConnect = !!(data && data.connect);

  function setStatus(text) {
    statusEl.textContent = text || '';
  }

  function escapeHtml(s) {
    return String(s)
      .replaceAll('&', '&amp;').replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;').replaceAll('"', '&quot;');
  }

  function renderChat() {
    const hasChat = v.lines.length > 0;
    if (copy) copy.classList.toggle('hidden', hasChat);
    chat.innerHTML = '';
    for (const line of v.lines.slice(-40)) {
      const div = document.createElement('div');
      div.className = 'bubble ' + line.role;
      div.innerHTML = '<div class="role">' + (line.role === 'user' ? 'You' : 'Dola') +
        '</div>' + escapeHtml(line.text);
      chat.appendChild(div);
    }
    chat.scrollTop = chat.scrollHeight;
    setStateValue('lines', v.lines.slice(-40));
  }

  function pushLine(role, text) {
    if (!text || !String(text).trim()) return;
    const t = String(text).trim();
    if (v.lines.length && v.lines[v.lines.length - 1].role === role) {
      v.lines[v.lines.length - 1].text = t;
    } else {
      v.lines.push({ role, text: t });
    }
    renderChat();
  }

  function handleEvent(raw) {
    let msg;
    try { msg = JSON.parse(raw); } catch (e) { return; }
    const type = msg.type || '';

    if (type === 'input_audio_buffer.speech_started') {
      v.targetEnergy = 0.28;
      setStatus('Listening…');
      v.userBuf = '';
    } else if (type === 'input_audio_buffer.speech_stopped') {
      v.targetEnergy = 0.18;
      setStatus('Thinking…');
    } else if (type === 'response.output_audio.delta' || type === 'response.audio.delta') {
      v.targetEnergy = 0.32;
      setStatus('Speaking…');
    } else if (
      type === 'conversation.item.input_audio_transcription.completed' ||
      type === 'conversation.item.input_audio_transcription.delta'
    ) {
      const piece = msg.transcript || msg.delta || '';
      if (type.endsWith('delta')) {
        v.userBuf = (v.userBuf || '') + piece;
        pushLine('user', v.userBuf);
      } else if (piece) {
        v.userBuf = piece;
        pushLine('user', piece);
      }
    } else if (
      type === 'response.output_audio_transcript.delta' ||
      type === 'response.audio_transcript.delta'
    ) {
      v.assistantBuf = (v.assistantBuf || '') + (msg.delta || '');
      pushLine('assistant', v.assistantBuf);
      v.targetEnergy = 0.3;
      setStatus('Speaking…');
    } else if (
      type === 'response.output_audio_transcript.done' ||
      type === 'response.audio_transcript.done' ||
      type === 'response.done'
    ) {
      if (msg.transcript) pushLine('assistant', msg.transcript);
      v.assistantBuf = '';
      v.targetEnergy = 0.14;
      setStatus(v.connected ? 'Listening…' : '');
    } else if (type === 'error') {
      const err = (msg.error && (msg.error.message || msg.error)) || 'Connection error';
      setStatus(String(err));
      setStateValue('error', String(err));
      v.targetEnergy = 0.1;
    }
  }

  async function waitIce(pc) {
    if (pc.iceGatheringState === 'complete') return;
    await new Promise((resolve) => {
      const check = () => {
        if (pc.iceGatheringState === 'complete') {
          pc.removeEventListener('icegatheringstatechange', check);
          resolve();
        }
      };
      pc.addEventListener('icegatheringstatechange', check);
      setTimeout(resolve, 2000);
    });
  }

  async function connect() {
    if (v.connecting || v.connected) return;
    if (!ephemeralKey) {
      setStatus('Missing session token');
      return;
    }
    v.connecting = true;
    v.targetEnergy = 0.35;
    setStatus('Connecting…');
    try {
      const pc = new RTCPeerConnection();
      v.pc = pc;

      const audioEl = document.createElement('audio');
      audioEl.autoplay = true;
      audioEl.playsInline = true;
      parentElement.appendChild(audioEl);
      v.audioEl = audioEl;
      pc.ontrack = (e) => {
        audioEl.srcObject = e.streams[0];
        audioEl.muted = v.muted;
        audioEl.play().catch(() => {});
      };

      const ms = await navigator.mediaDevices.getUserMedia({
        audio: { echoCancellation: true, noiseSuppression: true, autoGainControl: true },
      });
      v.stream = ms;
      ms.getTracks().forEach((t) => pc.addTrack(t, ms));

      const dc = pc.createDataChannel('oai-events');
      v.dc = dc;
      dc.addEventListener('message', (e) => handleEvent(e.data));
      dc.addEventListener('open', () => {
        dc.send(JSON.stringify({
          type: 'session.update',
          session: {
            type: 'realtime',
            instructions:
              'You are Dola, a lively travel AI assistant. Speak naturally like ChatGPT voice. ' +
              'Be an expert on travel, and joke or sing briefly when asked.',
          },
        }));
      });

      const offer = await pc.createOffer();
      await pc.setLocalDescription(offer);
      await waitIce(pc);

      const sdpResponse = await fetch('https://api.openai.com/v1/realtime/calls', {
        method: 'POST',
        body: pc.localDescription.sdp,
        headers: {
          Authorization: 'Bearer ' + ephemeralKey,
          'Content-Type': 'application/sdp',
        },
      });
      if (!sdpResponse.ok) {
        const t = await sdpResponse.text();
        throw new Error('Realtime call failed: ' + sdpResponse.status + ' ' + t);
      }
      await pc.setRemoteDescription({ type: 'answer', sdp: await sdpResponse.text() });

      v.connected = true;
      v.connecting = false;
      v.targetEnergy = 0.22;
      setStatus('Listening…');
      setStateValue('connected', true);
    } catch (err) {
      v.connecting = false;
      setStatus((err && err.message) ? err.message : String(err));
      setStateValue('error', String(err && err.message ? err.message : err));
      await disconnect(false);
    }
  }

  async function disconnect(updateHint) {
    try { v.dc && v.dc.close(); } catch (e) {}
    try { v.pc && v.pc.close(); } catch (e) {}
    if (v.stream) v.stream.getTracks().forEach((t) => t.stop());
    if (v.audioEl) {
      v.audioEl.srcObject = null;
      try { v.audioEl.remove(); } catch (e) {}
    }
    v.pc = null; v.dc = null; v.stream = null; v.audioEl = null;
    v.connected = false; v.connecting = false;
    v.targetEnergy = 0.15;
    setStateValue('connected', false);
    if (updateHint !== false) setStatus('Tap the orb to talk');
  }

  orbBtn.onclick = async () => {
    if (v.connected || v.connecting) await disconnect();
    else await connect();
  };

  if (btnMenu) {
    btnMenu.onclick = () => setTriggerValue('change_key', true);
  }
  if (btnMute) {
    btnMute.onclick = () => {
      v.muted = !v.muted;
      if (v.audioEl) v.audioEl.muted = v.muted;
      btnMute.classList.toggle('muted', v.muted);
    };
  }

  if (wantConnect && ephemeralKey && !v.connected && !v.connecting && v._key !== ephemeralKey) {
    v._key = ephemeralKey;
    connect();
  }
  if (!wantConnect && v.connected) disconnect();
}

function initParticles(v, canvas) {
  const pts = [];
  const N = 1700;
  for (let i = 0; i < N; i++) {
    const u = Math.random();
    const vang = Math.random();
    const theta = 2 * Math.PI * u;
    const phi = Math.acos(2 * vang - 1);
    pts.push({
      theta, phi,
      r: 0.82 + Math.random() * 0.12,
      phase: Math.random() * Math.PI * 2,
      speed: 0.08 + Math.random() * 0.12,
      size: 0.7 + Math.random() * 1.5,
    });
  }
  v.particles = pts;
}

function colorFor(y, elev) {
  // y in [-1,1], elev boosts warm highlights
  const t = (y + 1) / 2;
  const warm = Math.max(0, elev);
  // purple -> blue base, orange on ridges
  const r = Math.floor(70 + 90 * (1 - t) + 160 * warm);
  const g = Math.floor(40 + 60 * t + 90 * warm);
  const b = Math.floor(170 + 40 * t - 80 * warm);
  return 'rgba(' + r + ',' + g + ',' + b + ',';
}

function loop(v, canvas) {
  const ctx = canvas.getContext('2d');
  const dpr = Math.min(window.devicePixelRatio || 1, 2);
  const css = canvas.clientWidth || 280;
  canvas.width = Math.floor(css * dpr);
  canvas.height = Math.floor(css * dpr);

  const draw = (now) => {
    v.raf = requestAnimationFrame(draw);
    v.anim = now * 0.001;
    v.energy += (v.targetEnergy - v.energy) * 0.04;

    const w = canvas.width;
    const h = canvas.height;
    ctx.clearRect(0, 0, w, h);
    const cx = w / 2;
    const cy = h / 2;
    const scale = Math.min(w, h) * 0.42;

    // soft glow behind sphere
    const glow = ctx.createRadialGradient(cx, cy, scale * 0.2, cx, cy, scale * 1.35);
    glow.addColorStop(0, 'rgba(124,58,237,' + (0.14 + v.energy * 0.08) + ')');
    glow.addColorStop(0.55, 'rgba(37,99,235,0.06)');
    glow.addColorStop(1, 'rgba(0,0,0,0)');
    ctx.fillStyle = glow;
    ctx.beginPath();
    ctx.arc(cx, cy, scale * 1.35, 0, Math.PI * 2);
    ctx.fill();

    const pts = v.particles || [];
    const t = v.anim;
    const e = v.energy;

    // Stable sphere: tiny surface shimmer + very slow spin
    for (let i = 0; i < pts.length; i++) {
      const p = pts[i];
      const wave =
        Math.sin(p.theta * 2 + t * p.speed + p.phase) * 0.012 +
        Math.sin(p.phi * 3 - t * 0.25 + p.phase) * 0.01 +
        Math.sin((p.theta + p.phi) + t * 0.2) * (0.006 + e * 0.012);
      const radius = p.r + wave;
      const x3 = radius * Math.sin(p.phi) * Math.cos(p.theta);
      const y3 = radius * Math.cos(p.phi);
      const z3 = radius * Math.sin(p.phi) * Math.sin(p.theta);

      const rot = t * 0.04;
      const xr = x3 * Math.cos(rot) - z3 * Math.sin(rot);
      const zr = x3 * Math.sin(rot) + z3 * Math.cos(rot);

      const depth = (zr + 1.2) / 2.2;
      const px = cx + xr * scale;
      const py = cy + y3 * scale;
      const elev = Math.max(0, wave * 8);
      const alpha = 0.28 + depth * 0.65;
      const size = p.size * dpr * (0.75 + depth * 0.85) * (1 + e * 0.12);

      ctx.beginPath();
      ctx.fillStyle = colorFor(y3, elev) + alpha + ')';
      ctx.arc(px, py, size, 0, Math.PI * 2);
      ctx.fill();
    }
  };
  cancelAnimationFrame(v.raf);
  v.raf = requestAnimationFrame(draw);
}
""",
)


st.session_state.setdefault("voice_connect", True)
st.session_state.setdefault("ephemeral_key", None)
st.session_state.setdefault("mint_error", None)

if st.session_state.voice_connect and not st.session_state.ephemeral_key:
    try:
        st.session_state.ephemeral_key = mint_realtime_client_secret(
            st.session_state["openai_api_key"]
        )
        st.session_state.mint_error = None
    except Exception as exc:  # noqa: BLE001
        st.session_state.mint_error = str(exc)
        st.session_state.voice_connect = False

if st.session_state.mint_error:
    st.error(st.session_state.mint_error)
    if st.button("Retry", type="primary", use_container_width=True):
        st.session_state.mint_error = None
        st.session_state.ephemeral_key = None
        st.session_state.voice_connect = True
        st.rerun()


def _on_change_key() -> None:
    st.session_state["_force_key_reset"] = True


_VOICE(
    key="live_voice",
    data={
        "ephemeralKey": st.session_state.ephemeral_key,
        "connect": bool(st.session_state.voice_connect and st.session_state.ephemeral_key),
    },
    default={"phase": "idle", "connected": False, "lines": [], "error": None},
    on_phase_change=lambda: None,
    on_connected_change=lambda: None,
    on_lines_change=lambda: None,
    on_error_change=lambda: None,
    on_change_key_change=_on_change_key,
    height="auto",
)

if st.session_state.pop("_force_key_reset", None):
    st.session_state.voice_connect = False
    st.session_state.ephemeral_key = None
    st.session_state.pop("openai_api_key", None)
    st.rerun()
