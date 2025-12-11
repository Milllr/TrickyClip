# TrickyClip Google Cloud Deployment Guide

Deploy TrickyClip to run 24/7 on Google Cloud (FREE for ~1 year with $300 credits).

## 📋 Prerequisites

- Google Cloud account with $300 free credits
- Your TrickyClip code (already done ✓)
- Cloudflare tunnel credentials (already done ✓)
- Google Drive credentials (already done ✓)

---

## 🚀 Part 1: Create the VM

### 1. Go to Google Cloud Console

Visit: https://console.cloud.google.com/compute/instances

### 2. Create Instance

Click **"CREATE INSTANCE"** and configure:

**Basic settings:**
- **Name:** `trickyclip-server`
- **Region:** Choose closest to you (e.g., `us-central1` or `us-east1`)
- **Zone:** Any (e.g., `us-central1-a`)

**Machine configuration:**
- **Series:** E2
- **Machine type:** `e2-medium` (2 vCPU, 4 GB RAM)
  - Cost: ~$25/month (covered by free credits)
  - Enough for video processing

**Boot disk:**
- Click "CHANGE"
- **Operating system:** Ubuntu
- **Version:** Ubuntu 22.04 LTS
- **Boot disk type:** Balanced persistent disk
- **Size:** 50 GB (or more if you'll store lots of originals)

**Firewall:**
- ✅ Allow HTTP traffic
- ✅ Allow HTTPS traffic

**Advanced options → Networking:**
- **Network tags:** Add `trickyclip-server`

Click **"CREATE"**

### 3. Wait for VM to Start

Takes ~30 seconds. You'll see a green checkmark when ready.

---

## 🔐 Part 2: Connect to Your VM

### Option A: SSH from Browser (Easiest)

1. Click the **SSH** button next to your instance
2. A terminal will open in your browser

### Option B: SSH from Terminal

```bash
# get the external IP from the console
gcloud compute ssh trickyclip-server --zone=us-central1-a
```

---

## 📦 Part 3: Set Up the VM

### 1. Run the Setup Script

In your **local terminal** (on your Mac), copy the setup script to the VM:

```bash
cd /Users/kahuna/code/TrickyClip/deploy

# copy setup script to VM (replace EXTERNAL_IP with your VM's IP)
gcloud compute scp google-cloud-setup.sh trickyclip-server:~/ --zone=us-central1-a

# SSH into the VM
gcloud compute ssh trickyclip-server --zone=us-central1-a

# run the setup script
bash ~/google-cloud-setup.sh
```

This installs:
- Docker & Docker Compose
- Cloudflare Tunnel
- Creates necessary directories

**Note:** After the script completes, you need to **log out and back in** for Docker permissions:

```bash
exit
# then SSH back in
gcloud compute ssh trickyclip-server --zone=us-central1-a
```

### 2. Verify Docker Works

```bash
docker --version
docker-compose --version
```

Should show versions without errors.

---

## 📤 Part 4: Transfer Your Files

On your **Mac terminal**:

```bash
cd /Users/kahuna/code/TrickyClip

# copy backend code
gcloud compute scp --recurse backend/ trickyclip-server:/opt/trickyclip/backend/ --zone=us-central1-a

# copy frontend code
gcloud compute scp --recurse frontend/ trickyclip-server:/opt/trickyclip/frontend/ --zone=us-central1-a

# copy deployment files
gcloud compute scp --recurse deploy/ trickyclip-server:/opt/trickyclip/deploy/ --zone=us-central1-a

# copy secrets (google drive credentials)
gcloud compute scp --recurse secrets/ trickyclip-server:/opt/trickyclip/secrets/ --zone=us-central1-a

# copy tunnel credentials
gcloud compute scp ~/.cloudflared/5bc69abe-fe75-4cbe-9421-14a358ffede0.json trickyclip-server:~/.cloudflared/ --zone=us-central1-a

# copy tunnel cert
gcloud compute scp ~/.cloudflared/cert.pem trickyclip-server:~/.cloudflared/ --zone=us-central1-a
```

### Update Tunnel Config on VM

SSH back into the VM and update the tunnel config path:

```bash
gcloud compute ssh trickyclip-server --zone=us-central1-a

# create .cloudflared directory
mkdir -p ~/.cloudflared

# edit tunnel config to use correct paths
nano /opt/trickyclip/deploy/cloudflared-config.yml
```

The file should look like:

```yaml
tunnel: 5bc69abe-fe75-4cbe-9421-14a358ffede0
credentials-file: /home/YOUR_USERNAME/.cloudflared/5bc69abe-fe75-4cbe-9421-14a358ffede0.json

ingress:
  - hostname: trickyclip.com
    path: /api/*
    service: http://localhost:8001
  
  - hostname: trickyclip.com
    service: http://localhost:3000
  
  - service: http_status:404
```

(Replace `YOUR_USERNAME` with your actual username, check with `whoami`)

Save and exit (Ctrl+X, Y, Enter).

---

## 🐳 Part 5: Start Docker Services

Still on the VM:

```bash
cd /opt/trickyclip/deploy

# start all services
docker-compose up -d

# check status
docker-compose ps
```

All services should show "Up".

### Check Logs if Needed

```bash
# backend logs
docker-compose logs backend

# worker logs
docker-compose logs worker

# all logs
docker-compose logs -f
```

---

## ☁️ Part 6: Set Up Auto-Start

### 1. Set Up Cloudflare Tunnel Service

```bash
cd /opt/trickyclip/deploy
bash setup-tunnel-on-vm.sh
```

Verify it's running:

```bash
sudo systemctl status cloudflared-tunnel
```

### 2. Set Up Docker Auto-Start

```bash
bash setup-docker-autostart.sh
```

### 3. Test Auto-Start

Reboot the VM to verify everything starts automatically:

```bash
sudo reboot
```

Wait 2 minutes, then SSH back in:

```bash
gcloud compute ssh trickyclip-server --zone=us-central1-a

# check if services are running
docker ps
sudo systemctl status cloudflared-tunnel
```

All should be up and running!

---

## 🌐 Part 7: Verify Deployment

### Check Your Site

Open in browser: **https://trickyclip.com**

You should see your TrickyClip frontend!

### Test the API

```bash
curl https://trickyclip.com/api/
```

### Monitor Services

```bash
# docker containers
cd /opt/trickyclip/deploy
docker-compose ps

# tunnel status
sudo systemctl status cloudflared-tunnel

# tunnel logs
sudo journalctl -u cloudflared-tunnel -f

# worker logs (processing uploads)
docker-compose logs -f worker
```

---

## 🎯 Part 8: Stop Your Local Services

Now that everything is on Google Cloud, you can stop the services on your laptop:

**On your Mac:**

```bash
cd /Users/kahuna/code/TrickyClip/deploy

# stop docker containers
docker-compose down

# stop local tunnel (find process)
ps aux | grep cloudflared
kill <PID>
```

Your site will **continue running** on Google Cloud! 🎉

---

## 📊 Monitoring & Maintenance

### Check VM Status

Go to: https://console.cloud.google.com/compute/instances

### SSH Into VM Anytime

```bash
gcloud compute ssh trickyclip-server --zone=us-central1-a
```

### Restart Services

```bash
# restart docker containers
cd /opt/trickyclip/deploy
docker-compose restart

# restart tunnel
sudo systemctl restart cloudflared-tunnel
```

### View Logs

```bash
# worker processing logs
docker-compose logs -f worker

# backend logs
docker-compose logs -f backend

# tunnel logs
sudo journalctl -u cloudflared-tunnel -f
```

### Update Code

When you make changes locally:

```bash
# on your Mac, copy updated files
gcloud compute scp --recurse backend/ trickyclip-server:/opt/trickyclip/backend/ --zone=us-central1-a

# SSH into VM
gcloud compute ssh trickyclip-server --zone=us-central1-a

# rebuild and restart
cd /opt/trickyclip/deploy
docker-compose up -d --build
```

---

## 💰 Cost Breakdown

With your **$300 free credits**:

- VM (e2-medium): ~$25/month
- Storage (50GB): ~$2/month
- Network egress: ~$1-5/month (depending on video uploads)

**Total:** ~$28-32/month = **~10 months free** with your credits

After credits run out, you can:
- Continue paying ~$30/month
- Downgrade to e2-small (~$12/month) if traffic is low
- Move to cheaper VPS (Hetzner $4/month)

---

## 🔥 What Happens Now

✅ **TrickyClip runs 24/7** on Google Cloud  
✅ **Users can upload anytime** - even when your laptop is off  
✅ **Worker auto-processes** videos in the background  
✅ **Clips auto-upload** to Google Drive  
✅ **Auto-restarts** if VM reboots  
✅ **Cloudflare CDN** speeds up delivery worldwide  

Your laptop can be **completely off** - TrickyClip keeps running! 🚀

---

## 🐛 Troubleshooting

### Site not loading?

```bash
# check docker
docker-compose ps

# check tunnel
sudo systemctl status cloudflared-tunnel

# restart everything
docker-compose restart
sudo systemctl restart cloudflared-tunnel
```

### Worker not processing uploads?

```bash
# check worker logs
docker-compose logs worker

# restart worker
docker-compose restart worker
```

### Out of disk space?

```bash
# check disk usage
df -h

# clean up old docker images
docker system prune -a
```

### Need more resources?

In Google Cloud Console:
1. Stop the instance
2. Edit → Machine type → Choose larger size
3. Start the instance

---

## 🎉 You're Done!

TrickyClip is now running 24/7 on Google Cloud!

**Your site:** https://trickyclip.com  
**Cost:** FREE for ~10 months  
**Uptime:** Always online  
**Your laptop:** Can stay off!  

Share the URL with your crew and start collecting clips! 🎿📹



