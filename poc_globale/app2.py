"""
app2.py — Détection de polypes : images ET vidéos
===================================================

Extension de app.py pour l'équipe médicale :
- Images : même pipeline qu'avant (YOLO étage 1 → EfficientNet étage 2)
- Vidéos  : analyse frame par frame, affichage de la timeline,
            des secondes et frames exactes de chaque détection,
            et de la frame clé avec la boîte dessinée.

Interface redessinée dans un langage visuel clinique premium
(palette navy/teal, typographie IBM Plex, cartes et tableau de bord)
— la logique de détection, de streaming et d'export est strictement
inchangée par rapport à la version d'origine.

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
# Palette & typographie — identité visuelle "clinique premium"
# -------------------------------------------------------------------
# Ces valeurs pilotent uniquement l'apparence (CSS + couleurs matplotlib).
# Aucune ne participe à la logique de détection.

COLOR_NAVY        = "#0B2545"   # bleu nuit clinique — en-têtes, texte fort
COLOR_TEAL        = "#0F8B8D"   # teal médical — accent principal
COLOR_TEAL_DARK   = "#0A6567"
COLOR_DANGER      = "#D64550"   # alerte / anomalie confirmée
COLOR_WARNING     = "#E8A33D"   # prudence / seuil / préparation
COLOR_SUCCESS     = "#2E9E6B"   # normal / rien détecté
COLOR_BG          = "#F3F6F8"   # fond général, gris-bleu très clair
COLOR_SURFACE     = "#FFFFFF"
COLOR_BORDER      = "#DFE6EB"
COLOR_INK         = "#14213D"
COLOR_INK_MUTED   = "#5C6B7A"

# Applique la palette aux graphiques matplotlib (uniquement esthétique).
plt.rcParams.update({
    "font.family": "sans-serif",
    "font.sans-serif": ["IBM Plex Sans", "Helvetica Neue", "Arial", "sans-serif"],
    "axes.edgecolor": COLOR_BORDER,
    "axes.labelcolor": COLOR_INK,
    "text.color": COLOR_INK,
    "xtick.color": COLOR_INK_MUTED,
    "ytick.color": COLOR_INK_MUTED,
    "axes.facecolor": COLOR_SURFACE,
    "figure.facecolor": COLOR_SURFACE,
    "grid.color": COLOR_BORDER,
    "grid.alpha": 0.6,
})

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
# Feuille de style premium (clinique / instrumentation médicale)
# -------------------------------------------------------------------

PREMIUM_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=IBM+Plex+Sans:wght@400;500;600;700&family=IBM+Plex+Mono:wght@400;500;600&display=swap');

html, body, [class*="css"] {
    font-family: 'IBM Plex Sans', 'Helvetica Neue', Arial, sans-serif;
}

/* Fond général */
[data-testid="stAppViewContainer"] {
    background: #F3F6F8;
}
[data-testid="stHeader"] {
    background: rgba(255,255,255,0.0);
}
.block-container {
    padding-top: 1.6rem;
    padding-bottom: 3rem;
    max-width: 1180px;
}

/* Barre latérale */
[data-testid="stSidebar"] {
    background: #F7FAFC;
    border-right: 1px solid #DFE6EB;
}
[data-testid="stSidebar"] * {
    color: #14213D !important;
}
[data-testid="stSidebar"] hr {
    border-color: rgba(11,37,69,0.12) !important;
}

/* En-tête produit */
.medet-header {
    display: flex;
    align-items: center;
    gap: 18px;
    padding: 22px 26px;
    background: linear-gradient(135deg, #0B2545 0%, #0F8B8D 130%);
    border-radius: 16px;
    box-shadow: 0 8px 24px rgba(11, 37, 69, 0.18);
    margin-bottom: 4px;
}
.medet-header-mark {
    width: 52px;
    height: 52px;
    min-width: 52px;
    border-radius: 12px;
    background: rgba(255,255,255,0.12);
    border: 1px solid rgba(255,255,255,0.25);
    display: flex;
    align-items: center;
    justify-content: center;
    font-size: 26px;
    color: #ffffff;
}
.medet-eyebrow {
    text-transform: uppercase;
    letter-spacing: 0.12em;
    font-size: 0.72rem;
    font-weight: 600;
    color: rgba(255,255,255,0.75);
    margin-bottom: 2px;
}
.medet-title {
    color: #ffffff;
    font-size: 1.55rem;
    font-weight: 700;
    margin: 0;
    letter-spacing: -0.01em;
}
.medet-subtitle {
    color: rgba(255,255,255,0.85);
    font-size: 0.92rem;
    margin: 4px 0 0 0;
}

/* Séparateurs — trait façon tracé ECG */
hr {
    border: none !important;
    height: 10px !important;
    margin: 1.4rem 0 !important;
    background-image: url("data:image/svg+xml;utf8,<svg xmlns='http://www.w3.org/2000/svg' width='120' height='10' viewBox='0 0 120 10'><polyline points='0,5 30,5 38,1 44,9 50,5 120,5' fill='none' stroke='%230F8B8D' stroke-width='1.2' opacity='0.55'/></svg>");
    background-repeat: repeat-x;
    background-position: center;
}

/* Titres de section */
h1, h2, h3 { color: #0B2545; font-weight: 700; letter-spacing: -0.01em; }
h4, h5 { color: #14213D; font-weight: 600; }
p, li, label, span { color: #14213D; }
.stCaption, [data-testid="stCaptionContainer"] { color: #5C6B7A !important; }

/* Boutons radio (sélecteur d'entrée) */
[data-testid="stRadio"] > div {
    gap: 8px;
}
[data-testid="stRadio"] label {
    background: #EAF4FC;
    border: 1px solid #BEE0F5;
    border-radius: 10px;
    padding: 8px 14px;
    transition: all 0.15s ease;
}
[data-testid="stRadio"] label:hover {
    border-color: #0F8B8D;
    background: #DCEEFB;
}

/* Boutons */
.stButton button, .stDownloadButton button {
    border-radius: 10px;
    font-weight: 600;
    border: 1px solid #DFE6EB;
    padding: 0.55rem 1.1rem;
    transition: all 0.15s ease;
}
.stButton button[kind="primary"] {
    background: linear-gradient(135deg, #0F8B8D, #0A6567);
    border: none;
    color: #ffffff;
    box-shadow: 0 4px 12px rgba(15, 139, 141, 0.28);
}
.stButton button[kind="primary"]:hover {
    box-shadow: 0 6px 16px rgba(15, 139, 141, 0.4);
    transform: translateY(-1px);
}
.stDownloadButton button {
    background: #ffffff;
    color: #0B2545;
}
.stDownloadButton button:hover {
    border-color: #0F8B8D;
    color: #0F8B8D;
}

/* Cases à cocher / sliders / number input */
[data-testid="stCheckbox"] label p { font-weight: 500; }

/* Zone de dépôt de fichier */
[data-testid="stFileUploader"] {
    border-radius: 12px;
}
[data-testid="stFileUploaderDropzone"] {
    background: #FFFFFF !important;
    border: 1.5px dashed #B9C6CE !important;
    border-radius: 12px !important;
}

/* Cartes conteneurs (segments, résultats) */
[data-testid="stVerticalBlockBorderWrapper"] {
    background: #FFFFFF;
    border-radius: 14px !important;
    border: 1px solid #DFE6EB !important;
    box-shadow: 0 2px 10px rgba(11, 37, 69, 0.05);
    margin-bottom: 14px;
}

/* Métriques */
[data-testid="stMetric"] {
    background: #FFFFFF;
    border: 1px solid #DFE6EB;
    border-radius: 12px;
    padding: 14px 16px;
    box-shadow: 0 2px 8px rgba(11, 37, 69, 0.04);
}
[data-testid="stMetricLabel"] {
    color: #5C6B7A !important;
    font-size: 0.8rem !important;
    text-transform: uppercase;
    letter-spacing: 0.05em;
}
[data-testid="stMetricValue"] {
    color: #0B2545 !important;
    font-family: 'IBM Plex Mono', monospace;
}

/* Expanders (segments vidéo) */
[data-testid="stExpander"] {
    border: 1px solid #DFE6EB !important;
    border-radius: 12px !important;
    background: #FFFFFF;
    overflow: hidden;
}

/* Alertes (success / info / warning / error) */
[data-testid="stAlert"], .stAlert {
    border-radius: 10px !important;
    border: 1px solid #DFE6EB !important;
    font-size: 0.92rem;
}

/* Tableaux de données */
[data-testid="stDataFrame"] {
    border: 1px solid #DFE6EB;
    border-radius: 10px;
    overflow: hidden;
}

/* Badges d'information (statuts modèle, chips) */
.medet-chip {
    display: inline-flex;
    align-items: center;
    gap: 6px;
    padding: 3px 10px;
    border-radius: 999px;
    font-size: 0.78rem;
    font-weight: 600;
    font-family: 'IBM Plex Mono', monospace;
}
.medet-chip-ok { background: rgba(46,158,107,0.12); color: #2E9E6B; }
.medet-chip-demo { background: rgba(232,163,61,0.15); color: #B87A1E; }

/* Bandeau statistique (infos fichier / flux) */
.medet-stat-strip {
    display: flex;
    flex-wrap: wrap;
    gap: 22px;
    background: #FFFFFF;
    border: 1px solid #DFE6EB;
    border-radius: 12px;
    padding: 12px 18px;
    margin-bottom: 6px;
    font-family: 'IBM Plex Mono', monospace;
    font-size: 0.88rem;
    color: #14213D;
}
.medet-stat-strip b { color: #0B2545; }

/* Carte de résultat final (image) */
.result-card {
    display: flex;
    align-items: center;
    gap: 16px;
    padding: 18px 22px;
    border-radius: 14px;
    border: 1px solid #DFE6EB;
    background: #FFFFFF;
}
.result-card .result-icon { font-size: 2rem; line-height: 1; }
.result-label {
    text-transform: uppercase;
    letter-spacing: 0.08em;
    font-size: 0.72rem;
    font-weight: 600;
    color: #5C6B7A;
    margin-bottom: 2px;
}
.result-value {
    font-size: 1.35rem;
    font-weight: 700;
    font-family: 'IBM Plex Mono', monospace;
}
.result-success { border-left: 5px solid #2E9E6B; }
.result-success .result-value { color: #2E9E6B; }
.result-warning { border-left: 5px solid #E8A33D; }
.result-warning .result-value { color: #B87A1E; }
.result-danger { border-left: 5px solid #D64550; }
.result-danger .result-value { color: #D64550; }
.result-neutral { border-left: 5px solid #B9C6CE; }

/* Pastille LIVE clignotante (webcam / RTSP) */
.medet-live-dot {
    display: inline-block;
    width: 9px; height: 9px;
    border-radius: 50%;
    background: #D64550;
    margin-right: 6px;
    animation: medet-pulse 1.4s infinite;
}
@keyframes medet-pulse {
    0% { box-shadow: 0 0 0 0 rgba(214,69,80,0.5); }
    70% { box-shadow: 0 0 0 8px rgba(214,69,80,0); }
    100% { box-shadow: 0 0 0 0 rgba(214,69,80,0); }
}

/* Pied de page */
.medet-footer {
    text-align: center;
    color: #5C6B7A;
    font-size: 0.82rem;
    padding-top: 6px;
}
</style>
"""

st.markdown(PREMIUM_CSS, unsafe_allow_html=True)

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
            linewidth=2.4, edgecolor=COLOR_DANGER, facecolor="none"
        )
        ax.add_patch(rect)
        ax.text(x1, max(y1 - 6, 0),
                "polype " + f"{conf:.0%}",
                color=COLOR_DANGER, fontsize=10, fontweight="bold")
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
            with st.container(border=True):
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


def get_frame_at(video_path, frame_idx):
    """Extrait une frame précise d'une vidéo."""
    cap = cv2.VideoCapture(video_path)
    cap.set(cv2.CAP_PROP_POS_FRAMES, frame_idx)
    ret, frame = cap.read()
    cap.release()
    return frame if ret else None

# -------------------------------------------------------------------
# Barre latérale — identité & état du pipeline
# -------------------------------------------------------------------

with st.sidebar:
    st.markdown(
        """
        <div style="display:flex;align-items:center;gap:10px;margin-bottom:4px;">
            <div style="width:38px;height:38px;border-radius:10px;background:rgba(15,139,141,0.12);
                        border:1px solid rgba(15,139,141,0.3);display:flex;align-items:center;
                        justify-content:center;font-size:20px;">🩺</div>
            <div>
                <div style="font-weight:700;font-size:1.05rem;color:#0B2545;">medet</div>
                <div style="font-size:0.72rem;color:#5C6B7A;">Aide au diagnostic endoscopique</div>
            </div>
        </div>
        """,
        unsafe_allow_html=True,
    )
    st.divider()
    st.markdown("#### État du pipeline")

    yolo_chip = (
        '<span class="medet-chip medet-chip-ok">🟢 Chargé</span>'
        if yolo_model is not None
        else '<span class="medet-chip medet-chip-demo">🟡 Démo</span>'
    )
    eff_chip = (
        '<span class="medet-chip medet-chip-ok">🟢 Chargé</span>'
        if eff_model is not None
        else '<span class="medet-chip medet-chip-demo">🟡 Démo</span>'
    )
    st.markdown(f"**Étage 1 — YOLO (local)**<br>{yolo_chip}", unsafe_allow_html=True)
    st.markdown(f"**Étage 2 — EfficientNet (cloud)**<br>{eff_chip}", unsafe_allow_html=True)

    st.divider()
    st.markdown("#### Paramètres actifs")
    st.caption(f"Seuil de confiance YOLO : **{YOLO_CONF}**")
    st.caption(f"Frame analysée : 1 sur {FRAME_SKIP}")
    st.caption("Classes : " + ", ".join(CLASS_NAMES))

    st.divider()
    st.caption("Usage interne uniquement — pas d'utilisation clinique.")

# -------------------------------------------------------------------
# Interface Streamlit
# -------------------------------------------------------------------

st.markdown(
    """
    <div class="medet-header">
      <div class="medet-header-mark">⌬</div>
      <div class="medet-header-text">
        <div class="medet-eyebrow">Pipeline d'aide au diagnostic</div>
        <h1 class="medet-title">Détection d'anomalies digestives</h1>
        <p class="medet-subtitle">Images et vidéos d'endoscopie — Pipeline hybride YOLO (local) + EfficientNet (cloud)</p>
      </div>
    </div>
    """,
    unsafe_allow_html=True,
)

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
    [" Image", " Vidéo", " Webcam (live)", "🔗 Flux réseau (URL)"],
    horizontal=True
)

st.divider()

# ===================================================================
# CAS 1 — IMAGE
# ===================================================================

if input_type == " Image":
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
        badge_class = {
            "normal": "result-success",
            "polype": "result-danger",
            "mici": "result-danger",
            "mauvaise_preparation": "result-warning",
        }.get(final_class, "result-neutral")
        st.markdown(
            f"""
            <div class="result-card {badge_class}">
                <div class="result-icon">{color}</div>
                <div>
                    <div class="result-label">Résultat final</div>
                    <div class="result-value">{final_class.upper()}</div>
                </div>
            </div>
            """,
            unsafe_allow_html=True,
        )

    else:
        st.info("👆 Dépose une image ci-dessus pour lancer l'analyse.")

# ===================================================================
# CAS 2 — VIDÉO
# ===================================================================

elif input_type == " Vidéo":
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

        st.markdown(
            f"""
            <div class="medet-stat-strip">
                <div>📁 <b>{uploaded_video.name}</b></div>
                <div>⏱ <b>{dur_info/60:.1f}</b> min</div>
                <div>🎞 <b>{fps_info:.0f}</b> fps</div>
                <div>🧮 <b>{total_info}</b> frames</div>
            </div>
            """,
            unsafe_allow_html=True,
        )
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

                ax1.plot(timestamps, conf_values, color=COLOR_TEAL,
                         linewidth=1.1, alpha=0.85, label="Confiance YOLO")
                ax1.axhline(YOLO_CONF, color=COLOR_WARNING, linestyle="--",
                            linewidth=1, label=f"Seuil ({YOLO_CONF})")
                ax1.fill_between(
                    timestamps, conf_values,
                    where=detected_flags,
                    alpha=0.28, color=COLOR_DANGER, label="Détection active"
                )
                ax1.grid(True, axis="y", alpha=0.4)
                ax1.spines[["top", "right"]].set_visible(False)
                ax1.set_ylabel("Confiance")
                ax1.set_ylim(0, 1.05)
                ax1.legend(fontsize=9)
                ax1.set_title(f"Timeline — {uploaded_video.name}")

                for seg in segments:
                    ax2.barh(0, seg["duration_s"], left=seg["start_s"],
                             height=0.6, color=COLOR_DANGER, alpha=0.85)
                    ax2.text(
                        seg["start_s"] + seg["duration_s"] / 2, 0,
                        seg["start_ts"],
                        ha="center", va="center",
                        fontsize=7, color="white", fontweight="bold"
                    )

                ax2.set_xlim(0, duration_s)
                ax2.spines[["top", "right", "left"]].set_visible(False)
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

# ===================================================================
# CAS 3 — WEBCAM (live)
# ===================================================================

elif input_type == " Webcam (live)":
    st.caption(
        "Lit un flux caméra local en direct — sert à valider le pipeline "
        "en streaming avant le branchement sur un vrai flux endoscopique (RTSP)."
    )

    camera_index = st.number_input(
        "Index de la caméra", min_value=0, max_value=5, value=0, step=1
    )
    frame_skip_webcam = st.slider(
        "Analyser 1 frame sur N", min_value=1, max_value=10, value=3,
        help="Réduit la charge CPU. Valeur 3 = environ 10 analyses/sec sur 30fps."
    )
    run = st.checkbox("▶️ Démarrer le flux", key="run_webcam")

    col_live, col_hist = st.columns([2, 1])
    frame_placeholder  = col_live.empty()
    status_placeholder = col_live.empty()
    hist_placeholder   = col_hist.empty()

    # Historique des détections dans la session
    if "webcam_detections" not in st.session_state:
        st.session_state.webcam_detections = []

    if run:
        cap = cv2.VideoCapture(int(camera_index))
        if not cap.isOpened():
            st.error(f"Impossible d'ouvrir la caméra à l'index {camera_index}.")
        else:
            frame_idx  = 0
            start_time = time.time()

            while st.session_state.get("run_webcam", False):
                ret, frame = cap.read()
                if not ret:
                    st.warning("Flux interrompu ou caméra déconnectée.")
                    break

                elapsed = time.time() - start_time
                ts = fmt_time(elapsed)

                if frame_idx % frame_skip_webcam == 0:
                    detected, boxes = analyze_frame(frame)

                    if detected:
                        img_with_boxes = draw_boxes(frame, boxes)
                        frame_placeholder.image(
                            img_with_boxes,
                            caption=f"⏱ {ts} — Frame #{frame_idx} — anomalie détectée",
                            use_column_width=True,
                        )
                        pil_frame = Image.fromarray(cv2.cvtColor(frame, cv2.COLOR_BGR2RGB))
                        label, conf = predict_stage2_image(pil_frame)
                        status_placeholder.success(
                            f"**Étage 2 :** `{label.upper()}` — confiance : {conf:.0%}"
                        )
                        # Ajouter à l'historique
                        st.session_state.webcam_detections.append({
                            "timestamp": ts,
                            "frame": frame_idx,
                            "classe": label,
                            "confiance": f"{conf:.0%}",
                        })
                    else:
                        frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                        frame_placeholder.image(
                            frame_rgb, channels="RGB",
                            caption=f"⏱ {ts} — Frame #{frame_idx} — rien détecté"
                        )
                        status_placeholder.info("Aucune anomalie détectée.")

                    # Mise à jour historique en temps réel
                    if st.session_state.webcam_detections:
                        import pandas as pd
                        df_hist = pd.DataFrame(st.session_state.webcam_detections[-10:])
                        hist_placeholder.markdown("**🔴 Détections récentes**")
                        hist_placeholder.dataframe(df_hist, hide_index=True, use_container_width=True)

                frame_idx += 1

            cap.release()

    # Export CSV historique
    if st.session_state.get("webcam_detections"):
        import pandas as pd
        csv = pd.DataFrame(st.session_state.webcam_detections).to_csv(index=False)
        st.download_button(
            "⬇️ Télécharger le rapport de session (CSV)",
            data=csv,
            file_name="rapport_webcam.csv",
            mime="text/csv"
        )
        if st.button("🗑️ Effacer l'historique"):
            st.session_state.webcam_detections = []
            st.rerun()

    if DEMO_MODE:
        st.caption("⚠️ Mode démo : détections simulées (poids introuvables).")


# ===================================================================
# CAS 4 — FLUX RÉSEAU RTSP (endoscope réel)
# ===================================================================

elif input_type == "🔗 Flux réseau (URL)":
    st.caption(
        "Se connecte au flux vidéo de la tour d'endoscopie en temps réel "
        "(RTSP, HTTP/MJPEG). Produit les mêmes sorties que le mode vidéo : "
        "timeline, frames clés, graphique et rapport CSV."
    )

    stream_url = st.text_input(
        "URL du flux",
        placeholder="rtsp://user:pass@192.168.1.50:554/stream1",
        help="Formats supportés : rtsp://, http:// (MJPEG), .m3u8 (HLS)",
    )

    col_cfg1, col_cfg2 = st.columns(2)
    frame_skip_url = col_cfg1.slider(
        "Analyser 1 frame sur N", min_value=1, max_value=15, value=FRAME_SKIP,
        help="Plus la valeur est haute, moins ça consomme de CPU."
    )
    max_reconnects = col_cfg2.number_input(
        "Tentatives de reconnexion automatique", min_value=0, max_value=10, value=3
    )

    run_url = st.checkbox(
        "▶️ Se connecter et démarrer l'analyse", key="run_url_stream"
    )

    if "rtsp_rows"     not in st.session_state:
        st.session_state.rtsp_rows     = []
    if "rtsp_segments" not in st.session_state:
        st.session_state.rtsp_segments = []

    # Variables de segment en cours (stockées en session pour survivre aux reruns)
    if "rtsp_seg_start"    not in st.session_state:
        st.session_state.rtsp_seg_start    = None
    if "rtsp_seg_end"      not in st.session_state:
        st.session_state.rtsp_seg_end      = None
    if "rtsp_seg_conf"     not in st.session_state:
        st.session_state.rtsp_seg_conf     = 0.0
    if "rtsp_seg_frame"    not in st.session_state:
        st.session_state.rtsp_seg_frame    = None
    if "rtsp_seg_boxes"    not in st.session_state:
        st.session_state.rtsp_seg_boxes    = []
    if "rtsp_seg_n"        not in st.session_state:
        st.session_state.rtsp_seg_n        = 0
    if "rtsp_start_time"   not in st.session_state:
        st.session_state.rtsp_start_time   = None

    # Layout : flux live à gauche, segments détectés à droite
    col_live, col_segs = st.columns([1, 1])

    with col_live:
        st.markdown('### 📡 Flux en direct <span class="medet-live-dot"></span>', unsafe_allow_html=True)
        live_frame_ph  = st.empty()
        live_status_ph = st.empty()

    with col_segs:
        st.markdown("### 📍 Segments détectés")
        st.caption("S'actualise en temps réel dès qu'un polype est confirmé.")
        segments_ph = st.container()

    # Graphique timeline (en dessous)
    st.divider()
    st.markdown("### 📊 Timeline (mise à jour en continu)")
    timeline_ph = st.empty()

    # ---------------------------------------------------------------
    def close_rtsp_segment():
        """Ferme le segment courant et l'affiche immédiatement."""
        seg_start = st.session_state.rtsp_seg_start
        seg_end   = st.session_state.rtsp_seg_end

        if seg_start is None:
            return
        dur = seg_end - seg_start
        if dur < MIN_SEGMENT_DURATION:
            # Réinitialiser sans afficher
            st.session_state.rtsp_seg_start = None
            return

        seg = {
            "start_s":        seg_start,
            "start_ts":       fmt_time(seg_start),
            "end_s":          seg_end,
            "end_ts":         fmt_time(seg_end),
            "duration_s":     round(dur, 2),
            "max_conf":       round(st.session_state.rtsp_seg_conf, 4),
            "best_frame_bgr": st.session_state.rtsp_seg_frame,
            "best_boxes":     st.session_state.rtsp_seg_boxes,
            "n_frames":       st.session_state.rtsp_seg_n,
        }
        st.session_state.rtsp_segments.append(seg)

        # Affichage immédiat dans le container segments
        with segments_ph:
            idx = len(st.session_state.rtsp_segments)
            with st.container(border=True):
                st.markdown(
                    f"#### 🔴 Segment {idx} — "
                    f"{seg['start_ts']} → {seg['end_ts']} "
                    f"| {seg['duration_s']:.1f}s "
                    f"| {seg['max_conf']:.0%}"
                )
                c1, c2 = st.columns([1, 2])
                with c1:
                    st.markdown(f"**Début :** `{seg['start_ts']}`")
                    st.markdown(f"**Fin :** `{seg['end_ts']}`")
                    st.markdown(f"**Durée :** {seg['duration_s']:.1f}s")
                    st.markdown(f"**Confiance :** {seg['max_conf']:.0%}")
                    st.markdown(f"**Frames :** {seg['n_frames']}")
                with c2:
                    if seg["best_frame_bgr"] is not None:
                        img_boxes = draw_boxes(seg["best_frame_bgr"], seg["best_boxes"])
                        start_ts = seg["start_ts"]
                        st.image(
                            img_boxes,
                            caption=f"Frame clé à {start_ts}",
                            use_column_width=True
                        )

        # Réinitialiser le segment courant
        st.session_state.rtsp_seg_start = None
        st.session_state.rtsp_seg_end   = None
        st.session_state.rtsp_seg_conf  = 0.0
        st.session_state.rtsp_seg_frame = None
        st.session_state.rtsp_seg_boxes = []
        st.session_state.rtsp_seg_n     = 0

    # ---------------------------------------------------------------
    def update_timeline():
        """Met à jour le graphique timeline avec les données actuelles."""
        rows = st.session_state.rtsp_rows
        segs = st.session_state.rtsp_segments
        if not rows:
            return

        timestamps  = [r["timestamp_s"] for r in rows]
        conf_values = [r["max_conf"]     for r in rows]
        detected    = [r["detected"]     for r in rows]
        duration_s  = rows[-1]["timestamp_s"] if rows else 1

        fig, (ax1, ax2) = plt.subplots(
            2, 1, figsize=(12, 4),
            gridspec_kw={"height_ratios": [3, 1]}
        )
        ax1.plot(timestamps, conf_values, color=COLOR_TEAL,
                 linewidth=1.0, alpha=0.85, label="Confiance YOLO")
        ax1.axhline(YOLO_CONF, color=COLOR_WARNING, linestyle="--",
                    linewidth=1, label=f"Seuil ({YOLO_CONF})")
        ax1.fill_between(timestamps, conf_values,
                         where=detected, alpha=0.28, color=COLOR_DANGER,
                         label="Détection active")
        ax1.grid(True, axis="y", alpha=0.4)
        ax1.spines[["top", "right"]].set_visible(False)
        ax1.set_ylabel("Confiance")
        ax1.set_ylim(0, 1.05)
        ax1.legend(fontsize=8)
        ax1.set_title("Timeline flux endoscopique en direct")

        for seg in segs:
            ax2.barh(0, seg["duration_s"], left=seg["start_s"],
                     height=0.6, color=COLOR_DANGER, alpha=0.85)

        ax2.set_xlim(0, max(duration_s, 1))
        ax2.spines[["top", "right", "left"]].set_visible(False)
        ax2.set_xlabel("Temps (secondes)")
        ax2.set_yticks([])
        ax2.set_ylabel("Polypes")

        plt.tight_layout()
        timeline_ph.pyplot(fig)
        plt.close(fig)

    # ---------------------------------------------------------------
    if run_url:
        if not stream_url:
            st.error("Merci de renseigner une URL de flux avant de démarrer.")
        else:
            if st.session_state.rtsp_start_time is None:
                st.session_state.rtsp_start_time = time.time()

            reconnect_count = 0
            frame_idx       = 0
            gap_threshold   = (frame_skip_url / 25) * 3

            while st.session_state.get("run_url_stream", False):
                cap = cv2.VideoCapture(stream_url)

                if not cap.isOpened():
                    reconnect_count += 1
                    if reconnect_count > max_reconnects:
                        live_status_ph.error(
                            f"Connexion impossible après {max_reconnects} tentatives : "
                            f"`{stream_url}`"
                        )
                        break
                    live_status_ph.warning(
                        f"Reconnexion {reconnect_count}/{max_reconnects}..."
                    )
                    time.sleep(2)
                    continue

                reconnect_count = 0
                live_status_ph.success(f"✅ Connecté : `{stream_url}`")

                while st.session_state.get("run_url_stream", False):
                    ret, frame = cap.read()
                    if not ret:
                        live_status_ph.warning("Flux interrompu — reconnexion...")
                        break

                    elapsed = time.time() - st.session_state.rtsp_start_time
                    ts = fmt_time(elapsed)

                    if frame_idx % frame_skip_url == 0:
                        detected, boxes = analyze_frame(frame)
                        max_conf = max(b[4] for b in boxes) if boxes else 0.0

                        # Enregistrer la frame
                        st.session_state.rtsp_rows.append({
                            "timestamp_s": round(elapsed, 2),
                            "timestamp":   ts,
                            "detected":    detected,
                            "max_conf":    round(max_conf, 4),
                        })

                        # Gestion du segment en cours
                        if detected:
                            if st.session_state.rtsp_seg_start is None:
                                # Nouveau segment
                                st.session_state.rtsp_seg_start = elapsed
                                st.session_state.rtsp_seg_end   = elapsed
                                st.session_state.rtsp_seg_conf  = max_conf
                                st.session_state.rtsp_seg_frame = frame.copy()
                                st.session_state.rtsp_seg_boxes = boxes
                                st.session_state.rtsp_seg_n     = 1
                            elif elapsed - st.session_state.rtsp_seg_end <= gap_threshold:
                                # Continuation
                                st.session_state.rtsp_seg_end = elapsed
                                st.session_state.rtsp_seg_n  += 1
                                if max_conf > st.session_state.rtsp_seg_conf:
                                    st.session_state.rtsp_seg_conf  = max_conf
                                    st.session_state.rtsp_seg_frame = frame.copy()
                                    st.session_state.rtsp_seg_boxes = boxes
                            else:
                                # Gap trop grand → fermer et démarrer nouveau
                                close_rtsp_segment()
                                st.session_state.rtsp_seg_start = elapsed
                                st.session_state.rtsp_seg_end   = elapsed
                                st.session_state.rtsp_seg_conf  = max_conf
                                st.session_state.rtsp_seg_frame = frame.copy()
                                st.session_state.rtsp_seg_boxes = boxes
                                st.session_state.rtsp_seg_n     = 1
                        else:
                            # Pas de détection : fermer le segment si gap suffisant
                            if (st.session_state.rtsp_seg_start is not None and
                                    elapsed - st.session_state.rtsp_seg_end > gap_threshold):
                                close_rtsp_segment()

                        # Affichage live
                        if detected:
                            img_boxes = draw_boxes(frame, boxes)
                            live_frame_ph.image(
                                img_boxes,
                                caption=f"⏱ {ts} — Frame #{frame_idx} — 🔴 anomalie",
                                use_column_width=True
                            )
                            live_status_ph.success(
                                f"⏱ {ts} | Frame #{frame_idx} — "
                                f"confiance YOLO : {max_conf:.0%}"
                            )
                        else:
                            frame_rgb = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
                            live_frame_ph.image(
                                frame_rgb, channels="RGB",
                                caption=f"⏱ {ts} — Frame #{frame_idx}"
                            )
                            live_status_ph.info(f"⏱ {ts} — Aucune anomalie.")

                        # Mise à jour timeline toutes les 10 frames analysées
                        if len(st.session_state.rtsp_rows) % 10 == 0:
                            update_timeline()

                    frame_idx += 1

                cap.release()

            # Fermer le dernier segment ouvert à l'arrêt
            close_rtsp_segment()
            update_timeline()

    # --- Export CSV final ---
    if st.session_state.rtsp_segments:
        st.divider()
        st.markdown("### Rapport final de session")

        import pandas as pd
        seg_export = [
            {k: v for k, v in s.items()
             if k not in ("best_frame_bgr", "best_boxes")}
            for s in st.session_state.rtsp_segments
        ]
        csv = pd.DataFrame(seg_export).to_csv(index=False)
        col_dl1, col_dl2 = st.columns(2)
        col_dl1.download_button(
            "⬇️ Télécharger le rapport (CSV)",
            data=csv,
            file_name="rapport_endoscopie.csv",
            mime="text/csv"
        )
        if col_dl2.button("🗑️ Nouvelle session"):
            for key in ["rtsp_rows", "rtsp_segments", "rtsp_seg_start",
                        "rtsp_seg_end", "rtsp_seg_conf", "rtsp_seg_frame",
                        "rtsp_seg_boxes", "rtsp_seg_n", "rtsp_start_time"]:
                st.session_state[key] = None if "start" in key or "frame" in key \
                    or "end" in key else [] if key in ["rtsp_rows", "rtsp_segments",
                    "rtsp_seg_boxes"] else 0.0 if "conf" in key else 0
            st.rerun()

    if DEMO_MODE:
        st.caption("⚠️ Mode démo : détections simulées (poids introuvables).")


st.divider()
st.markdown(
    """
    <div class="medet-footer">
        medet — Pipeline hybride YOLO (étage 1, local) + EfficientNet (étage 2, cloud) ·
        Usage interne, pas d'utilisation clinique.
    </div>
    """,
    unsafe_allow_html=True,
)
