"""
app2.py — Détection de polypes : images ET vidéos
===================================================

Extension de app.py pour l'équipe médicale :
- Images : même pipeline qu'avant (YOLO étage 1 → EfficientNet étage 2)
- Vidéos  : analyse frame par frame, affichage de la timeline,
            des secondes et frames exactes de chaque détection,
            et de la frame clé avec la boîte dessinée.

Pour lancer :
    pip install -r requirements.txt
    streamlit run app2.py
"""

import io
import os
import random
import time
import tempfile

import cv2
import matplotlib.patches as patches
import matplotlib.pyplot as plt
import numpy as np
import streamlit as st
from PIL import Image

# -------------------------------------------------------------------
# Configuration
# -------------------------------------------------------------------

YOLO_WEIGHTS_PATH   = "weights/best.pt"
EFFICIENTNET_PATH   = "weights/efficientnet_etage2.pt"
CLASS_NAMES         = ["mauvaise_preparation", "mici", "normal", "polype"]
YOLO_CONF           = 0.25
FRAME_SKIP          = 5       # 1 frame analysée sur N
MIN_SEGMENT_DURATION = 0.5   # secondes

st.set_page_config(
    page_title="medet — Détection d'anomalies digestives",
    page_icon="🩺",
    layout="wide",
)

# -------------------------------------------------------------------
# Chargement des modèles (mis en cache)
# -------------------------------------------------------------------

@st.cache_resource(show_spinner=False)
def load_models():
    yolo_model = None
    eff_model  = None

    try:
        from ultralytics import YOLO
        if os.path.exists(YOLO_WEIGHTS_PATH):
            yolo_model = YOLO(YOLO_WEIGHTS_PATH)
    except Exception:
        pass

    try:
        import torch
        import torch.nn as nn
        from torchvision import models, transforms

        if os.path.exists(EFFICIENTNET_PATH):
            eff = models.efficientnet_b0(weights=None)
            eff.classifier[1] = nn.Linear(
                eff.classifier[1].in_features, len(CLASS_NAMES)
            )
            import torch
            eff.load_state_dict(torch.load(EFFICIENTNET_PATH, map_location="cpu"))
            eff.eval()
            eff_model = eff
    except Exception:
        pass

    return yolo_model, eff_model

yolo_model, eff_model = load_models()
DEMO_MODE = (yolo_model is None) or (eff_model is None)

# -------------------------------------------------------------------
# Fonctions de prédiction
# -------------------------------------------------------------------

def predict_stage1_image(image: Image.Image):
    """Étage 1 sur une image PIL. Retourne (detected, n_boxes)."""
    if DEMO_MODE:
        time.sleep(0.4)
        detected = random.random() < 0.55
        return detected, (1 if detected else 0)

    image.save("_tmp.jpg")
    result = yolo_model.predict("_tmp.jpg", conf=YOLO_CONF, verbose=False)[0]
    return len(result.boxes) > 0, len(result.boxes)


def predict_stage2_image(image: Image.Image):
    """Étage 2 sur une image PIL. Retourne (classe, confiance)."""
    if DEMO_MODE:
        time.sleep(0.6)
        cls = random.choice(["polype", "mici", "mauvaise_preparation"])
        return cls, random.uniform(0.75, 0.98)

    import torch
    from torchvision import transforms
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
    ])
    tensor = transform(image.convert("RGB")).unsqueeze(0)
    with torch.no_grad():
        out = eff_model(tensor)
        probs = torch.softmax(out, dim=1)
        conf, idx = torch.max(probs, dim=1)
    return CLASS_NAMES[idx.item()], conf.item()


def analyze_frame(frame_bgr):
    """
    Applique YOLO sur une frame BGR (numpy array).
    Retourne (detected: bool, boxes: list of (x1,y1,x2,y2,conf)).
    """
    if DEMO_MODE:
        detected = random.random() < 0.4
        return detected, [(50, 50, 200, 200, 0.82)] if detected else []

    result = yolo_model.predict(frame_bgr, conf=YOLO_CONF, verbose=False)[0]
    detected = len(result.boxes) > 0
    boxes = []
    if detected:
        for box in result.boxes:
            x1, y1, x2, y2 = box.xyxy[0].tolist()
            c = float(box.conf[0])
            boxes.append((x1, y1, x2, y2, c))
    return detected, boxes


def draw_boxes(frame_bgr, boxes):
    """Dessine les boîtes YOLO sur une frame et retourne une image PIL."""
    frame_rgb = cv2.cvtColor(frame_bgr, cv2.COLOR_BGR2RGB)
    img = Image.fromarray(frame_rgb)

    fig, ax = plt.subplots(figsize=(6, 4))
    ax.imshow(img)
    for (x1, y1, x2, y2, conf) in boxes:
        rect = patches.Rectangle(
            (x1, y1), x2 - x1, y2 - y1,
            linewidth=2, edgecolor="red", facecolor="none"
        )
        ax.add_patch(rect)
        ax.text(x1, max(y1 - 6, 0),
                "polype " + f"{conf:.0%}",
                color="red", fontsize=10, fontweight="bold")
    ax.axis("off")
    plt.tight_layout(pad=0)

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=120, bbox_inches="tight")
    plt.close(fig)
    buf.seek(0)
    return Image.open(buf)


def fmt_time(seconds):
    """Formate un nombre de secondes en HH:MM:SS."""
    h = int(seconds // 3600)
    m = int((seconds % 3600) // 60)
    s = int(seconds % 60)
    return f"{h:02d}:{m:02d}:{s:02d}"


def analyze_video_stream(video_path, progress_bar, segments_container):
    """
    Analyse une vidéo frame par frame avec YOLO.
    Affiche chaque segment détecté en temps réel dans segments_container.
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS) or 25
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    duration_s = total_frames / fps

    rows = []
    frame_idx = 0
    segments = []

    # Variables pour le segment en cours
    seg_start = None
    seg_end = None
    seg_max_conf = 0
    seg_best_frame_idx = None
    seg_best_frame_bgr = None
    seg_best_boxes = []
    seg_n = 0
    gap_threshold = (FRAME_SKIP / fps) * 3

    def close_and_display_segment():
        """Ferme le segment courant et l'affiche immédiatement."""
        nonlocal seg_start, seg_end, seg_max_conf
        nonlocal seg_best_frame_idx, seg_best_frame_bgr, seg_best_boxes, seg_n

        dur = seg_end - seg_start
        if dur < MIN_SEGMENT_DURATION:
            return

        seg = {
            "start_s": seg_start, "start_ts": fmt_time(seg_start),
            "end_s": seg_end, "end_ts": fmt_time(seg_end),
            "duration_s": round(dur, 2),
            "max_conf": round(seg_max_conf, 4),
            "best_frame_idx": seg_best_frame_idx,
            "n_frames": seg_n,
        }
        segments.append(seg)

        # Affichage immédiat dans le container streaming
        with segments_container:
            idx = len(segments)
            st.markdown(
                f"#### 🔴 Segment {idx} détecté — "
                f"{seg['start_ts']} → {seg['end_ts']} "
                f"| {seg['duration_s']:.1f}s "
                f"| confiance : {seg['max_conf']:.0%}"
            )
            col_info, col_frame = st.columns([1, 2])
            with col_info:
                st.markdown(f"**Début :** `{seg['start_ts']}`")
                st.markdown(f"**Fin :** `{seg['end_ts']}`")
                st.markdown(f"**Durée :** {seg['duration_s']:.1f} secondes")
                st.markdown(f"**Frame :** #{seg['best_frame_idx']}")
                st.markdown(f"**Confiance :** {seg['max_conf']:.0%}")
            with col_frame:
                if seg_best_frame_bgr is not None:
                    img_with_boxes = draw_boxes(seg_best_frame_bgr, seg_best_boxes)
                    st.image(
                        img_with_boxes,
                        caption=(
                            f"Frame #{seg['best_frame_idx']} "
                            f"à {seg['start_ts']}"
                        ),
                        use_column_width=True
                    )
            st.divider()

        # Réinitialiser
        seg_start = seg_end = seg_best_frame_idx = None
        seg_best_frame_bgr = None
        seg_best_boxes = []
        seg_max_conf = 0
        seg_n = 0

    while True:
        ret, frame = cap.read()
        if not ret:
            break

        if frame_idx % FRAME_SKIP == 0:
            detected, boxes = analyze_frame(frame)
            ts_s = frame_idx / fps

            rows.append({
                "frame_idx": frame_idx,
                "timestamp_s": round(ts_s, 2),
                "timestamp": fmt_time(ts_s),
                "detected": detected,
                "n_boxes": len(boxes),
                "max_conf": round(max(b[4] for b in boxes), 4) if boxes else 0.0,
                "boxes": boxes,
            })

            if detected:
                max_conf = max(b[4] for b in boxes)
                if seg_start is None:
                    # Début d'un nouveau segment
                    seg_start = ts_s
                    seg_end = ts_s
                    seg_max_conf = max_conf
                    seg_best_frame_idx = frame_idx
                    seg_best_frame_bgr = frame.copy()
                    seg_best_boxes = boxes
                    seg_n = 1
                elif ts_s - seg_end <= gap_threshold:
                    # Continuation du segment
                    seg_end = ts_s
                    seg_n += 1
                    if max_conf > seg_max_conf:
                        seg_max_conf = max_conf
                        seg_best_frame_idx = frame_idx
                        seg_best_frame_bgr = frame.copy()
                        seg_best_boxes = boxes
                else:
                    # Gap trop grand → fermer et afficher le segment
                    close_and_display_segment()
                    # Commencer un nouveau segment
                    seg_start = ts_s
                    seg_end = ts_s
                    seg_max_conf = max_conf
                    seg_best_frame_idx = frame_idx
                    seg_best_frame_bgr = frame.copy()
                    seg_best_boxes = boxes
                    seg_n = 1
            else:
                # Pas de détection — fermer le segment si on en avait un
                if seg_start is not None and ts_s - seg_end > gap_threshold:
                    close_and_display_segment()

            # Barre de progression
            progress_bar.progress(min(frame_idx / max(total_frames, 1), 1.0))

        frame_idx += 1

    # Fermer le dernier segment si encore ouvert
    if seg_start is not None:
        close_and_display_segment()

    cap.release()
    progress_bar.progress(1.0)

    return rows, fps, total_frames, duration_s, segments
    """Extrait une frame précise d'une vidéo."""
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    cap.release()
    return frame if ret else None

# -------------------------------------------------------------------
# Interface Streamlit
# -------------------------------------------------------------------

st.title("🩺 Détection d'anomalies digestives")
st.caption("Images et vidéos d'endoscopie — Pipeline hybride YOLO (local) + EfficientNet (cloud)")

if DEMO_MODE:
    st.warning(
        "⚠️ **Mode démo actif** — poids non trouvés. "
        "Les prédictions sont simulées pour présentation.",
        icon="⚠️"
    )

st.divider()

# --- Sélection du type d'entrée ---
input_type = st.radio(
    "Type d'entrée",
    ["🖼️ Image", "🎬 Vidéo"],
    horizontal=True
)

st.divider()

# ===================================================================
# CAS 1 — IMAGE
# ===================================================================

if input_type == "🖼️ Image":
    uploaded = st.file_uploader(
        "Dépose une image (endoscopie / coloscopie)",
        type=["jpg", "jpeg", "png"],
    )

    if uploaded:
        image = Image.open(uploaded).convert("RGB")
        col1, col2 = st.columns([1, 1])

        with col1:
            st.image(image, caption="Image envoyée", use_column_width=True)

        with col2:
            st.markdown("### Déroulé du pipeline")

            with st.spinner("Étage 1 — analyse locale (YOLO)..."):
                detected, n_boxes = predict_stage1_image(image)

            if detected:
                st.success(f"**Étage 1 (YOLO)** : anomalie détectée ({n_boxes} zone(s))")
                st.markdown("→ *Image envoyée à l'étage 2 (cloud)*")

                with st.spinner("Étage 2 — classification précise (EfficientNet)..."):
                    cloud_class, cloud_conf = predict_stage2_image(image)

                st.success(
                    f"**Étage 2 (EfficientNet)** : **{cloud_class.upper()}** "
                    f"(confiance : {cloud_conf:.0%})"
                )
                final_class = cloud_class
            else:
                st.info("**Étage 1 (YOLO)** : aucune anomalie détectée")
                st.markdown("→ *Pas d'appel cloud*")
                final_class = "normal"

        st.divider()
        color = {"normal": "🟢", "polype": "🟠", "mici": "🟠",
                 "mauvaise_preparation": "🟡"}.get(final_class, "⚪")
        st.markdown(f"## Résultat final : {color} **{final_class.upper()}**")

    else:
        st.info("👆 Dépose une image ci-dessus pour lancer l'analyse.")

# ===================================================================
# CAS 2 — VIDÉO
# ===================================================================

else:
    uploaded_video = st.file_uploader(
        "Dépose une vidéo d'endoscopie (.avi, .mp4, .mov)",
        type=["avi", "mp4", "mov"],
    )

    if uploaded_video:
        # Sauvegarder la vidéo dans un fichier temporaire
        with tempfile.NamedTemporaryFile(
            delete=False,
            suffix="." + uploaded_video.name.split(".")[-1]
        ) as tmp:
            tmp.write(uploaded_video.read())
            tmp_path = tmp.name

        # Informations sur la vidéo
        cap_info = cv2.VideoCapture(tmp_path)
        fps_info = cap_info.get(cv2.CAP_PROP_FPS) or 25
        total_info = int(cap_info.get(cv2.CAP_PROP_FRAME_COUNT))
        dur_info = total_info / fps_info
        cap_info.release()

        st.markdown(f"**Vidéo chargée :** `{uploaded_video.name}` — "
                    f"{dur_info/60:.1f} min · {fps_info:.0f} fps · {total_info} frames")
        st.divider()

        if st.button("▶️ Lancer l'analyse", type="primary"):
            st.markdown("### Analyse en cours...")
            progress = st.progress(0)

            st.divider()
            st.markdown("### 📍 Segments détectés en temps réel")
            st.caption("Les polypes apparaissent ici au fur et à mesure de l'analyse.")
            segments_container = st.container()

            rows, fps, total_frames, duration_s, segments = \
                analyze_video_stream(tmp_path, progress, segments_container)

            # Résumé final (après analyse complète)
            st.divider()
            st.markdown("### Résumé final")
            col_a, col_b, col_c, col_d = st.columns(4)
            col_a.metric("Durée", f"{duration_s/60:.1f} min")
            col_b.metric("Frames analysées", len(rows))
            col_c.metric("Frames avec polype", sum(1 for r in rows if r["detected"]))
            col_d.metric("Segments détectés", len(segments))


            st.divider()

            if segments:
                st.success(
                    f"✅ **{len(segments)} polype(s) détecté(s)** "
                    f"sur {duration_s/60:.1f} minutes de vidéo"
                )

                # --- Timeline des segments ---
                st.markdown("### 📍 Timeline des détections")
                st.caption(
                    "Chaque ligne correspond à une apparition de polype "
                    "dans la vidéo, avec le timestamp précis et la frame exacte."
                )

                for i, seg in enumerate(segments, 1):
                    with st.expander(
                        f"**Segment {i}** — "
                        f"{seg['start_ts']} → {seg['end_ts']} "
                        f"| durée : {seg['duration_s']:.1f}s "
                        f"| confiance : {seg['max_conf']:.0%}",
                        expanded=(i == 1)
                    ):
                        col_info, col_frame = st.columns([1, 2])

                        with col_info:
                            st.markdown(f"**Début :** {seg['start_ts']}")
                            st.markdown(f"**Fin :** {seg['end_ts']}")
                            st.markdown(f"**Durée :** {seg['duration_s']:.1f} secondes")
                            st.markdown(f"**Frame clé :** #{seg['best_frame_idx']}")
                            st.markdown(f"**Confiance max :** {seg['max_conf']:.0%}")
                            st.markdown(f"**Frames détectées :** {seg['n_frames']}")

                        with col_frame:
                            frame = get_frame_at(tmp_path, seg["best_frame_idx"])
                            if frame is not None:
                                # Récupérer les boîtes de cette frame
                                frame_row = next(
                                    (r for r in rows
                                     if r["frame_idx"] == seg["best_frame_idx"]),
                                    None
                                )
                                boxes = frame_row["boxes"] if frame_row else []
                                img_with_boxes = draw_boxes(frame, boxes)
                                st.image(
                                    img_with_boxes,
                                    caption=f"Frame #{seg['best_frame_idx']} "
                                            f"à {seg['start_ts']}",
                                    use_column_width=True
                                )

                # --- Graphique timeline ---
                st.divider()
                st.markdown("### 📊 Graphique de présence du polype")

                timestamps = [r["timestamp_s"] for r in rows]
                conf_values = [r["max_conf"] for r in rows]
                detected_flags = [r["detected"] for r in rows]

                fig, (ax1, ax2) = plt.subplots(
                    2, 1, figsize=(12, 5),
                    gridspec_kw={"height_ratios": [3, 1]}
                )

                ax1.plot(timestamps, conf_values, color="#4C72B0",
                         linewidth=0.8, alpha=0.7, label="Confiance YOLO")
                ax1.axhline(YOLO_CONF, color="orange", linestyle="--",
                            linewidth=1, label=f"Seuil ({YOLO_CONF})")
                ax1.fill_between(
                    timestamps, conf_values,
                    where=detected_flags,
                    alpha=0.3, color="red", label="Détection active"
                )
                ax1.set_ylabel("Confiance")
                ax1.set_ylim(0, 1.05)
                ax1.legend(fontsize=9)
                ax1.set_title(f"Timeline — {uploaded_video.name}")

                for seg in segments:
                    ax2.barh(0, seg["duration_s"], left=seg["start_s"],
                             height=0.6, color="red", alpha=0.8)
                    ax2.text(
                        seg["start_s"] + seg["duration_s"] / 2, 0,
                        seg["start_ts"],
                        ha="center", va="center",
                        fontsize=7, color="white", fontweight="bold"
                    )

                ax2.set_xlim(0, duration_s)
                ax2.set_xlabel("Temps (secondes)")
                ax2.set_yticks([])
                ax2.set_ylabel("Polypes")

                plt.tight_layout()
                st.pyplot(fig)

            else:
                st.info(
                    "ℹ️ Aucun polype détecté dans cette vidéo "
                    f"(seuil de confiance : {YOLO_CONF})."
                )

            # --- Export CSV ---
            st.divider()
            import pandas as pd
            seg_df = pd.DataFrame(segments) if segments else pd.DataFrame()

            if not seg_df.empty:
                csv_segments = seg_df[
                    ["start_ts", "end_ts", "duration_s",
                     "best_frame_idx", "max_conf", "n_frames"]
                ].to_csv(index=False)

                st.download_button(
                    label="⬇️ Télécharger le rapport (CSV)",
                    data=csv_segments,
                    file_name="rapport_detections.csv",
                    mime="text/csv",
                )

        os.unlink(tmp_path) if os.path.exists(tmp_path) else None

    else:
        st.info("👆 Dépose une vidéo ci-dessus pour lancer l'analyse.")

st.divider()
st.caption(
    "medet — Pipeline hybride YOLO (étage 1, local) + EfficientNet (étage 2, cloud) · "
    "Usage interne, pas d'utilisation clinique."
)
