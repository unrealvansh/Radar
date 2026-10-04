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
    """Build a concise instruction prompt with real examples."""
    today_str = datetime.now().strftime('%Y-%m-%d')
    tomorrow_str = (datetime.now() + timedelta(days=1)).strftime('%Y-%m-%d')

    return (
        'Convert to JSON. Examples: '
        '"chai 20" -> {"action":"expense","amount":20,"description":"chai","category":"food"}. '
        '"auto 30" -> {"action":"expense","amount":30,"description":"auto","category":"transport"}. '
        '"gym done" -> {"action":"habit","name":"gym"}. '
        '"bunked CN" -> {"action":"attendance","subject":"CN","status":"bunked"}. '
        f'"remind me call mom at 7pm" -> {{"action":"reminder","title":"call mom","date":"{today_str}","time":"19:00"}}. '
        f'"OS assignment due tomorrow" -> {{"action":"deadline","title":"assignment","subject":"OS","due_date":"{tomorrow_str}"}}. '
        '"save placement talk on oct 20" -> {"action":"note","content":"placement talk on oct 20"}. '
        f'Now convert this message to JSON: "{message}"'
    )


def extract_json(raw_text):
    """Extract valid JSON with 'action' key from LLM output."""
    if not raw_text:
        return None

    # Strip markdown code fences if present
    cleaned = re.sub(r'```json\s*', '', raw_text)
    cleaned = re.sub(r'```\s*', '', cleaned)

    # Find all JSON object candidates
    candidates = re.findall(r'\{[^{}]*\}', cleaned)
    for c in candidates:
        try:
            data = json.loads(c)
            if 'action' in data and data['action'] != 'unknown':
                # Normalize amount to float if present
                if 'amount' in data:
                    try:
                        data['amount'] = float(data['amount'])
                    except (ValueError, TypeError):
                        pass
                return data
        except (json.JSONDecodeError, ValueError):
            continue
    return None


def llm_parse(message: str) -> dict:
    """
    Fallback LLM parser using SmolLM2 360M via llama.cpp.
    Uses conversation mode with --single-turn (proven working approach).
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
        "--temp", "0.1",          # Low temperature for deterministic output
        "--single-turn",          # Generate one response and exit
        "--simple-io",            # Streamlined I/O
        "--no-display-prompt",    # Don't echo prompt to stdout
        "-c", "512",              # Context window
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=25
        )

        # Combine stdout and stderr for parsing
        output = (proc.stdout + "\n" + proc.stderr).strip()
        print(f"[LLM] raw output: {repr(output[:300])}")

        parsed = extract_json(output)
        if parsed:
            print(f"[LLM] parsed: {parsed}")
            return parsed
        else:
            print(f"[LLM] no valid JSON found in output")

    except subprocess.TimeoutExpired:
        print("⚠️ LLM inference timed out (>25s)")
    except Exception as e:
        print(f"⚠️ LLM error: {e}")

    return None
