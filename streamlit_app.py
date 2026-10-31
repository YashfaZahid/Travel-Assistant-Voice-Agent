"""Travel Assistant — ChatGPT-style live voice (WebRTC) + minimal purple/charcoal UI."""

from __future__ import annotations

import os

import streamlit as st

st.set_page_config(
    page_title="Travel Assistant",
    page_icon=":material/travel_explore:",
    layout="centered",
    initial_sidebar_state="collapsed",
)

st.html(
    """
<style>
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');

html, body, [data-testid="stAppViewContainer"], .stApp {
  background: radial-gradient(1200px 700px at 20% -10%, #5B4BDB 0%, transparent 55%),
              radial-gradient(900px 600px at 100% 10%, #1F6FEB 0%, transparent 50%),
              linear-gradient(165deg, #0B0F1A 0%, #141A2A 45%, #0E1320 100%) !important;
  color: #E8ECF5 !important;
  font-family: 'DM Sans', system-ui, sans-serif !important;
}
[data-testid="stHeader"] { background: transparent !important; }
[data-testid="stToolbar"] { display: none !important; }
#MainMenu, footer { visibility: hidden; }
.block-container {
  padding-top: 1.25rem !important;
  padding-bottom: 2rem !important;
  max-width: 560px !important;
}
div[data-testid="stTextInput"] input {
  background: rgba(20, 24, 38, 0.9) !important;
  color: #E8ECF5 !important;
  border: 1px solid rgba(120, 140, 200, 0.35) !important;
  border-radius: 14px !important;
}
</style>
"""
)


def _api_key_page() -> None:
    st.markdown(
        """
        <div style="text-align:center;padding:2rem 0 1rem;font-family:'DM Sans',sans-serif;">
          <div style="width:88px;height:88px;margin:0 auto 1.25rem;border-radius:50%;
            background:radial-gradient(circle at 30% 30%, #A78BFA, #4F46E5 45%, #1D4ED8);
            box-shadow:0 0 48px rgba(99,102,241,0.45);"></div>
          <div style="font-size:1.6rem;font-weight:700;color:#F1F5FF;letter-spacing:-0.02em;">
            Travel Assistant
          </div>
          <div style="margin-top:0.4rem;color:#9AA6C2;font-size:0.95rem;">
            Enter your OpenAI API key to start
          </div>
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

# ---------------------------------------------------------------------------
# Live WebRTC voice experience (orb + conversation)
# ---------------------------------------------------------------------------
_VOICE = st.components.v2.component(
    name="travel_live_voice",
    html="""
    <div class="shell">
      <button class="orb" id="orb" type="button" aria-label="Start or stop voice">
        <span class="orb-core"></span>
        <span class="ring r1"></span>
        <span class="ring r2"></span>
      </button>
      <div class="hint" id="hint">Tap to talk</div>
      <div class="chat" id="chat"></div>
    </div>
    """,
    css="""
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@400;500;600;700&display=swap');
    :host, .shell {
      font-family: 'DM Sans', system-ui, sans-serif;
      color: #E8ECF5;
      width: 100%;
      display: block;
    }
    .shell {
      display: flex;
      flex-direction: column;
      align-items: center;
      gap: 0.85rem;
      padding: 0.5rem 0 1rem;
    }
    .orb {
      position: relative;
      width: 168px;
      height: 168px;
      border: 0;
      border-radius: 50%;
      background: transparent;
      cursor: pointer;
      outline: none;
    }
    .orb-core {
      position: absolute;
      inset: 18px;
      border-radius: 50%;
      background:
        radial-gradient(circle at 32% 28%, #C4B5FD 0%, #7C3AED 38%, #2563EB 72%, #0F172A 100%);
      box-shadow:
        0 0 40px rgba(124, 58, 237, 0.55),
        0 18px 40px rgba(15, 23, 42, 0.55),
        inset 0 1px 0 rgba(255,255,255,0.25);
      transition: transform 0.25s ease, box-shadow 0.25s ease;
    }
    .ring {
      position: absolute;
      inset: 0;
      border-radius: 50%;
      border: 1px solid rgba(167, 139, 250, 0.28);
      opacity: 0;
    }
    .orb[data-state="listening"] .orb-core,
    .orb[data-state="speaking"] .orb-core {
      animation: pulse 1.8s ease-in-out infinite;
    }
    .orb[data-state="speaking"] .r1,
    .orb[data-state="listening"] .r1 {
      animation: ripple 2s ease-out infinite;
      opacity: 1;
    }
    .orb[data-state="speaking"] .r2,
    .orb[data-state="listening"] .r2 {
      animation: ripple 2s ease-out 0.7s infinite;
      opacity: 1;
    }
    .orb[data-state="connecting"] .orb-core {
      animation: spin-glow 1.2s linear infinite;
    }
    .hint {
      font-size: 0.9rem;
      color: #9AA6C2;
      min-height: 1.2rem;
      text-align: center;
    }
    .chat {
      width: 100%;
      margin-top: 0.5rem;
      display: flex;
      flex-direction: column;
      gap: 0.55rem;
      max-height: 42vh;
      overflow-y: auto;
      padding: 0.25rem 0.15rem 0.5rem;
    }
    .bubble {
      max-width: 92%;
      padding: 0.7rem 0.9rem;
      border-radius: 16px;
      font-size: 0.92rem;
      line-height: 1.45;
      background: rgba(30, 36, 56, 0.92);
      border: 1px solid rgba(120, 140, 200, 0.18);
      color: #E8ECF5;
      box-shadow: 0 8px 24px rgba(0,0,0,0.22);
    }
    .bubble.user {
      align-self: flex-end;
      background: linear-gradient(135deg, rgba(79,70,229,0.45), rgba(37,99,235,0.35));
      border-color: rgba(129,140,248,0.35);
    }
    .bubble.assistant {
      align-self: flex-start;
      background: rgba(22, 27, 42, 0.95);
    }
    .role {
      font-size: 0.68rem;
      letter-spacing: 0.06em;
      text-transform: uppercase;
      color: #8B97B5;
      margin-bottom: 0.2rem;
      font-weight: 600;
    }
    @keyframes pulse {
      0%, 100% { transform: scale(1); box-shadow: 0 0 40px rgba(124,58,237,0.55); }
      50% { transform: scale(1.04); box-shadow: 0 0 58px rgba(37,99,235,0.7); }
    }
    @keyframes ripple {
      0% { transform: scale(0.85); opacity: 0.55; }
      100% { transform: scale(1.18); opacity: 0; }
    }
    @keyframes spin-glow {
      0% { filter: hue-rotate(0deg); }
      100% { filter: hue-rotate(40deg); }
    }
    """,
    js="""
export default function (component) {
  const { data, parentElement, setStateValue } = component;
  const orb = parentElement.querySelector('#orb');
  const hint = parentElement.querySelector('#hint');
  const chat = parentElement.querySelector('#chat');
  if (!orb || !hint || !chat) return;

  if (!parentElement.__voice) {
    parentElement.__voice = {
      pc: null,
      dc: null,
      stream: null,
      audioEl: null,
      connected: false,
      connecting: false,
      lines: [],
      assistantBuf: '',
      userBuf: '',
    };
  }
  const v = parentElement.__voice;
  const ephemeralKey = data && data.ephemeralKey;
  const wantConnect = !!(data && data.connect);

  function setUi(state, text) {
    orb.setAttribute('data-state', state);
    hint.textContent = text;
    setStateValue('phase', state);
  }

  function renderChat() {
    chat.innerHTML = '';
    for (const line of v.lines.slice(-40)) {
      const div = document.createElement('div');
      div.className = 'bubble ' + line.role;
      div.innerHTML = '<div class="role">' + (line.role === 'user' ? 'You' : 'Assistant') +
        '</div>' + escapeHtml(line.text);
      chat.appendChild(div);
    }
    chat.scrollTop = chat.scrollHeight;
    setStateValue('lines', v.lines.slice(-40));
  }

  function escapeHtml(s) {
    return String(s)
      .replaceAll('&', '&amp;')
      .replaceAll('<', '&lt;')
      .replaceAll('>', '&gt;')
      .replaceAll('"', '&quot;');
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
      setUi('listening', 'Listening…');
      v.userBuf = '';
    } else if (type === 'input_audio_buffer.speech_stopped') {
      setUi('connecting', 'Thinking…');
    } else if (type === 'response.output_audio.delta' || type === 'response.audio.delta') {
      setUi('speaking', 'Speaking…');
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
      setUi('speaking', 'Speaking…');
    } else if (
      type === 'response.output_audio_transcript.done' ||
      type === 'response.audio_transcript.done' ||
      type === 'response.done'
    ) {
      if (msg.transcript) pushLine('assistant', msg.transcript);
      v.assistantBuf = '';
      setUi('listening', 'Listening…');
    } else if (type === 'error') {
      const err = (msg.error && (msg.error.message || msg.error)) || 'Connection error';
      setUi('error', String(err));
      setStateValue('error', String(err));
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
      setUi('error', 'Missing session token');
      return;
    }
    v.connecting = true;
    setUi('connecting', 'Connecting…');
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
        // Optional session nudge for conversational style.
        dc.send(JSON.stringify({
          type: 'session.update',
          session: {
            type: 'realtime',
            instructions:
              'Be a lively travel expert. Chat naturally like ChatGPT voice. Joke and sing briefly when asked.',
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
      const answer = { type: 'answer', sdp: await sdpResponse.text() };
      await pc.setRemoteDescription(answer);

      v.connected = true;
      v.connecting = false;
      setUi('listening', 'Listening…');
      setStateValue('connected', true);
    } catch (err) {
      v.connecting = false;
      setUi('error', (err && err.message) ? err.message : String(err));
      setStateValue('error', String(err && err.message ? err.message : err));
      await disconnect();
    }
  }

  async function disconnect() {
    try { v.dc && v.dc.close(); } catch (e) {}
    try { v.pc && v.pc.close(); } catch (e) {}
    if (v.stream) v.stream.getTracks().forEach((t) => t.stop());
    if (v.audioEl) {
      v.audioEl.srcObject = null;
      try { v.audioEl.remove(); } catch (e) {}
    }
    v.pc = null;
    v.dc = null;
    v.stream = null;
    v.audioEl = null;
    v.connected = false;
    v.connecting = false;
    setStateValue('connected', false);
    setUi('idle', 'Tap to talk');
  }

  orb.onclick = async () => {
    if (v.connected || v.connecting) await disconnect();
    else await connect();
  };

  // Auto-connect once when Streamlit provides a fresh token + connect flag.
  if (wantConnect && ephemeralKey && !v.connected && !v.connecting && v._key !== ephemeralKey) {
    v._key = ephemeralKey;
    connect();
  }
  if (!wantConnect && v.connected) {
    disconnect();
  }
}
""",
)


st.session_state.setdefault("voice_connect", True)
st.session_state.setdefault("ephemeral_key", None)
st.session_state.setdefault("mint_error", None)

top = st.columns([6, 1])
with top[1]:
    if st.button(":material/vpn_key:", help="Change API key", use_container_width=True):
        st.session_state.voice_connect = False
        st.session_state.ephemeral_key = None
        st.session_state.pop("openai_api_key", None)
        st.rerun()

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
    height="auto",
)
