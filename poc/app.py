"""
Pipeline hybride de détection de polypes — démo Streamlit
==========================================================

Étage 1 (local)  : YOLO nano -> détecte si une anomalie est présente.
Étage 2 (cloud)  : si l'étage 1 détecte quelque chose, EfficientNet
                   tranche entre les 4 classes (normal, polype, mici,
                   mauvaise_preparation).

Pour lancer l'application :
    pip install streamlit ultralytics torch torchvision pillow
    streamlit run app.py

Si les poids entraînés (YOLO_WEIGHTS_PATH / EFFICIENTNET_WEIGHTS_PATH)
ne sont pas trouvés, l'application bascule automatiquement en MODE DÉMO
(prédictions simulées) afin de pouvoir présenter l'interface au manager
même avant la fin de l'entraînement final.
"""

import os
import random
import time

import streamlit as st
from PIL import Image

# -----------------------------------------------------------------
# Configuration
# -----------------------------------------------------------------

YOLO_WEIGHTS_PATH = "weights/yolo_polype_best.pt"
EFFICIENTNET_WEIGHTS_PATH = "weights/efficientnet_etage2.pt"

CLASS_NAMES = ["mauvaise_preparation", "mici", "normal", "polype"]

YOLO_CONF_THRESHOLD = 0.25

st.set_page_config(
    page_title="Détection de polypes — Pipeline hybride",
    page_icon="🩺",
    layout="centered",
)

# -----------------------------------------------------------------
# Chargement des modèles (mis en cache pour ne pas recharger à chaque clic)
# -----------------------------------------------------------------


@st.cache_resource(show_spinner=False)
def load_models():
    """
    Tente de charger les vrais modèles. Si les fichiers de poids sont
    absents ou si les librairies ne sont pas disponibles, retourne
    (None, None) -> l'application passera en mode démo.
    """
    yolo_model = None
    efficientnet_model = None

    try:
        from ultralytics import YOLO

        if os.path.exists(YOLO_WEIGHTS_PATH):
            yolo_model = YOLO(YOLO_WEIGHTS_PATH)
    except Exception:
        yolo_model = None

    try:
        import torch
        import torch.nn as nn
        from torchvision import models

        if os.path.exists(EFFICIENTNET_WEIGHTS_PATH):
            eff = models.efficientnet_b0(weights=None)
            eff.classifier[1] = nn.Linear(eff.classifier[1].in_features, len(CLASS_NAMES))
            eff.load_state_dict(torch.load(EFFICIENTNET_WEIGHTS_PATH, map_location="cpu"))
            eff.eval()
            efficientnet_model = eff
    except Exception:
        efficientnet_model = None

    return yolo_model, efficientnet_model


yolo_model, efficientnet_model = load_models()
DEMO_MODE = (yolo_model is None) or (efficientnet_model is None)


# -----------------------------------------------------------------
# Fonctions de prédiction (réelles ou simulées)
# -----------------------------------------------------------------


def predict_stage1(image: Image.Image):
    """Étage 1 — YOLO. Retourne (detected: bool, n_boxes: int)."""
    if DEMO_MODE:
        # Simulation : ~55% de chances de détecter une anomalie,
        # pour montrer les deux chemins possibles à la démo.
        time.sleep(0.5)
        detected = random.random() < 0.55
        return detected, (1 if detected else 0)

    image.save("_tmp_input.jpg")
    result = yolo_model.predict("_tmp_input.jpg", conf=YOLO_CONF_THRESHOLD, verbose=False)[0]
    n_boxes = len(result.boxes)
    return n_boxes > 0, n_boxes


def predict_stage2(image: Image.Image):
    """Étage 2 — EfficientNet. Retourne (classe: str, confiance: float)."""
    if DEMO_MODE:
        time.sleep(0.8)
        candidate_classes = ["polype", "mici", "mauvaise_preparation"]
        cls = random.choice(candidate_classes)
        confidence = random.uniform(0.75, 0.98)
        return cls, confidence

    import torch
    from torchvision import transforms

    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
    ])
    img_tensor = transform(image.convert("RGB")).unsqueeze(0)

    with torch.no_grad():
        outputs = efficientnet_model(img_tensor)
        probs = torch.softmax(outputs, dim=1)
        confidence, pred_idx = torch.max(probs, dim=1)

    return CLASS_NAMES[pred_idx.item()], confidence.item()


# -----------------------------------------------------------------
# Interface
# -----------------------------------------------------------------

st.title("🩺 Détection et classification de polypes")
st.caption("Architecture hybride : Étage 1 (YOLO, local) → Étage 2 (EfficientNet, cloud)")

if DEMO_MODE:
    st.warning(
        "⚠️ **Mode démo actif** — les poids entraînés n'ont pas été trouvés "
        f"(`{YOLO_WEIGHTS_PATH}`, `{EFFICIENTNET_WEIGHTS_PATH}`). "
        "Les prédictions ci-dessous sont **simulées**, uniquement pour présenter "
        "l'interface et le déroulé du pipeline. Place les vrais fichiers `.pt` dans "
        "le dossier `weights/` pour passer en mode réel.",
        icon="⚠️",
    )

st.divider()

uploaded_file = st.file_uploader(
    "Dépose une image (endoscopie / coloscopie)",
    type=["jpg", "jpeg", "png"],
)

if uploaded_file is not None:
    image = Image.open(uploaded_file).convert("RGB")

    col1, col2 = st.columns([1, 1])
    with col1:
        st.image(image, caption="Image envoyée", use_column_width=True)

    with col2:
        st.markdown("### Déroulé du pipeline")

        # --- Étage 1 ---
        with st.spinner("Étage 1 — analyse locale (YOLO)..."):
            detected, n_boxes = predict_stage1(image)

        if detected:
            st.success(f"**Étage 1 (YOLO)** : anomalie détectée ({n_boxes} zone(s) suspecte(s))")
        else:
            st.info("**Étage 1 (YOLO)** : aucune anomalie détectée")

        # --- Étage 2, seulement si nécessaire ---
        if detected:
            st.markdown("→ *Image envoyée à l'étage 2 (cloud)*")
            with st.spinner("Étage 2 — classification précise (EfficientNet)..."):
                cloud_class, cloud_confidence = predict_stage2(image)

            st.success(
                f"**Étage 2 (EfficientNet)** : **{cloud_class.upper()}** "
                f"(confiance : {cloud_confidence:.0%})"
            )
            final_class = cloud_class
        else:
            st.markdown("→ *Pas d'appel cloud — économie de ressources*")
            final_class = "normal"

    st.divider()

    # --- Résultat final mis en avant ---
    color_map = {
        "normal": "🟢",
        "polype": "🟠",
        "mici": "🟠",
        "mauvaise_preparation": "🟡",
    }
    emoji = color_map.get(final_class, "⚪")
    st.markdown(f"## Résultat final : {emoji} **{final_class.upper()}**")

else:
    st.info("👆 Dépose une image ci-dessus pour lancer l'analyse.")

st.divider()
st.caption(
    "Démo interne — architecture hybride proposée pour limiter les appels au "
    "modèle cloud (EfficientNet) aux seuls cas où une anomalie est suspectée "
    "localement par YOLO."
)
