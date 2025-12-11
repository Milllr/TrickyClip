#!/usr/bin/env python3
"""
train movinet-a0 model for highlight detection

usage:
    python train_movinet.py --dataset ./dataset --output ./models/highlight_movinet_a0_v001.tflite
"""

import argparse
import tensorflow as tf
import tensorflow_hub as hub
from pathlib import Path
import json
from dataset_loader import HighlightDataset


def build_model(num_frames: int = 16, frame_size: int = 172) -> tf.keras.Model:
    """
    build movinet-a0 based highlight classifier
    
    uses pretrained movinet from tensorflow hub
    adds binary classification head
    """
    
    # load pretrained movinet-a0 from tf hub
    # note: this downloads the model on first run
    movinet_url = "https://tfhub.dev/tensorflow/movinet/a0/base/kinetics-600/classification/3"
    
    # input: [batch, num_frames, height, width, 3]
    inputs = tf.keras.layers.Input(
        shape=(num_frames, frame_size, frame_size, 3),
        dtype=tf.float32,
        name='video_input'
    )
    
    # load movinet backbone
    movinet_model = hub.KerasLayer(movinet_url, trainable=True)
    
    # get features
    features = movinet_model(inputs)
    
    # classification head
    x = tf.keras.layers.Dense(128, activation='relu')(features)
    x = tf.keras.layers.Dropout(0.3)(x)
    x = tf.keras.layers.Dense(64, activation='relu')(x)
    x = tf.keras.layers.Dropout(0.2)(x)
    outputs = tf.keras.layers.Dense(1, activation='sigmoid', name='trick_probability')(x)
    
    model = tf.keras.Model(inputs=inputs, outputs=outputs)
    
    return model


def train_model(
    dataset_dir: Path,
    output_path: Path,
    epochs: int = 20,
    learning_rate: float = 0.001
):
    """train highlight detection model"""
    
    print("loading dataset...")
    dataset = HighlightDataset(dataset_dir, num_frames=16, frame_size=172, batch_size=8)
    
    train_ds = dataset.create_tf_dataset('train')
    val_ds = dataset.create_tf_dataset('val')
    
    print("building model...")
    model = build_model(num_frames=16, frame_size=172)
    
    # compile
    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss='binary_crossentropy',
        metrics=[
            'accuracy',
            tf.keras.metrics.Precision(name='precision'),
            tf.keras.metrics.Recall(name='recall'),
            tf.keras.metrics.AUC(name='auc')
        ]
    )
    
    print(model.summary())
    
    # callbacks
    callbacks = [
        tf.keras.callbacks.EarlyStopping(
            monitor='val_loss',
            patience=5,
            restore_best_weights=True
        ),
        tf.keras.callbacks.ReduceLROnPlateau(
            monitor='val_loss',
            factor=0.5,
            patience=3
        )
    ]
    
    # train
    print(f"training for {epochs} epochs...")
    history = model.fit(
        train_ds,
        validation_data=val_ds,
        epochs=epochs,
        callbacks=callbacks
    )
    
    # evaluate
    print("\nevaluating on validation set...")
    val_metrics = model.evaluate(val_ds)
    print(f"validation metrics: {dict(zip(model.metrics_names, val_metrics))}")
    
    # save keras model first
    keras_path = output_path.parent / (output_path.stem + ".keras")
    model.save(keras_path)
    print(f"saved keras model: {keras_path}")
    
    # convert to tflite
    print("converting to tflite...")
    converter = tf.lite.TFLiteConverter.from_keras_model(model)
    
    # enable optimizations
    converter.optimizations = [tf.lite.Optimize.DEFAULT]
    
    tflite_model = converter.convert()
    
    # save tflite model
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'wb') as f:
        f.write(tflite_model)
    
    print(f"✅ saved tflite model: {output_path}")
    
    # save training metadata
    metadata = {
        "model_name": output_path.name,
        "created": str(tf.timestamp()),
        "num_frames": 16,
        "frame_size": 172,
        "epochs_trained": len(history.history['loss']),
        "final_metrics": {
            "val_loss": float(history.history['val_loss'][-1]),
            "val_accuracy": float(history.history['val_accuracy'][-1]),
            "val_precision": float(history.history['val_precision'][-1]),
            "val_recall": float(history.history['val_recall'][-1]),
        }
    }
    
    metadata_path = output_path.parent / (output_path.stem + "_metadata.json")
    with open(metadata_path, 'w') as f:
        json.dump(metadata, f, indent=2)
    
    print(f"saved metadata: {metadata_path}")
    
    return model, history


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="train movinet highlight model")
    parser.add_argument("--dataset", type=str, required=True, help="dataset directory")
    parser.add_argument("--output", type=str, required=True, help="output tflite model path")
    parser.add_argument("--epochs", type=int, default=20, help="number of epochs")
    parser.add_argument("--lr", type=float, default=0.001, help="learning rate")
    
    args = parser.parse_args()
    
    train_model(
        Path(args.dataset),
        Path(args.output),
        epochs=args.epochs,
        learning_rate=args.lr
    )


