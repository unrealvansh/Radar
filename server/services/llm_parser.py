import os
import re
import json
import subprocess
from datetime import datetime, timedelta

# Paths
MODEL_PATH = os.path.expanduser("~/pocketbrain/models/smollm2-360m-instruct.Q4_K_M.gguf")
LLAMA_CLI_PATH = os.path.expanduser("~/pocketbrain/llama.cpp/build/bin/llama-cli")
LLAMA_LEGACY_PATH = os.path.expanduser("~/pocketbrain/llama.cpp/llama-cli")
LLAMA_MAIN_PATH = os.path.expanduser("~/pocketbrain/llama.cpp/main")

def get_llama_binary():
    """Find available llama.cpp binary."""
    for p in [LLAMA_CLI_PATH, LLAMA_LEGACY_PATH, LLAMA_MAIN_PATH]:
        if os.path.exists(p) and os.access(p, os.X_OK):
            return p
    return None

def is_llm_available():
    """Check if model and llama.cpp binary exist."""
    binary = get_llama_binary()
    return binary is not None and os.path.exists(MODEL_PATH)


def _build_prompt(message: str) -> str:
    """Build a SHORT completion-style prompt with 3 examples."""
    today_str = datetime.now().strftime('%Y-%m-%d')
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    # Keep it VERY short — completion mode, not chat mode
    return (
        f'Convert the message to JSON. Today is {today_str}.\n'
        f'User: "chai 20" -> {{"action":"expense","amount":20,"description":"chai","category":"food"}}\n'
        f'User: "gym done" -> {{"action":"habit","name":"gym"}}\n'
        f'User: "bunked CN" -> {{"action":"attendance","subject":"CN","status":"bunked"}}\n'
        f'User: "remind me call mom at 7pm" -> {{"action":"reminder","title":"call mom","date":"{today_str}","time":"19:00"}}\n'
        f'User: "OS assignment due tomorrow" -> {{"action":"deadline","title":"assignment","subject":"OS","due_date":"{tomorrow_str}"}}\n'
        f'User: "{message}" -> '
    )


def extract_json(raw_text):
    """Extract valid JSON with 'action' key from raw LLM output."""
    if not raw_text:
        return None
    candidates = re.findall(r'\{[^{}]*\}', raw_text)
    for c in candidates:
        try:
            data = json.loads(c)
            if 'action' in data and data['action'] != 'unknown':
                return data
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def llm_parse(message: str) -> dict:
    """
    Fallback LLM parser using SmolLM2 360M via llama.cpp.
    Uses raw completion mode (NOT conversation mode).
    Returns parsed action dict or None.
    """
    binary = get_llama_binary()
    if not binary or not os.path.exists(MODEL_PATH):
        return None

    prompt = _build_prompt(message)

    cmd = [
        binary,
        "-m", MODEL_PATH,
        "-p", prompt,
        "-n", "50",               # Max tokens (JSON is short)
        "-t", "4",                # 4 CPU threads
        "--temp", "0.1",          # Deterministic
        "--no-display-prompt",    # Don't echo prompt to stdout
        "--no-conversation",      # Force completion mode (not chat)
        "-c", "512",              # Context window
    ]

    # If --no-conversation fails, remove it and retry
    for attempt in range(2):
        try:
            proc = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                timeout=20
            )

            output = (proc.stdout + "\n" + proc.stderr).strip()
            print(f"[LLM] attempt={attempt} output: {repr(output[:300])}")

            parsed = extract_json(output)
            if parsed:
                return parsed

        except subprocess.TimeoutExpired:
            print(f"⚠️ LLM inference timed out attempt={attempt}")
        except Exception as e:
            print(f"⚠️ LLM error attempt={attempt}: {e}")

        # On first failure, try without --no-conversation
        if attempt == 0:
            cmd = [x for x in cmd if x != "--no-conversation"]

    return None
