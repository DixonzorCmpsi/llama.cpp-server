#!/usr/bin/env python3
"""
Interactive CLI chat client for the on-prem llama.cpp API.
Configure connection in .env — no code changes needed.
"""

import os
import sys

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

load_dotenv(os.path.join(os.path.dirname(__file__), ".env"))

API_BASE_URL = os.getenv("API_BASE_URL", "http://localhost/v1")
API_KEY      = os.getenv("API_KEY", "missing-key")
MODEL        = os.getenv("MODEL", "")
SYSTEM_PROMPT = "You are a helpful assistant."


def main():
    client = OpenAI(base_url=API_BASE_URL, api_key=API_KEY)

    # Verify connection and resolve model
    try:
        models = client.models.list()
        available = [m.id for m in models.data]
    except Exception as e:
        print(f"[!] Cannot reach API at {API_BASE_URL}: {e}")
        sys.exit(1)

    if not available:
        print(f"[!] Connected to {API_BASE_URL} but no models are registered.")
        print("    Run: docker compose restart ai-server")
        sys.exit(1)

    model = MODEL if MODEL in available else available[0]

    print(f"[+] Connected to {API_BASE_URL}")
    print(f"[+] Model: {model}")
    if available:
        print(f"[+] All available models: {', '.join(available)}")
    print("-" * 50)
    print("Type your message and press Enter. Type 'exit' or Ctrl+C to quit.")
    print("Type 'reset' to clear conversation history.")
    print("-" * 50)

    history = [{"role": "system", "content": SYSTEM_PROMPT}]

    while True:
        try:
            user_input = input("\nYou: ").strip()
        except (KeyboardInterrupt, EOFError):
            print("\n[*] Goodbye.")
            break

        if not user_input:
            continue
        if user_input.lower() == "exit":
            print("[*] Goodbye.")
            break
        if user_input.lower() == "reset":
            history = [{"role": "system", "content": SYSTEM_PROMPT}]
            print("[*] Conversation history cleared.")
            continue

        history.append({"role": "user", "content": user_input})

        try:
            response = client.chat.completions.create(
                model=model,
                messages=history,
                stream=True,
            )

            print("\nAssistant: ", end="", flush=True)
            full_reply = ""
            for chunk in response:
                delta = chunk.choices[0].delta.content or ""
                print(delta, end="", flush=True)
                full_reply += delta
            print()

            history.append({"role": "assistant", "content": full_reply})

        except Exception as e:
            print(f"\n[!] Request failed: {e}")
            history.pop()  # remove the user message that failed


if __name__ == "__main__":
    main()
