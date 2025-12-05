#!/bin/bash
# cleanup cache files on VM that might cause permission issues

echo "cleaning up cache files on VM..."

cd /opt/trickyclip

# remove python cache
sudo find backend -type d -name "__pycache__" -exec rm -rf {} + 2>/dev/null || true
sudo find backend -name "*.pyc" -delete 2>/dev/null || true

# fix ownership
sudo chown -R kahuna:kahuna /opt/trickyclip/backend
sudo chown -R kahuna:kahuna /opt/trickyclip/frontend
sudo chown -R kahuna:kahuna /opt/trickyclip/deploy

echo "cleanup complete"

