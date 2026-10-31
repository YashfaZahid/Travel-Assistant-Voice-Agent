# Travel Assistant Voice Agent

ChatGPT-style live voice travel companion on Streamlit. Paste your API key, allow the mic, and talk — replies stream in real time over WebRTC (not recorded clips).

## Features

- API key gate (session-only — never written to disk)
- OpenAI Realtime **WebRTC** conversation (interruptible, low-latency)
- Minimal purple / blue / charcoal UI — gradient orb + chat
- Works on Streamlit Cloud (browser mic, no PortAudio)

## Setup

```bash
python -m pip install -r requirements.txt
```

Optional: copy `.env.example` to `.env` and set `OPENAI_API_KEY`. You can also enter the key in the app UI.

## Run

```bash
streamlit run streamlit_app.py
```

CLI (no UI):

```bash
python 16-realtime_agents.py
```

## Requirements

- Python 3.10+
- Working microphone and speakers
- OpenAI API key with Realtime / `gpt-realtime` access

## Repo layout

| File | Purpose |
|------|---------|
| `streamlit_app.py` | Main Streamlit UI + API key page |
| `realtime_core.py` | Shared realtime session, audio I/O, VAD settings |
| `16-realtime_agents.py` | Terminal voice agent |
| `.streamlit/config.toml` | Soft mint theme |
