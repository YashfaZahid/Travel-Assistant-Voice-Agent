# Travel Assistant

A live voice travel agent. You talk, it talks back, and you can interrupt it. Audio goes over OpenAI Realtime with WebRTC in the browser, not through recorded clips uploaded after the fact.

The assistant is **Dola**: a travel companion that can plan, banter, and keep a short spoken reply instead of a wall of text.

## What it does

- Session-only API key gate. The key is not written to disk by the Streamlit UI.
- Interruptible realtime conversation with voice-activity detection tuned for noisy rooms
- Browser microphone path that runs on Streamlit Community Cloud without PortAudio
- Optional local continuous microphone through `sounddevice` when PortAudio is installed
- A terminal agent (`16-realtime_agents.py`) that shares the same session core

## Run

Python 3.10+ and an OpenAI key with Realtime access.

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env        # optional; you can also paste the key in the UI
streamlit run streamlit_app.py
```

Terminal only:

```bash
python 16-realtime_agents.py
```

## Layout

| File | Role |
| --- | --- |
| `streamlit_app.py` | UI, key gate, browser session |
| `voice_browser.py` | Browser microphone path |
| `realtime_core.py` | Shared session, sample rate, VAD thresholds |
| `ephemeral.py` | Short-lived realtime session helper |
| `16-realtime_agents.py` | Terminal voice agent |

## Limits

You need a working microphone and a Realtime-capable key. The local mic path is optional and is not required on Streamlit Cloud.
