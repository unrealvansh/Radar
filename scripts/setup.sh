#!/bin/bash
# ============================================================
# PocketBrain — One-Time Setup Script for Termux
# Run this ONCE when you first set up the phone.
# ============================================================

echo "🧠 PocketBrain — Initial Setup"
echo "================================"

# 1. Update packages
echo "📦 Updating packages..."
pkg update -y && pkg upgrade -y

# 2. Install required packages
echo "📦 Installing Python, Git, SSH, and tools..."
pkg install -y python git openssh nano curl wget termux-api

# 3. Set up project directory
echo "📁 Setting up project directory..."
PROJ_DIR="$HOME/pocketbrain"

# If pocketbrain doesn't exist yet, create it
if [ ! -d "$PROJ_DIR" ]; then
    mkdir -p "$PROJ_DIR"/{server,frontend,data,storage,logs,config,scripts}
    mkdir -p "$PROJ_DIR"/storage/{cloud,notes,downloads,bookmarks,print-queue}
    echo "✅ Project directories created!"
else
    echo "ℹ️  Project directory already exists, skipping."
fi

# 4. Set up Python virtual environment
echo "🐍 Setting up Python virtual environment..."
cd "$PROJ_DIR"
python -m venv venv
source venv/bin/activate

# 5. Install Python dependencies
echo "📦 Installing Python libraries..."
pip install --upgrade pip
pip install flask apscheduler requests

# 6. Set up SSH
echo "🔐 Setting up SSH server..."
echo "Please set a password for SSH access:"
passwd

# 7. Acquire wake lock (keeps phone awake)
echo "🔒 Acquiring wake lock..."
termux-wake-lock 2>/dev/null || echo "⚠️  termux-wake-lock not available, install Termux:API"

# 8. Set up auto-start on boot
echo "🚀 Setting up auto-start..."
mkdir -p ~/.termux/boot
cat > ~/.termux/boot/start-pocketbrain.sh << 'BOOTEOF'
#!/data/data/com.termux/files/usr/bin/bash
termux-wake-lock
cd ~/pocketbrain
source venv/bin/activate
python server/app.py >> logs/app.log 2>&1 &
BOOTEOF
chmod +x ~/.termux/boot/start-pocketbrain.sh

echo ""
echo "================================"
echo "✅ Setup complete!"
echo ""
echo "Next steps:"
echo "  1. Copy your project files to ~/pocketbrain/"
echo "  2. Run: cd ~/pocketbrain && source venv/bin/activate"
echo "  3. Run: python server/app.py"
echo "  4. Open browser: http://localhost:5000"
echo ""
echo "SSH into this phone from laptop:"
echo "  ssh -p 8022 $(whoami)@$(ifconfig wlan0 2>/dev/null | grep 'inet ' | awk '{print $2}')"
echo "================================"
