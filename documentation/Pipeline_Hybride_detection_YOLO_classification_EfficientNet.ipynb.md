# Pipeline_Hybride_detection_YOLO_classification_EfficientNet.ipynb

## Rôle dans le projet
Notebook qui implémente et valide le **pipeline de production 2 étages** : YOLO détecte d'abord si une anomalie est présente dans l'image, puis EfficientNet la classifie précisément. C'est l'architecture centrale du projet MEDET, à l'origine du POC.

---

## Concept du pipeline hybride

L'idée principale est de **filtrer avec YOLO** avant de classifier, pour deux raisons :
1. **Rapidité** : YOLO est beaucoup plus rapide qu'EfficientNet. Les images normales sont traitées en quelques ms sans passer par le 2ᵉ étage.
2. **Précision** : EfficientNet fine-tuné sur les images filtrées est plus précis qu'un modèle qui reçoit tout indifféremment.

```
Image d'entrée
      │
      ▼
┌──────────────────────────────────┐
│  ÉTAGE 1 — YOLO (détection)      │
│  yolo_polype_best.pt             │
│  Détecte : anomalie présente ?   │
└──────────────────────────────────┘
      │
   OUI ──────────────────────────────▶ ┌──────────────────────────────────┐
   NON ──▶ Résultat : NORMAL ✅         │  ÉTAGE 2 — EfficientNet           │
                                        │  efficientnet_etage2.pt           │
                                        │  Classifie : polype / mici /       │
                                        │  mauvaise_preparation / normal     │
                                        └──────────────────────────────────┘
                                                        │
                                                        ▼
                                              Résultat final + confiance
```

---

## Modèles utilisés

### Étage 1 — YOLO (`yolo_polype_best.pt`)
- Modèle : YOLOv8 (Ultralytics)
- Tâche : détection d'objet (binaire : anomalie / pas anomalie)
- Entrée : image brute (toute taille, YOLO redimensionne automatiquement)
- Sortie : liste de boîtes englobantes avec score de confiance

### Étage 2 — EfficientNet (`efficientnet_etage2.pt`)
- Modèle : EfficientNet-B0 fine-tuné (pré-entraîné ImageNet → fine-tuné sur `deep_polypes`)
- Tâche : classification 4 classes
- Entrée : image redimensionnée 224×224 px
- Sortie : probabilités sur 4 classes → classe avec le score max

---

## Sections du notebook

### 1. Chargement des modèles
```python
from ultralytics import YOLO
import torch
from torchvision import models

# Étage 1
yolo_model = YOLO("yolo_polype_best.pt")

# Étage 2
efficientnet = models.efficientnet_b0()
efficientnet.classifier[1] = nn.Linear(efficientnet.classifier[1].in_features, 4)
efficientnet.load_state_dict(torch.load("efficientnet_etage2.pt"))
efficientnet.eval()
```

---

### 2. Preprocessing pour EfficientNet
```python
transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])
```

---

### 3. Fonction pipeline complète
Logique centrale : appelle YOLO, et seulement si une détection est trouvée, appelle EfficientNet.

```python
def predict_pipeline(img_path, confidence_threshold=0.5):
    # Étage 1 — YOLO
    results = yolo_model(img_path)
    detections = [d for d in results[0].boxes if d.conf > confidence_threshold]

    if len(detections) == 0:
        return "normal", 1.0     # Aucune anomalie → NORMAL
    
    # Étage 2 — EfficientNet
    img = Image.open(img_path).convert("RGB")
    tensor = transform(img).unsqueeze(0)
    with torch.no_grad():
        outputs = efficientnet(tensor)
        probs   = torch.softmax(outputs, dim=1)
        pred    = probs.argmax(dim=1).item()
    
    class_names = ['mauvaise_preparation', 'mici', 'normal', 'polype']
    return class_names[pred], probs[0][pred].item()
```

---

### 4. Évaluation du pipeline sur le test set
Lance le pipeline sur toutes les images du test set et calcule les métriques combinées.

**Métriques mesurées :**
- Accuracy globale du pipeline
- Precision / Recall / F1 par classe
- Temps total d'inférence et temps moyen par image
- Nombre de cas où YOLO détecte vs ne détecte pas

---

### 5. Analyse des cas limites
Analyse des images mal classées pour comprendre les erreurs du pipeline :
- Images où YOLO détecte à tort (faux positifs → charge inutile sur EfficientNet)
- Images où YOLO rate la détection (faux négatifs → classifiées comme "normal" à tort)
- Images où EfficientNet se trompe malgré une bonne détection YOLO

---

### 6. Mesure des temps d'inférence

```python
import time

t_start = time.time()
pred, conf = predict_pipeline(img_path)
t_end = time.time()

print(f"Temps : {(t_end - t_start)*1000:.1f} ms")
```

**Résultats typiques :**
- YOLO seul : ~12–15 ms/image
- YOLO + EfficientNet : ~27–30 ms/image (quand anomalie détectée)
- Images normales (YOLO seul) : ~12–15 ms/image

---

## Seuil de confiance YOLO

Le paramètre `confidence_threshold` contrôle la sensibilité du pipeline :
- **Valeur élevée (0.7+)** : moins de faux positifs, mais risque de rater des polypes subtils
- **Valeur basse (0.3–0.4)** : plus sensible, mais plus d'images passent à EfficientNet inutilement
- **Valeur recommandée** : `0.5` (compromis clinique)

---

## Fichiers requis

| Fichier | Où le trouver |
|---|---|
| `yolo_polype_best.pt` | `poc/weights/` ou `poc_globale/weights/` |
| `efficientnet_etage2.pt` | `poc/weights/` ou `poc_globale/weights/` |
| Dataset test | Google Drive → `deep_polypes/` |

---

## Dépendances
```
torch, torchvision, ultralytics, Pillow, scikit-learn, matplotlib, time
```
