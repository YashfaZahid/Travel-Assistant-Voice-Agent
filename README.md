# Travel Assistant Voice Agent

A cute, animated Streamlit voice companion built on the OpenAI Agents SDK realtime API. Paste your API key, tap **Get started**, and talk.

## Features

- API key gate (session-only — never written to disk)
- Soft Recenter-inspired UI with an animated companion blob
- Noise-hardened listening (far-field noise reduction + server VAD + mic RMS gate)
- Live conversation transcripts

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
