#!/bin/bash
# google cloud vm setup script for trickyclip
# run this script on your new google cloud vm

set -e

echo "🚀 Setting up TrickyClip on Google Cloud VM..."

# update system
echo "📦 Updating system packages..."
sudo apt-get update
sudo apt-get upgrade -y

# install docker
echo "🐳 Installing Docker..."
sudo apt-get install -y apt-transport-https ca-certificates curl software-properties-common
curl -fsSL https://download.docker.com/linux/ubuntu/gpg | sudo gpg --dearmor -o /usr/share/keyrings/docker-archive-keyring.gpg
echo "deb [arch=$(dpkg --print-architecture) signed-by=/usr/share/keyrings/docker-archive-keyring.gpg] https://download.docker.com/linux/ubuntu $(lsb_release -cs) stable" | sudo tee /etc/apt/sources.list.d/docker.list > /dev/null
sudo apt-get update
sudo apt-get install -y docker-ce docker-ce-cli containerd.io docker-compose-plugin

# add user to docker group
sudo usermod -aG docker $USER

# install docker compose standalone
echo "📦 Installing Docker Compose..."
sudo curl -L "https://github.com/docker/compose/releases/latest/download/docker-compose-$(uname -s)-$(uname -m)" -o /usr/local/bin/docker-compose
sudo chmod +x /usr/local/bin/docker-compose

# install cloudflared
echo "☁️ Installing Cloudflare Tunnel..."
curl -L --output cloudflared.deb https://github.com/cloudflare/cloudflared/releases/latest/download/cloudflared-linux-amd64.deb
sudo dpkg -i cloudflared.deb
rm cloudflared.deb

# create app directory
echo "📁 Creating application directory..."
sudo mkdir -p /opt/trickyclip
sudo chown $USER:$USER /opt/trickyclip

# create data directories
sudo mkdir -p /data/originals /data/candidates /data/final_clips
sudo chown -R $USER:$USER /data

echo "✅ Base setup complete!"
echo ""
echo "📋 Next steps:"
echo "1. Upload your TrickyClip files to /opt/trickyclip"
echo "2. Set up Cloudflare tunnel credentials"
echo "3. Run docker-compose up -d"



