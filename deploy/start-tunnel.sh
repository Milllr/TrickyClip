#!/bin/bash
# start cloudflare tunnel for trickyclip

echo "starting cloudflare tunnel..."
cloudflared tunnel --config /Users/kahuna/code/TrickyClip/deploy/cloudflared-config.yml run trickyclip

