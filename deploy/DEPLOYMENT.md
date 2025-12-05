# TrickyClip Deployment Guide

## ✅ What's Already Set Up

Your TrickyClip is now deployed and accessible at **https://trickyclip.com**!

### Cloudflare Tunnel Status

- **Tunnel Name**: trickyclip
- **Tunnel ID**: 5bc69abe-fe75-4cbe-9421-14a358ffede0
- **Status**: Running (4 connections to Cloudflare edge)
- **DNS**: trickyclip.com → Cloudflare Tunnel CNAME

### Service URLs

- **Frontend**: https://trickyclip.com
- **Backend API**: https://trickyclip.com/api/*
- **Upload**: https://trickyclip.com/upload
- **Sort**: https://trickyclip.com/sort
- **Clips**: https://trickyclip.com/clips

## 🔍 Verify Deployment

DNS propagation can take 1-5 minutes. To check if your site is live:

```bash
# check DNS
dig +short trickyclip.com

# test the site
curl -I https://trickyclip.com
```

Or just open https://trickyclip.com in your browser!

## 🚀 Managing the Tunnel

### Check Tunnel Status

```bash
# view running tunnel
ps aux | grep cloudflared

# check tunnel logs
tail -f ~/.cursor/projects/Users-kahuna-code-TrickyClip/terminals/2.txt
```

### Stop the Tunnel

```bash
# find the process
ps aux | grep cloudflared

# kill it
kill <PID>
```

### Restart the Tunnel

```bash
cd /Users/kahuna/code/TrickyClip/deploy
./start-tunnel.sh
```

## 🔄 Auto-Start on System Boot

To make the tunnel start automatically when your Mac boots:

### Option 1: Using brew services (Recommended)

```bash
brew services start cloudflared
```

### Option 2: Create a LaunchAgent

```bash
# create launch agent plist
cat > ~/Library/LaunchAgents/com.trickyclip.tunnel.plist << 'EOF'
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.trickyclip.tunnel</string>
    <key>ProgramArguments</key>
    <array>
        <string>/Users/kahuna/code/TrickyClip/deploy/start-tunnel.sh</string>
    </array>
    <key>RunAtLoad</key>
    <true/>
    <key>KeepAlive</key>
    <true/>
    <key>StandardOutPath</key>
    <string>/Users/kahuna/code/TrickyClip/deploy/tunnel.log</string>
    <key>StandardErrorPath</key>
    <string>/Users/kahuna/code/TrickyClip/deploy/tunnel-error.log</string>
</dict>
</plist>
EOF

# load the service
launchctl load ~/Library/LaunchAgents/com.trickyclip.tunnel.plist

# start it
launchctl start com.trickyclip.tunnel
```

## 🔐 Important: Domain Setup

**CRITICAL**: Make sure `trickyclip.com` is added to your Cloudflare account:

1. Go to [Cloudflare Dashboard](https://dash.cloudflare.com)
2. Click "Add a site"
3. Enter `trickyclip.com`
4. Follow the nameserver setup instructions
5. Update your domain registrar to use Cloudflare's nameservers

If the domain isn't on Cloudflare yet, the DNS routing won't work!

## 🛠 Troubleshooting

### "Site can't be reached"

1. **Check DNS propagation**:
   ```bash
   dig +short trickyclip.com
   ```
   Should return Cloudflare IPs or CNAME

2. **Verify tunnel is running**:
   ```bash
   ps aux | grep cloudflared
   ```

3. **Check Docker containers**:
   ```bash
   cd /Users/kahuna/code/TrickyClip/deploy
   docker compose ps
   ```
   All should show "Up"

4. **Test local services**:
   ```bash
   curl http://localhost:3000  # frontend
   curl http://localhost:8001  # backend
   ```

### Tunnel keeps disconnecting

The tunnel may stop if your Mac sleeps. Use the LaunchAgent setup above to auto-restart.

### DNS not propagating

- Wait 5-10 minutes
- Clear your DNS cache: `sudo dscacheutil -flushcache; sudo killall -HUP mDNSResponder`
- Try accessing from your phone (different network)

## 📊 Monitoring

View tunnel metrics:
```bash
# tunnel exposes metrics on localhost
curl http://localhost:20241/metrics
```

## 🔄 Updating Your Site

After making code changes:

```bash
# rebuild and restart docker
cd /Users/kahuna/code/TrickyClip/deploy
docker compose down
docker compose up -d --build

# tunnel will automatically route to the new containers
```

## 🎯 Next Steps

Your TrickyClip is live! You can now:

1. ✅ Upload videos via https://trickyclip.com/upload
2. ✅ Sort clips via https://trickyclip.com/sort
3. ✅ Browse clips via https://trickyclip.com/clips
4. ✅ Clips auto-upload to your Google Drive
5. ✅ Share the site with friends (they'll need the password)

## 🔒 Security Notes

- The tunnel is secure (encrypted TLS connection)
- Add authentication to `/upload` and `/sort` routes in production
- Keep your tunnel credentials safe: `~/.cloudflared/*.json`
- These are already in `.gitignore`

## 🎉 You're Live!

TrickyClip is now accessible worldwide at **https://trickyclip.com** 🚀

