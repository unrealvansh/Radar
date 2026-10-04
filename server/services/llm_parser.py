import os
import re
import json
import subprocess
import tempfile
from datetime import datetime, timedelta

# Paths
MODEL_PATH = os.path.expanduser("~/pocketbrain/models/smollm2-360m-instruct.Q4_K_M.gguf")
LLAMA_CLI_PATH = os.path.expanduser("~/pocketbrain/llama.cpp/build/bin/llama-cli")
LLAMA_LEGACY_PATH = os.path.expanduser("~/pocketbrain/llama.cpp/llama-cli")
LLAMA_MAIN_PATH = os.path.expanduser("~/pocketbrain/llama.cpp/main")
GRAMMAR_PATH = os.path.expanduser("~/pocketbrain/models/action.gbnf")

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
    """Build ChatML-formatted prompt with few-shot examples."""
    today = datetime.now()
    today_str = today.strftime('%Y-%m-%d')
    tomorrow_str = (today + timedelta(days=1)).strftime('%Y-%m-%d')

    return f"""<|im_start|>system
You are a JSON converter. Convert user messages into exactly one JSON object. Output ONLY the JSON, nothing else. No explanation.

Valid JSON formats:
{{"action":"expense","amount":NUMBER,"description":"TEXT","category":"food"}}
{{"action":"reminder","title":"TEXT","date":"{today_str}","time":"HH:MM"}}
{{"action":"deadline","title":"TEXT","subject":"TEXT","due_date":"{today_str}"}}
{{"action":"attendance","subject":"TEXT","status":"bunked"}}
{{"action":"habit","name":"TEXT"}}
{{"action":"note","content":"TEXT"}}
{{"action":"unknown"}}

Today is {today_str}. Tomorrow is {tomorrow_str}.
<|im_end|>
<|im_start|>user
120 ka chai pi
<|im_end|>
<|im_start|>assistant
{{"action":"expense","amount":120,"description":"chai","category":"food"}}
<|im_end|>
<|im_start|>user
gym done
<|im_end|>
<|im_start|>assistant
{{"action":"habit","name":"gym"}}
<|im_end|>
<|im_start|>user
bunked CN class
<|im_end|>
<|im_start|>assistant
{{"action":"attendance","subject":"CN","status":"bunked"}}
<|im_end|>
<|im_start|>user
remind me to call mom at 19:30
<|im_end|>
<|im_start|>assistant
{{"action":"reminder","title":"call mom","date":"{today_str}","time":"19:30"}}
<|im_end|>
<|im_start|>user
OS assignment submit by tomorrow
<|im_end|>
<|im_start|>assistant
{{"action":"deadline","title":"assignment submit","subject":"OS","due_date":"{tomorrow_str}"}}
<|im_end|>
<|im_start|>user
save important: placement talk by google on oct 20
<|im_end|>
<|im_start|>assistant
{{"action":"note","content":"placement talk by google on oct 20"}}
<|im_end|>
<|im_start|>user
{message}
<|im_end|>
<|im_start|>assistant
"""


def extract_json(raw_text):
    """Extract valid JSON with 'action' key from raw LLM output."""
    if not raw_text:
        return None

    # Try to find JSON objects in the text
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
    Returns parsed action dict or None.
    """
    binary = get_llama_binary()
    if not binary or not os.path.exists(MODEL_PATH):
        return None

    prompt = _build_prompt(message)

    # Write prompt to a temp file to avoid shell escaping issues
    tmp = None
    try:
        tmp = tempfile.NamedTemporaryFile(mode='w', suffix='.txt', delete=False, encoding='utf-8')
        tmp.write(prompt)
        tmp.close()

        cmd = [
            binary,
            "-m", MODEL_PATH,
            "--file", tmp.name,       # Read prompt from file (avoids shell escaping)
            "-n", "80",               # Max tokens to generate
            "-t", "4",                # 4 CPU threads
            "--temp", "0.1",          # Low temperature for deterministic output
            "--single-turn",          # Exit after one response
            "--no-display-prompt",    # Don't echo prompt back to stdout
            "-c", "512",              # Small context window to save RAM
        ]

        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=20
        )

        output = proc.stdout.strip()
        stderr = proc.stderr.strip()

        # Debug logging
        print(f"[LLM] stdout: {output[:200]}")
        if proc.returncode != 0:
            print(f"[LLM] stderr: {stderr[:200]}")

        parsed = extract_json(output)
        if parsed:
            return parsed

        # If stdout failed, also check stderr (some versions print there)
        parsed = extract_json(stderr)
        if parsed:
            return parsed

    except subprocess.TimeoutExpired:
        print("⚠️ LLM inference timed out (>20s)")
    except Exception as e:
        print(f"⚠️ LLM execution error: {e}")
    finally:
        if tmp and os.path.exists(tmp.name):
            os.unlink(tmp.name)

    return None
