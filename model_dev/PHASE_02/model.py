"""
AIKONIC — model.py
==================
Single source of truth for DysgraphiaCNN architecture.
Both the training notebook and CV loop import from here.
Never redefine build_model() elsewhere.
"""

import tensorflow as tf
from tensorflow.keras import layers, Model
from tensorflow.keras.applications import MobileNetV3Small
import io, os, sys

sys.path.insert(0, os.path.join(os.path.dirname(__file__)))
import config


def build_model(
    freeze_base: bool = True,
    dropout_rate: float = config.DROPOUT_RATE,
    learning_rate: float = config.PHASE_A_LR,
) -> tf.keras.Model:
    """
    DysgraphiaCNN: MobileNetV3-Small binary classifier for dysgraphia screening.

    Architecture
    ------------
    Input (224, 224, 1) grayscale
        → Concatenate  [channel replication: 1-ch → 3-ch]
        → MobileNetV3-Small (ImageNet pretrained, freeze_base controls trainability)
        → GlobalAveragePooling2D
        → BatchNormalization
        → Dense(128, hard_swish)
        → Dropout(0.4)
        → Dense(2, softmax)   →  [P(LPD), P(PD)]

    Parameters
    ----------
    freeze_base    : if True, MobileNetV3-Small weights are frozen (Phase A)
    dropout_rate   : dropout probability on the dense head
    learning_rate  : Adam optimizer learning rate

    Notes
    -----
    - Concatenate is used instead of Lambda for channel replication.
      Lambda layers fail to deserialize from .keras/.h5 in TF ≥ 2.11.
    - Input is (224, 224, 1) grayscale. The Concatenate layer bridges to
      the 3-channel ImageNet pretrained weights without discarding
      grayscale preprocessing.
    """
    inputs = tf.keras.Input(shape=(224, 224, 1), name="grayscale_input")

    # 1-channel → 3-channel replication (Keras-safe, no Lambda)
    x = layers.Concatenate(axis=-1, name="channel_replication")(
        [inputs, inputs, inputs]
    )

    # MobileNetV3-Small pretrained backbone
    base = MobileNetV3Small(
        weights="imagenet",
        include_top=False,
        input_shape=(224, 224, 3),
    )
    base.trainable = not freeze_base
    x = base(x, training=not freeze_base)

    # Classification head
    x = layers.GlobalAveragePooling2D(name="global_avg_pool")(x)
    x = layers.BatchNormalization(name="batch_norm")(x)
    x = layers.Dense(
        config.DENSE_UNITS,
        activation=config.ACTIVATION,
        name="dense_128",
    )(x)
    x = layers.Dropout(dropout_rate, name="dropout")(x)
    outputs = layers.Dense(
        config.NUM_CLASSES,
        activation="softmax",
        name="classifier",
    )(x)

    model = Model(inputs=inputs, outputs=outputs, name="DysgraphiaCNN")

    model.compile(
        optimizer=tf.keras.optimizers.Adam(learning_rate=learning_rate),
        loss="categorical_crossentropy",
        metrics=[
            tf.keras.metrics.CategoricalAccuracy(name="accuracy"),
            tf.keras.metrics.AUC(name="auc"),
            tf.keras.metrics.Precision(name="precision"),
            tf.keras.metrics.Recall(name="recall"),
        ],
    )
    return model


def partial_unfreeze(
    model: tf.keras.Model,
    unfreeze_fraction: float = config.PHASE_B_UNFREEZE_FRACTION,
) -> tf.keras.Model:
    """
    Unfreeze the top `unfreeze_fraction` of MobileNetV3-Small layers for Phase B.

    Rationale
    ---------
    Full unfreeze risks destructive updates to early ImageNet features
    (edges, textures) that are still useful for handwriting analysis.
    Partial unfreeze exposes only the high-level semantic layers to
    domain adaptation while preserving foundational representations.

    Strategy: top 20% of base layers (≈ last 2–3 MobileNetV3 blocks)
    are unfrozen. All earlier layers remain frozen.

    Parameters
    ----------
    model             : the model returned by build_model()
    unfreeze_fraction : fraction of base layers to unfreeze from the top

    Returns
    -------
    model with selected layers unfrozen (recompilation is the caller's
    responsibility — see the training notebook).
    """
    # Isolate the MobileNetV3Small sub-model
    base = None
    for layer in model.layers:
        if isinstance(layer, tf.keras.Model) and "mobilenet" in layer.name.lower():
            base = layer
            break

    if base is None:
        raise RuntimeError(
            "Could not locate MobileNetV3Small sub-model inside DysgraphiaCNN. "
            "Check that build_model() was used to construct the model."
        )

    n_layers        = len(base.layers)
    n_to_unfreeze   = max(1, int(n_layers * unfreeze_fraction))
    freeze_boundary = n_layers - n_to_unfreeze

    for i, layer in enumerate(base.layers):
        layer.trainable = i >= freeze_boundary

    unfrozen = sum(1 for l in base.layers if l.trainable)
    frozen   = n_layers - unfrozen

    print(f"[partial_unfreeze] Base model: {n_layers} layers total")
    print(f"[partial_unfreeze] Frozen  : {frozen} layers (early feature extractors preserved)")
    print(f"[partial_unfreeze] Unfrozen: {unfrozen} layers (top {unfreeze_fraction:.0%} — domain adaptation)")

    return model


def save_architecture_summary(model: tf.keras.Model) -> None:
    """Write model.summary() output to config.ARCH_SUMMARY."""
    import os
    os.makedirs(config.REPORTS_DIR, exist_ok=True)
    stream = io.StringIO()
    model.summary(print_fn=lambda line: stream.write(line + "\n"))
    with open(config.ARCH_SUMMARY, "w") as f:
        f.write(stream.getvalue())
    print(f"Architecture summary saved → {config.ARCH_SUMMARY}")


if __name__ == "__main__":
    print("Building DysgraphiaCNN (Phase A — frozen base)...")
    m = build_model(freeze_base=True)
    m.summary()

    total     = m.count_params()
    trainable = int(sum(tf.size(w).numpy() for w in m.trainable_weights))
    frozen    = int(sum(tf.size(w).numpy() for w in m.non_trainable_weights))
    print(f"\nTotal      : {total:>10,}")
    print(f"Trainable  : {trainable:>10,}")
    print(f"Frozen     : {frozen:>10,}")

    dummy = tf.zeros((1, 224, 224, 1))
    out   = m(dummy, training=False)
    assert out.shape == (1, 2)
    print(f"\n✓ Output shape: {out.shape}")
