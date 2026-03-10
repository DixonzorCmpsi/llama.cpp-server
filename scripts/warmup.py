#!/usr/bin/env python3
"""
Warmup script — triggers lazy-loading of all registered models so they are
hot in VRAM before the first real request arrives.

Usage:
    python scripts/warmup.py

Reads connection settings from chat_cli/.env (API_BASE_URL, API_KEY).
Run after `docker compose restart ai-server`.
"""

import os
import sys
import time

try:
    from dotenv import load_dotenv
except ImportError:
    print("[!] Missing dependency: pip install python-dotenv openai")
    sys.exit(1)

try:
    from openai import OpenAI
except ImportError:
    print("[!] Missing dependency: pip install python-dotenv openai")
    sys.exit(1)

# Root of the repo (one level up from scripts/)
_REPO_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

load_dotenv(os.path.join(_REPO_ROOT, "chat_cli", ".env"))

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost/v1")
API_KEY      = os.getenv("API_KEY", "missing-key")


def wait_for_server(client: OpenAI, retries: int = 10, delay: int = 3) -> list[str]:
    for attempt in range(1, retries + 1):
        try:
            models = client.models.list()
            ids = [m.id for m in models.data]
            if ids:
                return ids
        except Exception:
            pass
        print(f"[~] Waiting for server... ({attempt}/{retries})")
        time.sleep(delay)
    print("[!] Server did not become ready in time.")
    sys.exit(1)


def warmup_model(client: OpenAI, model_id: str) -> None:
    print(f"[~] Loading {model_id} ...", end=" ", flush=True)
    start = time.time()
    try:
        client.chat.completions.create(
            model=model_id,
            messages=[{"role": "user", "content": "hi"}],
            max_tokens=1,
        )
        elapsed = time.time() - start
        print(f"ready ({elapsed:.1f}s)")
    except Exception as e:
        print(f"FAILED — {e}")


def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    print(f"[+] Connecting to {API_BASE_URL}")
    model_ids = wait_for_server(client)
    print(f"[+] Found {len(model_ids)} model(s): {', '.join(model_ids)}")
    print()

    for model_id in model_ids:
        warmup_model(client, model_id)

    print()
    print("[+] All models loaded and ready.")


if __name__ == "__main__":
    main()
