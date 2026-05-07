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


def plot_4_panel_diagnostic(
    img_array, heatmap, shap_values, save_name="diagnostic_panel.png"
):
    """
    Renders the Original Image, Grad-CAM, SHAP, and Severe Focus.
    All overlays are strictly cropped to a bubble around the actual handwriting.
    """
    os.makedirs(config.EXPLAINABILITY_DIR, exist_ok=True)

    # 1. Process Base Image
    img_squeezed = np.squeeze(img_array)
    if img_squeezed.max() <= 1.0:
        img_uint8 = np.uint8(255 * img_squeezed)
    else:
        img_uint8 = np.uint8(img_squeezed)

    img_rgb = (
        cv2.cvtColor(img_uint8, cv2.COLORMAP_BONE)
        if len(img_uint8.shape) == 2
        else img_uint8
    )

    # ─── MASTER BUBBLE MASK (Calculated once for all panels) ──────────────
    ink_mask_uint8 = np.uint8((img_uint8 < 200) * 255)
    kernel = cv2.getStructuringElement(cv2.MORPH_ELLIPSE, (40, 40))
    dilated_mask = cv2.dilate(ink_mask_uint8, kernel)

    # Mask sized for the 224x224 image
    spatial_mask_224 = (
        cv2.resize(dilated_mask, (img_uint8.shape[1], img_uint8.shape[0])) > 0
    )

    # 2. Process Grad-CAM Overlay
    heatmap_resized = cv2.resize(heatmap, (img_uint8.shape[1], img_uint8.shape[0]))
    heatmap_uint8 = np.uint8(255 * heatmap_resized)
    heatmap_color = cv2.applyColorMap(heatmap_uint8, cv2.COLORMAP_JET)

    raw_gradcam_overlay = cv2.addWeighted(img_rgb, 0.5, heatmap_color, 0.5, 0)

    # NEW: Only show the Grad-CAM color inside the bubble; otherwise, show plain grayscale paper
    gradcam_overlay = np.where(
        spatial_mask_224[..., None], raw_gradcam_overlay, img_rgb
    )

    # 3. Process SHAP
    if hasattr(shap_values, "values"):
        shap_val = shap_values.values[0, ..., 0]
    else:
        shap_val = shap_values[0]

    if len(shap_val.shape) == 3:
        if shap_val.shape[-1] == 3:
            shap_val = np.sum(shap_val, axis=-1)
        elif shap_val.shape[-1] == 1:
            shap_val = np.squeeze(shap_val, axis=-1)

    # Mask sized specifically for the SHAP grid
    spatial_mask_shap = (
        cv2.resize(dilated_mask, (shap_val.shape[1], shap_val.shape[0])) > 0
    )

    abs_shap = np.abs(shap_val)
    signal_threshold = np.percentile(abs_shap, 65)
    signal_mask = abs_shap >= signal_threshold

    final_shap_mask = spatial_mask_shap & signal_mask
    masked_shap = np.ma.masked_where(~final_shap_mask, shap_val)

    # 4. Create Panel 4: Severe Anomaly Focus
    threshold = np.percentile(heatmap_resized, 70)
    focus_mask = heatmap_resized > threshold
    focus_heatmap = np.zeros_like(heatmap_color)
    focus_heatmap[focus_mask] = heatmap_color[focus_mask]

    raw_focus_overlay = cv2.addWeighted(img_rgb, 0.7, focus_heatmap, 0.5, 0)

    # NEW: Apply the same bubble crop to the severe focus view
    focus_overlay = np.where(spatial_mask_224[..., None], raw_focus_overlay, img_rgb)

    # Fix the BGR to RGB color flip for Matplotlib
    gradcam_overlay = cv2.cvtColor(gradcam_overlay, cv2.COLOR_BGR2RGB)
    focus_overlay = cv2.cvtColor(focus_overlay, cv2.COLOR_BGR2RGB)

    # ─── Plotting the 1x4 Grid ─────────────────────────────────────────
    fig, axes = plt.subplots(1, 4, figsize=(20, 5))
    fig.suptitle(
        "AIKONIC Dysgraphia Diagnostic Analysis", fontsize=16, fontweight="bold", y=1.05
    )

    axes[0].imshow(img_uint8, cmap="gray")
    axes[0].set_title("1. Original Patient Patch", fontsize=12)
    axes[0].axis("off")

    axes[1].imshow(gradcam_overlay)
    axes[1].set_title("2. Grad-CAM Localization", fontsize=12)
    axes[1].axis("off")

    axes[2].imshow(img_uint8, cmap="gray")
    vmax = np.max(np.abs(shap_val))
    axes[2].imshow(masked_shap, cmap="coolwarm", alpha=0.75, vmin=-vmax, vmax=vmax)
    axes[2].set_title("3. SHAP Feature Attribution", fontsize=12)
    axes[2].axis("off")

    axes[3].imshow(focus_overlay)
    axes[3].set_title("4. Severe Anomaly Focus", fontsize=12)
    axes[3].axis("off")

    plt.tight_layout()
    save_path = os.path.join(config.EXPLAINABILITY_DIR, save_name)
    plt.savefig(save_path, dpi=300, bbox_inches="tight")
    plt.show()
    print(f"✓ Diagnostic graphic saved to {save_path}")
