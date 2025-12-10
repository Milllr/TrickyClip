# TrickyClip Google Cloud Deployment Checklist

Quick reference for deploying TrickyClip to Google Cloud.

## ✅ Pre-Deployment Checklist

- [x] Code working locally
- [x] Docker containers running locally
- [x] Cloudflare tunnel configured
- [x] Google Drive integration set up
- [ ] Google Cloud account created
- [ ] $300 free credits activated

---

## 🚀 Deployment Steps (30 minutes)

### Step 1: Create VM (5 min)
- [ ] Go to https://console.cloud.google.com/compute/instances
- [ ] Create instance: `trickyclip-server`
- [ ] Machine type: `e2-medium` (2 vCPU, 4 GB)
- [ ] Boot disk: Ubuntu 22.04 LTS, 50 GB
- [ ] Allow HTTP/HTTPS traffic
- [ ] Click CREATE

### Step 2: Set Up VM (5 min)
- [ ] SSH into VM (click SSH button in console)
- [ ] Copy and run setup script:
  ```bash
  # on your Mac
  gcloud compute scp deploy/google-cloud-setup.sh trickyclip-server:~/ --zone=YOUR_ZONE
  
  # on the VM
  bash ~/google-cloud-setup.sh
  exit  # log out and back in
  ```

### Step 3: Transfer Files (10 min)
- [ ] Copy backend: `gcloud compute scp --recurse backend/ trickyclip-server:/opt/trickyclip/backend/ --zone=YOUR_ZONE`
- [ ] Copy frontend: `gcloud compute scp --recurse frontend/ trickyclip-server:/opt/trickyclip/frontend/ --zone=YOUR_ZONE`
- [ ] Copy deploy: `gcloud compute scp --recurse deploy/ trickyclip-server:/opt/trickyclip/deploy/ --zone=YOUR_ZONE`
- [ ] Copy secrets: `gcloud compute scp --recurse secrets/ trickyclip-server:/opt/trickyclip/secrets/ --zone=YOUR_ZONE`
- [ ] Copy tunnel creds: `gcloud compute scp ~/.cloudflared/*.json trickyclip-server:~/.cloudflared/ --zone=YOUR_ZONE`
- [ ] Copy tunnel cert: `gcloud compute scp ~/.cloudflared/cert.pem trickyclip-server:~/.cloudflared/ --zone=YOUR_ZONE`

### Step 4: Start Services (5 min)
- [ ] SSH into VM
- [ ] Start Docker: `cd /opt/trickyclip/deploy && docker-compose up -d`
- [ ] Verify: `docker-compose ps` (all should be "Up")

### Step 5: Set Up Auto-Start (3 min)
- [ ] Setup tunnel: `cd /opt/trickyclip/deploy && bash setup-tunnel-on-vm.sh`
- [ ] Setup Docker: `bash setup-docker-autostart.sh`
- [ ] Test reboot: `sudo reboot` then verify services restart

### Step 6: Verify (2 min)
- [ ] Open https://trickyclip.com in browser
- [ ] Upload a test video
- [ ] Check worker processing: `docker-compose logs -f worker`

### Step 7: Stop Local Services
- [ ] On Mac: `cd deploy && docker-compose down`
- [ ] Kill local tunnel: `ps aux | grep cloudflared` → `kill <PID>`
- [ ] Verify site still works (now running on Google Cloud!)

---

## 🎯 Quick Commands Reference

### SSH into VM
```bash
gcloud compute ssh trickyclip-server --zone=YOUR_ZONE
```

### Check Services
```bash
# docker containers
cd /opt/trickyclip/deploy && docker-compose ps

# tunnel
sudo systemctl status cloudflared-tunnel

# worker logs
docker-compose logs -f worker
```

### Restart Services
```bash
# docker
docker-compose restart

# tunnel
sudo systemctl restart cloudflared-tunnel
```

### Update Code
```bash
# on Mac - copy files
gcloud compute scp --recurse backend/ trickyclip-server:/opt/trickyclip/backend/ --zone=YOUR_ZONE

# on VM - rebuild
cd /opt/trickyclip/deploy
docker-compose up -d --build
```

---

## 📍 Important Paths on VM

- Code: `/opt/trickyclip/`
- Data: `/data/` (originals, candidates, final_clips)
- Tunnel config: `/opt/trickyclip/deploy/cloudflared-config.yml`
- Tunnel creds: `~/.cloudflared/`
- Secrets: `/opt/trickyclip/secrets/`

---

## 💡 Tips

- Replace `YOUR_ZONE` with your actual zone (e.g., `us-central1-a`)
- Get your zone from: https://console.cloud.google.com/compute/instances
- Save your external IP for easy SSH access
- Bookmark the Google Cloud Console

---

## 🆘 Need Help?

See the full guide: `GOOGLE-CLOUD-DEPLOY.md`

Or check logs:
```bash
# all services
docker-compose logs

# specific service
docker-compose logs worker
docker-compose logs backend

# tunnel
sudo journalctl -u cloudflared-tunnel -f
```

---

## 🎉 Success Criteria

✅ https://trickyclip.com loads  
✅ Can upload videos  
✅ Worker processes them automatically  
✅ Final clips appear in Google Drive  
✅ Everything survives VM reboot  
✅ Your laptop can be off!  

**You're deployed!** 🚀


