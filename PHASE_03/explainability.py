"""
AIKONIC — explainability.py
===========================
Phase 3 Engine for generating Grad-CAM heatmaps, SHAP value arrays,
and compiling them into a 1x4 diagnostic clinical graphic.
"""

import os
import numpy as np
import tensorflow as tf
import matplotlib.pyplot as plt
import cv2
import shap
import config


def make_gradcam_heatmap(img_array, model, last_conv_layer_name=None, pred_index=None):
    """
    Calculates the Grad-CAM heatmap by manually chaining the layers,
    bypassing the Keras 3 nested model graph bug entirely.
    """
    if len(img_array.shape) == 3:
        img_array = np.expand_dims(img_array, axis=0)

    img_tensor = tf.convert_to_tensor(img_array, dtype=tf.float32)

    # 1. Manually replicate the 1-channel image to 3 channels
    x = tf.concat([img_tensor, img_tensor, img_tensor], axis=-1)

    # 2. Extract your exact layers by name
    base_model = model.get_layer("MobileNetV3Small")
    pool_layer = model.get_layer("global_avg_pool")
    bn_layer = model.get_layer("batch_norm")
    dense_layer = model.get_layer("dense_128")
    dropout_layer = model.get_layer("dropout")
    classifier = model.get_layer("classifier")

    with tf.GradientTape() as tape:
        # 3. Get the 3D spatial feature map from the base model
        last_conv_layer_output = base_model(x, training=False)

        # Tell TensorFlow to manually WATCH this specific step for gradients
        tape.watch(last_conv_layer_output)

        # 4. Push the feature map through the rest of the classification head
        x_head = pool_layer(last_conv_layer_output)
        x_head = bn_layer(x_head, training=False)
        x_head = dense_layer(x_head)
        x_head = dropout_layer(x_head, training=False)
        preds = classifier(x_head)

        if pred_index is None:
            pred_index = tf.argmax(preds[0])
        class_channel = preds[:, pred_index]

    # 5. Calculate Gradients
    grads = tape.gradient(class_channel, last_conv_layer_output)
    pooled_grads = tf.reduce_mean(grads, axis=(0, 1, 2))

    # 6. Apply weights to the feature map
    last_conv_layer_output = last_conv_layer_output[0]
    heatmap = last_conv_layer_output @ pooled_grads[..., tf.newaxis]
    heatmap = tf.squeeze(heatmap)

    # 7. Apply ReLU and normalize
    heatmap = tf.maximum(heatmap, 0) / tf.math.reduce_max(heatmap)

    return heatmap.numpy()


def generate_shap_values(model, test_image):
    """
    Calculates pixel attributions using SHAP's PartitionExplainer,
    which safely bypasses complex gradient math (like hard_swish).
    """
    # 1. Ensure batch dimension exists
    if len(test_image.shape) == 3:
        test_image = np.expand_dims(test_image, axis=0)

    # 2. Define the Masker (blurs out parts of the image to see how prediction changes)
    masker = shap.maskers.Image("inpaint_telea", test_image[0].shape)

    # 3. Create the Explainer wrapping the model's PREDICT function, NOT the graph
    explainer = shap.Explainer(model.predict, masker, output_names=config.CLASS_NAMES)

    # 4. Calculate SHAP values (max_evals=500 is a good balance of speed/detail)
    print("Calculating SHAP values (this may take a moment)...")
    shap_values = explainer(
        test_image, max_evals=500, outputs=shap.Explanation.argsort.flip[:1]
    )

    return shap_values
