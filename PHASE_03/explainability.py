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

    def generate_clinical_narrative(img_array, shap_values, predicted_class, confidence):

    # -------------------------------------------------------------------------
    # 1. Process Base Image
    # -------------------------------------------------------------------------
    img_squeezed = np.squeeze(img_array)
    if img_squeezed.max() <= 1.0:
        img_uint8 = np.uint8(255 * img_squeezed)
    else:
        img_uint8 = np.uint8(img_squeezed)

    # Extract the raw 2D SHAP array
    if hasattr(shap_values, "values"):
        shap_val = shap_values.values[0, ..., 0]
    else:
        shap_val = shap_values[0]

    if len(shap_val.shape) == 3:
        if shap_val.shape[-1] == 3:
            shap_val = np.sum(shap_val, axis=-1)
        elif shap_val.shape[-1] == 1:
            shap_val = np.squeeze(shap_val, axis=-1)

    # -------------------------------------------------------------------------
    # 2. Define the Clinical Zones
    # -------------------------------------------------------------------------
    ink_mask = img_uint8 < 200
    row_has_ink = np.any(ink_mask, axis=1)
    col_has_ink = np.any(ink_mask, axis=0)

    if not np.any(row_has_ink):
        return "System Warning: Unable to detect sufficient handwriting for spatial analysis."

    min_y = np.argmax(row_has_ink)
    max_y = len(row_has_ink) - np.argmax(row_has_ink[::-1])
    min_x = np.argmax(col_has_ink)
    max_x = len(col_has_ink) - np.argmax(col_has_ink[::-1])

    # Zone 1: Morphology — pixels directly on ink strokes.
    # Corresponds to Motor Dysgraphia: deficits in graphomotor execution
    # and fine-motor coordination (Deuel, 1995).
    zone1_morphology = ink_mask.copy()

    # Zone 2: Kerning — whitespace INSIDE the writing bounding box.
    # Corresponds to inter-character spacing deficits in Spatial Dysgraphia
    # (Deuel, 1995; Chung et al., 2020).
    zone2_kerning = np.zeros_like(ink_mask, dtype=bool)
    zone2_kerning[min_y:max_y, min_x:max_x] = ~ink_mask[min_y:max_y, min_x:max_x]

    # Zone 3: Spatial Planning — whitespace OUTSIDE the vertical bounding box.
    # Corresponds to macro-spatial planning failure and margin non-adherence,
    # assessed in standardized OT instruments such as the Beery VMI
    # (Beery & Beery, 2010).
    zone3_spatial = np.ones_like(ink_mask, dtype=bool)
    zone3_spatial[min_y:max_y, :] = False

    # -------------------------------------------------------------------------
    # 3. Calculate Impact Scores
    # Only positive SHAP values are used — pixels that support the prediction.
    # -------------------------------------------------------------------------
    supportive_shap = np.maximum(shap_val, 0)

    score_z1 = np.sum(supportive_shap[zone1_morphology])
    score_z2 = np.sum(supportive_shap[zone2_kerning])
    score_z3 = np.sum(supportive_shap[zone3_spatial])

    total_score = score_z1 + score_z2 + score_z3
    if total_score == 0:
        total_score = 1e-9

    pct_z1 = score_z1 / total_score
    pct_z2 = score_z2 / total_score
    pct_z3 = score_z3 / total_score

    # -------------------------------------------------------------------------
    # 4. Generate the Deterministic Academic Narrative
    # -------------------------------------------------------------------------
    narrative = "▶ AIKONIC CLINICAL DIAGNOSTIC REPORT\n"
    narrative += (
        f"Classification: {predicted_class} ({confidence:.1f}% System Confidence)\n"
    )
    narrative += "-" * 60 + "\n"

    if predicted_class == "PD":  # Possible Dysgraphia
        narrative += "EVIDENCE-BASED FINDINGS:\n"

        if pct_z3 > max(pct_z1, pct_z2):
            # Zone 3 dominant: macro-spatial planning failure
            narrative += (
                "The highest predictive anomalies are located in the upper or lower boundary margins "
                "of the handwriting sample. According to Deuel (1995), this pattern is characteristic "
                "of Spatial Dysgraphia, a subtype defined by impaired understanding of space that results "
                "in an inability to adhere to baselines and respect page margins regardless of letter-formation "
                "ability. This constitutes impaired macro-spatial planning, a primary indicator of the "
                "visual-spatial deficits associated with Specific Learning Disorder in written expression "
                "(American Psychiatric Association [APA], 2013). The Beery-Buktenica Developmental Test of "
                "Visual-Motor Integration (Beery VMI) — one of the most widely used standardized occupational "
                "therapy instruments — explicitly assesses a patient's ability to stay within designated "
                "spatial boundaries; the anomalies flagged in this zone represent the automated equivalent "
                "of that assessment criterion (Beery & Beery, 2010)."
            )

        elif pct_z2 > max(pct_z1, pct_z3):
            # Zone 2 dominant: inter-character spacing / kerning deficit
            narrative += (
                "The predictive anomalies are heavily localized in the whitespace between characters. "
                "Deuel (1995) defines Spatial Dysgraphia as producing illegible writing — whether spontaneous "
                "or copied — due to a fundamental deficit in spatial perception, which manifests directly as "
                "abnormal letter spacing and erratic kerning. Chung et al. (2020) further specify that in "
                "spatial dysgraphia, oral spelling and fine-motor tapping speed are preserved, indicating "
                "that the spacing irregularities detected in this zone are perceptual-spatial in origin rather "
                "than purely motoric. These atypical inter-character intervals are a strong behavioral marker "
                "of impaired graphomotor coordination, consistent with Specific Learning Disorder criteria "
                "(APA, 2013). Döhla and Heim (2016) additionally note that dysgraphia and dyslexia share "
                "spatial-processing deficits that manifest during the physical execution of written output."
            )

        else:
            # Zone 1 dominant: letter morphology / fine motor deficit
            narrative += (
                "The predictive anomalies are concentrated directly on the ink strokes themselves. "
                "Deuel (1995) classifies this presentation as Motor Dysgraphia, a subtype in which both "
                "spontaneous writing and copying are impaired due to deficient fine-motor coordination and "
                "graphomotor execution — distinguishable from other subtypes by abnormal finger-tapping speed "
                "and drawing performance. This is consistent with DSM-5 criteria for Specific Learning "
                "Disorder with impairment in written expression, which includes difficulties with the clarity "
                "and physical organization of written output (APA, 2013). Chung et al. (2020) describe this "
                "subtype as reflecting an inefficiency in the graphomotor loop, wherein motor memory fails to "
                "produce consistent letter formation. Döhla and Heim (2016) further associate motor dysgraphia "
                "with deficits in the automatization of fine-motor writing sequences, resulting in erratic pen "
                "pressure and inconsistent letterform."
            )

    else:  # Likely Probable with Dysgraphia (LPD) — within healthy limits
        narrative += (
            "EVIDENCE-BASED FINDINGS:\n"
            "Analysis indicates that graphomotor execution falls within healthy neurodevelopmental limits, "
            "with no dominant zone of anomalous SHAP attribution corresponding to known dysgraphia subtypes "
            "(Deuel, 1995; APA, 2013). "
        )

        if pct_z1 > 0.5:
            narrative += (
                "SHAP attributions are primarily distributed across the ink strokes (Zone 1), with letter "
                "morphology, line stability, and fine-motor execution consistent with standard age-appropriate "
                "motor development, as defined by Motor Dysgraphia absence criteria (Deuel, 1995)."
            )
        elif pct_z3 > 0.5:
            narrative += (
                "SHAP attributions are primarily distributed in the margin regions (Zone 3). Proper utilization "
                "of margins and baseline adherence indicate healthy visual-spatial planning and cognitive "
                "organization, consistent with passing performance on spatial boundary tasks assessed by the "
                "Beery VMI (Beery & Beery, 2010)."
            )
        else:
            narrative += (
                "Macro-spatial planning (Zone 3), intra-word kerning (Zone 2), and letter morphology (Zone 1) "
                "all appear balanced and within normal developmental thresholds for written expression, "
                "consistent with the absence of Spatial or Motor Dysgraphia indicators described by "
                "Deuel (1995) and Mather and Wendling (2011)."
            )

    # Append standard reference footer
    narrative += (
        "\n\n" + "-" * 60 + "\n"
        "REFERENCES\n"
        "American Psychiatric Association. (2013). Diagnostic and Statistical Manual of Mental\n"
        "  Disorders (5th ed.). https://doi.org/10.1176/appi.books.9780890425596\n\n"
        "Beery, K. E., & Beery, N. A. (2010). The Beery-Buktenica Developmental Test of\n"
        "  Visual-Motor Integration (6th ed.). NCS Pearson.\n\n"
        "Chung, P. J., Patel, D. R., & Nizami, I. (2020). Disorder of written expression and\n"
        "  dysgraphia: Definition, diagnosis, and management. Translational Pediatrics,\n"
        "  9(Suppl 1), S46-S54. https://doi.org/10.21037/tp.2019.11.01\n\n"
        "Deuel, R. K. (1995). Developmental dysgraphia and motor skills disorders. Journal of\n"
        "  Child Neurology, 10(Suppl 1), S6-S8. https://doi.org/10.1177/08830738950100S103\n\n"
        "Döhla, D., & Heim, S. (2016). Developmental dyslexia and dysgraphia: What can we\n"
        "  learn from the one about the other? Frontiers in Psychology, 6, 2045.\n"
        "  https://doi.org/10.3389/fpsyg.2015.02045\n\n"
        "Mather, N., & Wendling, B. J. (2011). Essentials of dyslexia assessment and\n"
        "  intervention. John Wiley & Sons.\n"
    )

    return narrative
