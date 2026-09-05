# poc/app.py

## Rôle dans le projet
Interface utilisateur du **POC v1** — application Streamlit permettant d'analyser une image de coloscopie via le pipeline hybride YOLO → EfficientNet. C'est la première démonstration fonctionnelle du projet, limitée aux images statiques.

---

## Lancement
```bash
cd poc/
streamlit run app.py
# → http://localhost:8501
```

---

## Architecture de l'application

```
app.py
  │
  ├── Chargement des modèles (au démarrage, mis en cache)
  │     ├── YOLO  → weights/yolo_polype_best.pt
  │     └── EfficientNet → weights/efficientnet_etage2.pt
  │
  ├── Interface Streamlit
  │     ├── Titre + description
  │     ├── Zone d'upload (JPG, PNG)
  │     └── Affichage résultat
  │
  └── Pipeline d'inférence (déclenché au clic)
        ├── YOLO : détecte une anomalie ?
        │     OUI → EfficientNet : quelle classe ?
        │     NON → "Normal"
        └── Affichage : classe + confiance + boîte sur image
```

---

## Fonctions principales

### `load_models()`
```python
@st.cache_resource
def load_models():
    """
    Charge et met en cache les deux modèles.
    @st.cache_resource : les modèles ne sont chargés qu'une seule fois
    même si l'utilisateur re-uploade une image.
    """
    yolo = YOLO("weights/yolo_polype_best.pt")
    
    efficientnet = models.efficientnet_b0()
    efficientnet.classifier[1] = nn.Linear(
        efficientnet.classifier[1].in_features, 4
    )
    efficientnet.load_state_dict(
        torch.load("weights/efficientnet_etage2.pt", map_location="cpu")
    )
    efficientnet.eval()
    return yolo, efficientnet
```

**Paramètre clé** : `map_location="cpu"` — permet de faire tourner sur machine sans GPU.

---

### `preprocess_image(image)`
```python
def preprocess_image(image: PIL.Image) -> torch.Tensor:
    """
    Prépare une image PIL pour EfficientNet.
    Retourne un tenseur (1, 3, 224, 224).
    """
    transform = transforms.Compose([
        transforms.Resize((224, 224)),
        transforms.ToTensor(),
    ])
    return transform(image).unsqueeze(0)   # Ajoute la dimension batch
```

---

### `run_pipeline(image, yolo_model, effnet_model)`
```python
def run_pipeline(image, yolo_model, effnet_model, conf_threshold=0.5):
    """
    Exécute le pipeline 2 étages sur une image PIL.
    Retourne : (classe_predite, confiance, image_annotée)
    """
    # --- Étage 1 : YOLO ---
    results = yolo_model(image)
    boxes = [b for b in results[0].boxes if float(b.conf) > conf_threshold]

    if not boxes:
        return "normal", 1.0, image   # Pas d'anomalie → Normal

    # Dessine les boîtes sur l'image
    annotated = draw_boxes(image, boxes)

    # --- Étage 2 : EfficientNet ---
    tensor  = preprocess_image(image)
    with torch.no_grad():
        outputs = effnet_model(tensor)
        probs   = torch.softmax(outputs, dim=1)[0]
        pred_idx = probs.argmax().item()

    CLASS_NAMES = ['mauvaise_preparation', 'mici', 'normal', 'polype']
    return CLASS_NAMES[pred_idx], float(probs[pred_idx]), annotated
```

---

### `draw_boxes(image, boxes)`
```python
def draw_boxes(image: PIL.Image, boxes) -> PIL.Image:
    """
    Dessine les boîtes de détection YOLO sur l'image.
    Couleur : rouge. Format boîte : xyxy (coin haut-gauche, coin bas-droit).
    """
    draw = ImageDraw.Draw(image)
    for box in boxes:
        x1, y1, x2, y2 = [int(c) for c in box.xyxy[0]]
        draw.rectangle([x1, y1, x2, y2], outline="red", width=3)
        draw.text((x1, y1-15), f"{float(box.conf):.2f}", fill="red")
    return image
```

---

## Interface Streamlit (UI)

### Upload
```python
uploaded_file = st.file_uploader(
    "Charger une image de coloscopie",
    type=["jpg", "jpeg", "png"]
)
```

### Affichage du résultat
```python
if predicted_class == "polype":
    st.error(f"🔴 POLYPE DÉTECTÉ — Confiance : {confidence:.1%}")
elif predicted_class == "mici":
    st.error(f"🔴 MICI DÉTECTÉE — Confiance : {confidence:.1%}")
elif predicted_class == "mauvaise_preparation":
    st.warning(f"🟡 MAUVAISE PRÉPARATION — Confiance : {confidence:.1%}")
else:
    st.success(f"🟢 NORMAL — Confiance : {confidence:.1%}")

st.image(annotated_image, caption="Résultat de l'analyse", use_column_width=True)
```

**Code couleur UI :**
- 🟢 Vert (`st.success`) → normal
- 🟡 Orange (`st.warning`) → mauvaise préparation
- 🔴 Rouge (`st.error`) → polype ou MICI

---

## Mode démo (sans poids)
Si les fichiers `.pt` sont absents de `weights/`, l'application :
1. Affiche un bandeau rouge `⚠️ Mode démo — Modèles non chargés`
2. Retourne des prédictions simulées aléatoirement
3. Reste utilisable pour la présentation

```python
if not os.path.exists("weights/yolo_polype_best.pt"):
    st.warning("⚠️ Modèles non trouvés — MODE DÉMO activé")
    USE_DEMO_MODE = True
```

---

## Fichiers requis

| Fichier | Requis ? | Description |
|---|---|---|
| `weights/yolo_polype_best.pt` | Oui (ou mode démo) | Poids YOLO étage 1 |
| `weights/efficientnet_etage2.pt` | Oui (ou mode démo) | Poids EfficientNet étage 2 |
| `requirements.txt` | Oui | Dépendances Python |

---

## Dépendances (`requirements.txt`)
```
streamlit
torch
torchvision
ultralytics
Pillow
numpy
```
