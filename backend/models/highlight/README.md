# Highlight Detection Models

## Directory Structure

```
models/highlight/
├── model_manifest.json          ← Points to current active model
├── highlight_movinet_a0_v001.tflite
├── highlight_movinet_a0_v002.tflite
└── README.md
```

## Deploying a New Model

### 1. Train Model Locally

See `ml_training/highlight_model/README.md` for training instructions.

### 2. Upload to VM

```bash
gcloud compute scp \
  ./highlight_movinet_a0_v001.tflite \
  kahuna@trickyclip-server:/opt/trickyclip/backend/models/highlight/ \
  --zone=us-central1-c
```

### 3. Update Manifest

```bash
gcloud compute ssh kahuna@trickyclip-server --zone=us-central1-c

cd /opt/trickyclip/backend/models/highlight
nano model_manifest.json
```

Update to:
```json
{
  "current": "highlight_movinet_a0_v001.tflite",
  "models": [
    {
      "name": "highlight_movinet_a0_v001.tflite",
      "created": "2025-01-08T10:00:00Z",
      "metrics": {
        "precision": 0.85,
        "recall": 0.78,
        "accuracy": 0.82
      }
    }
  ]
}
```

### 4. Enable Stage 2 Detection

```bash
nano /opt/trickyclip/backend/.env

# Add or update:
DETECTION_USE_ML_STAGE2=true
```

### 5. Restart Workers

```bash
cd /opt/trickyclip/deploy
docker compose restart worker
```

## Model Versioning

- Use semantic versioning: `v001`, `v002`, etc.
- Keep old models for rollback
- Track metrics in manifest
- Test new models in shadow mode first

## Rollback

If a model performs poorly:

1. Update manifest to point to previous version
2. Restart workers
3. No code changes needed!


