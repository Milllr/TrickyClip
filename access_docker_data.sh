#!/bin/bash
echo "=== Accessing Data Inside Docker Volumes ==="
echo ""
echo "The /data directory is inside Docker containers, not on the host."
echo "Here's how to access it:"
echo ""
cat << 'SCRIPT'
# You're currently on the VM. Navigate to deploy directory:
cd /opt/trickyclip/deploy

# Option 1: List files in originals directory via Docker
echo "Files in originals directory:"
docker compose exec -T backend ls -lh /data/originals | head -20

# Option 2: Check disk usage inside container
echo ""
echo "Disk usage inside container:"
docker compose exec -T backend df -h /data

# Option 3: Get file sizes
echo ""
echo "Finding largest files:"
docker compose exec -T backend du -h /data/originals | sort -rh | head -10

# Option 4: Delete a specific file
echo ""
echo "To delete a file:"
echo "docker compose exec -T backend rm /data/originals/FILENAME.MP4"
echo ""
echo "Example:"
echo "docker compose exec -T backend rm /data/originals/6270feee106b9c066583e13fefacf2fc.MP4"

# Option 5: Clean up via API (once deployed)
echo ""
echo "Or use the cleanup API:"
echo "curl -X POST https://trickyclip.com/api/admin/storage/cleanup -H 'Content-Type: application/json' -d '{\"aggressive\": false}'"
SCRIPT
