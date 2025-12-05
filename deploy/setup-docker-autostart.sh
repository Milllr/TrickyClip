#!/bin/bash
# setup docker compose to auto-start on vm boot

set -e

echo "🐳 Setting up Docker Compose auto-start..."

# create systemd service for docker compose
sudo tee /etc/systemd/system/trickyclip-docker.service > /dev/null <<EOF
[Unit]
Description=TrickyClip Docker Compose
After=docker.service network-online.target
Requires=docker.service
Wants=network-online.target

[Service]
Type=oneshot
RemainAfterExit=yes
WorkingDirectory=/opt/trickyclip
ExecStart=/usr/local/bin/docker-compose up -d
ExecStop=/usr/local/bin/docker-compose down
TimeoutStartSec=0

[Install]
WantedBy=multi-user.target
EOF

# reload systemd
sudo systemctl daemon-reload

# enable the service
sudo systemctl enable trickyclip-docker

echo "✅ Docker Compose auto-start enabled!"
echo ""
echo "📊 Services will start automatically on boot"
echo "🔄 Manual control:"
echo "  - Start: sudo systemctl start trickyclip-docker"
echo "  - Stop: sudo systemctl stop trickyclip-docker"
echo "  - Status: sudo systemctl status trickyclip-docker"

