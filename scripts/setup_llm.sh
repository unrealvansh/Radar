#!/data/data/com.termux/files/usr/bin/bash

# =================================================================
# PocketBrain — SmolLM2 360M + llama.cpp Setup for Termux (Android)
# =================================================================

set -e

echo "🧠 Setting up SmolLM2 360M + llama.cpp on Mobistar C2..."

# 1. Install build tools
echo "📦 Installing build tools (cmake, clang, make, wget, git)..."
pkg update -y
pkg install -y cmake clang make wget git

# 2. Build llama.cpp
POCKETBRAIN_DIR="$HOME/pocketbrain"
mkdir -p "$POCKETBRAIN_DIR/models"
cd "$POCKETBRAIN_DIR"

if [ ! -d "llama.cpp" ]; then
    echo "📥 Cloning llama.cpp..."
    git clone https://github.com/ggerganov/llama.cpp
fi

echo "⚙️ Compiling llama.cpp for ARM CPU..."
cd "$POCKETBRAIN_DIR/llama.cpp"
cmake -B build
cmake --build build --config Release -j4

# 3. Download SmolLM2-360M-Instruct (Quantized Q4_K_M ~230MB)
MODEL_DEST="$POCKETBRAIN_DIR/models/smollm2-360m-instruct.Q4_K_M.gguf"
if [ ! -f "$MODEL_DEST" ]; then
    echo "📥 Downloading SmolLM2-360M-Instruct GGUF (~230MB)..."
    wget -c "https://huggingface.co/HuggingFaceTB/SmolLM2-360M-Instruct-GGUF/resolve/main/smollm2-360m-instruct-q4_k_m.gguf" -O "$MODEL_DEST"
else
    echo "✅ Model already downloaded: $MODEL_DEST"
fi

echo "=============================================================="
echo "🎉 SmolLM2 360M + llama.cpp setup is COMPLETE!"
echo "Binary: $POCKETBRAIN_DIR/llama.cpp/build/bin/llama-cli"
echo "Model:  $MODEL_DEST"
echo "=============================================================="
