import os
import re
import json
import subprocess
from datetime import datetime

# Paths (check ~/pocketbrain/models or relative to server)
BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
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

FEW_SHOT_SYSTEM_PROMPT = """You are PocketBrain's message parser. Convert the user message into exactly ONE JSON action line. No explanation, no markdown.

VALID ACTIONS:
- {"action":"expense","amount":180,"description":"zomato","category":"food"}
- {"action":"reminder","title":"call mom","date":"YYYY-MM-DD","time":"HH:MM"}
- {"action":"deadline","title":"assignment","subject":"OS","due_date":"YYYY-MM-DD"}
- {"action":"attendance","subject":"OS","status":"present|bunked"}
- {"action":"habit","name":"gym"}
- {"action":"note","content":"text to save"}
- {"action":"unknown"}

EXAMPLES:
User: "parso subah 10 baje doctor jana hai"
{"action":"reminder","title":"doctor jana hai","date":"DATE_PARSO","time":"10:00"}
User: "bhai 120 ka roll khaya"
{"action":"expense","amount":120,"description":"roll","category":"food"}
User: "OS assignment submit karna hai 12 oct ko"
{"action":"deadline","title":"assignment submit karna hai","subject":"OS","due_date":"2026-10-12"}
User: "dsa practice complete ho gayi"
{"action":"habit","name":"dsa"}
User: "save this link https://github.com"
{"action":"note","content":"https://github.com"}
User: "bunked TOC class today"
{"action":"attendance","subject":"TOC","status":"bunked"}
"""

def extract_json(raw_text):
    """Safely extract valid JSON object from LLM response."""
    if not raw_text:
        return None
    # Find { ... }
    m = re.search(r'\{.*?\}', raw_text, re.DOTALL)
    if m:
        try:
            return json.loads(m.group(0))
        except Exception:
            pass
    return None

def llm_parse(message: str) -> dict:
    """
    Fallback LLM parser using SmolLM2 360M via llama.cpp.
    Returns parsed dict action or {'action': 'unknown'}.
    """
    binary = get_llama_binary()
    if not binary or not os.path.exists(MODEL_PATH):
        # LLM not installed yet
        return None

    today_str = datetime.now().strftime('%Y-%m-%d')
    prompt = f"""{FEW_SHOT_SYSTEM_PROMPT}
Current Date: {today_str}
User: "{message}"
"""

    cmd = [
        binary,
        "-m", MODEL_PATH,
        "-p", prompt,
        "-n", "64",
        "-t", "4",               # 4 CPU threads
        "--temp", "0.1",         # Low temperature for deterministic JSON
        "--no-conversation",     # Exit after outputting response (don't wait for user prompt)
        "--simple-io",           # Clean stdout
        "--log-disable",         # Disable verbose logs
        "-c", "512"              # Small context size to save RAM
    ]

    try:
        proc = subprocess.run(
            cmd,
            capture_output=True,
            text=True,
            timeout=15
        )
        output = proc.stdout.strip()
        parsed = extract_json(output)
        if parsed and 'action' in parsed:
            return parsed
    except subprocess.TimeoutExpired:
        print("⚠️ LLM inference timed out (>15s)")
    except Exception as e:
        print(f"⚠️ LLM execution error: {e}")

    return None
