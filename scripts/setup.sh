#!/bin/bash
PROJ_DIR="$(cd "$(dirname "$0")/.." && pwd)"
cd "$PROJ_DIR" || exit 1

echo "Installing packages..."
pkg update -y && pkg upgrade -y
pkg install -y python openssh termux-api

echo "Creating the Python environment..."
python -m venv venv
source venv/bin/activate
pip install --upgrade pip
pip install -r server/requirements.txt
mkdir -p data logs

echo "Set a password for SSH access:"
passwd

mkdir -p ~/.termux/boot
cat > ~/.termux/boot/start-radar.sh << BOOT
bash "$PROJ_DIR/scripts/start.sh"
BOOT
chmod +x ~/.termux/boot/start-radar.sh

echo
echo "Setup complete. Start Radar with: bash scripts/start.sh"
echo "SSH from your computer: ssh -p 8022 $(whoami)@$(ifconfig wlan0 2>/dev/null | awk '/inet /{print $2}')"
