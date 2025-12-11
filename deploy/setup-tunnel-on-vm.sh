#!/bin/bash
# setup cloudflare tunnel on google cloud vm
# run this after transferring tunnel credentials

set -e

echo "☁️ Setting up Cloudflare Tunnel as a service..."

# create systemd service for cloudflare tunnel
sudo tee /etc/systemd/system/cloudflared-tunnel.service > /dev/null <<EOF
[Unit]
Description=Cloudflare Tunnel
After=network.target

[Service]
Type=simple
User=$USER
ExecStart=/usr/local/bin/cloudflared tunnel --config /opt/trickyclip/cloudflared-config.yml run trickyclip
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
EOF

# reload systemd
sudo systemctl daemon-reload

# enable and start the service
sudo systemctl enable cloudflared-tunnel
sudo systemctl start cloudflared-tunnel

echo "✅ Cloudflare Tunnel service installed and started!"
echo ""
echo "📊 Check status with: sudo systemctl status cloudflared-tunnel"
echo "📋 View logs with: sudo journalctl -u cloudflared-tunnel -f"



