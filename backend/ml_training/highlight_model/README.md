# Highlight Model Training

## Overview

Train a MoViNet-A0 based model to classify video clips as "trick" vs "non-trick".

## Setup

```bash
# install training dependencies
pip install -r requirements.txt
```

## Training Workflow

### 1. Export Dataset from Production DB

```bash
# SSH to VM and export data
gcloud compute ssh kahuna@trickyclip-server --zone=us-central1-c

cd /opt/trickyclip/backend
python -m ml_training.export_highlight_dataset --output /tmp/highlight_dataset

# download dataset to local machine
gcloud compute scp --recurse \
  kahuna@trickyclip-server:/tmp/highlight_dataset \
  ./ml_training/highlight_model/dataset/ \
  --zone=us-central1-c
```

### 2. Train Model Locally

```bash
cd backend/ml_training/highlight_model

python train_movinet.py \
  --dataset ./dataset \
  --output ./models/highlight_movinet_a0_v001.tflite \
  --epochs 20 \
  --lr 0.001
```

This will:
- Load positive/negative clips
- Train MoViNet-A0 with transfer learning
- Export to TFLite with optimizations
- Save training metrics

### 3. Deploy Model to VM

```bash
# upload tflite model
gcloud compute scp \
  ./models/highlight_movinet_a0_v001.tflite \
  kahuna@trickyclip-server:/opt/trickyclip/backend/models/highlight/ \
  --zone=us-central1-c

# update manifest
gcloud compute ssh kahuna@trickyclip-server --zone=us-central1-c

cd /opt/trickyclip/backend/models/highlight
cat > model_manifest.json << 'EOF'
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
EOF
```

### 4. Enable Stage 2 Detection

```bash
# update .env on VM
nano /opt/trickyclip/backend/.env

# add:
DETECTION_USE_ML_STAGE2=true

# restart workers
docker compose restart worker
```

## Model Architecture

- **Base:** MoViNet-A0 (pretrained on Kinetics-600)
- **Input:** 16 frames @ 172×172 RGB
- **Head:** Dense(128) → Dropout(0.3) → Dense(64) → Dropout(0.2) → Dense(1, sigmoid)
- **Output:** Single probability score [0, 1]

## Training Strategy

1. **Transfer Learning:** Start with pretrained weights
2. **Freeze Backbone:** Train only classification head initially
3. **Fine-tune:** Unfreeze last few layers for domain adaptation
4. **Early Stopping:** Monitor validation loss
5. **Quantization:** Convert to TFLite with DEFAULT optimizations

## Expected Performance

- **Precision:** 70-85% (of shown segments are tricks)
- **Recall:** 75-90% (of actual tricks are detected)
- **Inference Time:** <100ms per clip on CPU
- **Model Size:** ~5-10 MB (TFLite)

## Iteration

After deploying and collecting more data:

1. Export new dataset (more positive/negative samples)
2. Retrain with updated data
3. Increment version (v002, v003, etc.)
4. Deploy and compare metrics
5. Keep best performing model in manifest


