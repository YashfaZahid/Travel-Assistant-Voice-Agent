"""Realtime voice agent CLI — noise-hardened VAD + local mic/speaker I/O."""

import asyncio

from dotenv import find_dotenv, load_dotenv

load_dotenv(find_dotenv(), override=True)

from realtime_core import SessionCallbacks, build_agent, run_realtime_session


async def main() -> None:
    agent = build_agent()
    print("Travel Advisor is listening... just speak. Press Ctrl+C to quit.\n")
    print(
        "(Noise gate + far-field NR + server VAD threshold "
        "are on — ambient noise should trigger less often.)\n"
    )

    def on_transcript(text: str) -> None:
        print(text, end="", flush=True)

    def on_user_transcript(text: str) -> None:
        print(f"\nYou: {text}")

    def on_agent_end() -> None:
        print()

    def on_error(err: object) -> None:
        print(f"Error: {err}")

    await run_realtime_session(
        agent,
        SessionCallbacks(
            on_transcript=on_transcript,
            on_user_transcript=on_user_transcript,
            on_agent_end=on_agent_end,
            on_error=on_error,
        ),
    )


if __name__ == "__main__":
    asyncio.run(main())
