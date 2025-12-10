# TrickyClip Deployment Guide

## Quick Deploy

From your local machine:

```bash
cd /Users/kahuna/code/TrickyClip
chmod +x deploy/deploy.sh
./deploy/deploy.sh
```

## What the Deploy Script Does

1. **Uploads code** - syncs backend, frontend, and deploy configs to VM
2. **Runs migrations** - applies database schema changes via Alembic
3. **Rebuilds containers** - builds new Docker images with latest code
4. **Restarts services** - zero-downtime restart of backend, frontend, worker
5. **Verifies deployment** - checks that services are running

## Emergency Rollback

If something goes wrong:

```bash
chmod +x deploy/rollback.sh
./deploy/rollback.sh
```

This will:
- Revert the last database migration
- Restart services with previous containers
- Display logs for verification

## Manual Deployment Steps

If you prefer manual control:

### 1. Upload Code

```bash
cd /Users/kahuna/code/TrickyClip
gcloud compute scp --recurse backend/ kahuna@trickyclip-server:/opt/trickyclip/ --zone=us-central1-c
gcloud compute scp --recurse frontend/ kahuna@trickyclip-server:/opt/trickyclip/ --zone=us-central1-c
gcloud compute scp --recurse deploy/ kahuna@trickyclip-server:/opt/trickyclip/ --zone=us-central1-c
```

### 2. SSH to VM

```bash
gcloud compute ssh kahuna@trickyclip-server --zone=us-central1-c
```

### 3. Run Migrations

```bash
cd /opt/trickyclip
docker compose exec backend alembic upgrade head
```

### 4. Rebuild & Restart

```bash
cd /opt/trickyclip/deploy
docker compose up -d --build
```

### 5. Verify

```bash
docker compose ps
docker compose logs backend --tail=50
docker compose logs worker --tail=50
```

## Database Migrations

### Create New Migration

When you add new models or fields:

```bash
# on your local machine
cd /Users/kahuna/code/TrickyClip/backend
docker compose exec backend alembic revision --autogenerate -m "description of changes"
```

### Apply Migration

```bash
# on the VM
docker compose exec backend alembic upgrade head
```

### Rollback Migration

```bash
# rollback last migration
docker compose exec backend alembic downgrade -1

# rollback to specific version
docker compose exec backend alembic downgrade <revision_id>
```

### View Migration History

```bash
docker compose exec backend alembic history
docker compose exec backend alembic current
```

## Monitoring

### View Logs

```bash
# all services
docker compose logs -f

# specific service
docker compose logs -f backend
docker compose logs -f worker
docker compose logs -f frontend

# last N lines
docker compose logs backend --tail=100
```

### Check Service Health

```bash
# service status
docker compose ps

# resource usage
docker stats

# disk space
df -h

# check database
docker compose exec db psql -U postgres -d trickyclip -c "SELECT COUNT(*) FROM original_files;"
```

### Monitor Jobs

```bash
# check job queue status
curl http://localhost:8001/api/jobs/

# check clips count
curl http://localhost:8001/api/clips/stats
```

## Troubleshooting

### Services Won't Start

```bash
# check logs
docker compose logs backend
docker compose logs worker

# rebuild from scratch
docker compose down
docker compose build --no-cache
docker compose up -d
```

### Database Connection Issues

```bash
# check database is running
docker compose ps db

# test connection
docker compose exec db psql -U postgres -d trickyclip -c "SELECT 1;"

# check environment variables
docker compose exec backend printenv | grep DATABASE
```

### Worker Not Processing Jobs

```bash
# check worker logs
docker compose logs worker -f

# check Redis connection
docker compose exec backend python -c "from redis import Redis; from app.core.config import settings; r = Redis.from_url(settings.REDIS_URL); print(r.ping())"

# restart worker
docker compose restart worker
```

### Google Drive Upload Failing

```bash
# check credentials exist
docker compose exec backend ls -la /opt/trickyclip/secrets/

# test drive connection
docker compose exec backend python -c "from app.services.drive import drive_service; print('Connected' if drive_service.service else 'Not connected')"
```

### Out of Disk Space

```bash
# check disk usage
df -h

# clean up docker
docker system prune -a --volumes

# check data directories
du -sh /opt/trickyclip/data/*

# remove old logs
docker compose logs --tail=0
```

## Backup & Recovery

### Backup Database

```bash
# on VM
docker compose exec db pg_dump -U postgres trickyclip > backup_$(date +%Y%m%d).sql
```

### Restore Database

```bash
# on VM
docker compose exec -T db psql -U postgres trickyclip < backup_20251202.sql
```

### Backup Entire System

```bash
# create snapshot of VM disk in Google Cloud Console
# or use gcloud command
gcloud compute disks snapshot trickyclip-server --zone=us-central1-c
```

## Performance Tuning

### Scale Workers

Edit `/opt/trickyclip/deploy/docker-compose.yml`:

```yaml
worker:
  deploy:
    replicas: 3  # run 3 worker instances
```

### Increase Resources

```bash
# stop VM
gcloud compute instances stop trickyclip-server --zone=us-central1-c

# change machine type
gcloud compute instances set-machine-type trickyclip-server --machine-type=e2-standard-8 --zone=us-central1-c

# start VM
gcloud compute instances start trickyclip-server --zone=us-central1-c
```

## Security

### Update Secrets

```bash
# on your local machine
gcloud compute scp /path/to/new-credentials.json kahuna@trickyclip-server:/opt/trickyclip/secrets/ --zone=us-central1-c

# restart services
gcloud compute ssh kahuna@trickyclip-server --zone=us-central1-c --command="cd /opt/trickyclip/deploy && docker compose restart backend worker"
```

### Rotate Database Password

1. Update password in Google Cloud SQL or local postgres
2. Update `.env` file on VM
3. Restart all services

## Cost Management

### Monitor Costs

```bash
# view current month costs
gcloud billing accounts list
```

### Reduce Costs

- Use preemptible VMs for workers
- Stop VM during low-usage hours
- Clean up old processed files
- Use Cloud Storage instead of VM disk for large files

### Auto-Shutdown Schedule

Create cron job on VM:

```bash
# shutdown at midnight, start at 8am
0 0 * * * /sbin/shutdown -h now
0 8 * * * gcloud compute instances start trickyclip-server --zone=us-central1-c
```

## Support

- Check logs first: `docker compose logs`
- Review this guide
- Check GitHub issues
- Contact maintainer


