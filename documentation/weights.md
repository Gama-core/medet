# weights/ — Fichiers de poids des modèles

Ce document couvre les 3 fichiers de poids présents dans le projet :
- `poc/weights/yolo_polype_best.pt`
- `poc/weights/efficientnet_etage2.pt`
- `poc_globale/weights/best.pt`
- `poc_globale/weights/efficientnet_etage2.pt` *(même fichier que poc/)*

---

## yolo_polype_best.pt

### Rôle
Poids du modèle **YOLO (étage 1)** du pipeline hybride. Utilisé dans `poc/app.py`. Détecte la présence d'une zone suspecte dans l'image avant de la passer à EfficientNet.

### Modèle de base
- Architecture : **YOLOv8** (Ultralytics)
- Tâche : détection d'objet (bounding box)
- Entraîné sur : images de colonoscopie annotées avec boîtes englobantes autour des polypes

### Comment l'utiliser
```python
from ultralytics import YOLO

model = YOLO("weights/yolo_polype_best.pt")
results = model("image.jpg")

for box in results[0].boxes:
    print(f"Confiance: {float(box.conf):.2f}")
    print(f"Boîte: {box.xyxy[0].tolist()}")   # [x1, y1, x2, y2]
```

### Sortie
```python
results[0].boxes        # Liste des détections
results[0].boxes[0].conf      # Score de confiance (0.0 → 1.0)
results[0].boxes[0].xyxy[0]   # Coordonnées [x1, y1, x2, y2]
```

### Seuil de confiance recommandé
`0.5` — équilibre entre sensibilité et spécificité dans un contexte clinique.

---

## best.pt

### Rôle
Poids YOLO **plus récents** utilisés dans `poc_globale/app2.py`. Version améliorée de `yolo_polype_best.pt` après ré-entraînement ou fine-tuning supplémentaire.

### Utilisation
Identique à `yolo_polype_best.pt` :
```python
model = YOLO("weights/best.pt")
```

### Différence avec `yolo_polype_best.pt`
`best.pt` est le fichier généré automatiquement par Ultralytics à la fin de l'entraînement (`runs/detect/train/weights/best.pt`). Il correspond aux poids du moment où la performance de validation était maximale.

---

## efficientnet_etage2.pt

### Rôle
Poids du modèle **EfficientNet-B0 fine-tuné (étage 2)** du pipeline hybride. Classifie une image en 4 catégories après qu'une anomalie ait été détectée par YOLO.

### Modèle de base
- Architecture : **EfficientNet-B0** (torchvision)
- Pré-entraîné sur : ImageNet (transfer learning)
- Fine-tuné sur : dataset `deep_polypes` (4 classes)
- Modification de la tête : `classifier[1]` → `Linear(1280, 4)`

### Comment le charger
```python
import torch
from torchvision import models
import torch.nn as nn

# Recréer l'architecture
model = models.efficientnet_b0()
model.classifier[1] = nn.Linear(model.classifier[1].in_features, 4)

# Charger les poids
model.load_state_dict(
    torch.load("weights/efficientnet_etage2.pt", map_location="cpu")
)
model.eval()
```

> ⚠️ **Important** : il faut **recréer la même architecture** avant de charger les poids. PyTorch sauvegarde les poids mais pas l'architecture.

### Comment l'utiliser pour une prédiction
```python
from torchvision import transforms
from PIL import Image

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

img = Image.open("image.jpg").convert("RGB")
tensor = transform(img).unsqueeze(0)   # (1, 3, 224, 224)

with torch.no_grad():
    outputs = model(tensor)
    probs   = torch.softmax(outputs, dim=1)[0]
    pred    = probs.argmax().item()

CLASS_NAMES = ['mauvaise_preparation', 'mici', 'normal', 'polype']
print(f"Prédiction : {CLASS_NAMES[pred]} ({float(probs[pred]):.1%})")
```

### Classes de sortie
| Index | Classe | Description |
|---|---|---|
| 0 | `mauvaise_preparation` | Préparation intestinale insuffisante |
| 1 | `mici` | Maladie Inflammatoire Chronique de l'Intestin |
| 2 | `normal` | Muqueuse saine |
| 3 | `polype` | Polype détecté |

### Performances sur le test set
- Accuracy : **96.55%**
- F1 Macro : 96.85%
- Temps moyen : 14.64 ms/image

---

## Résumé

| Fichier | Étage | Utilisé dans | Tâche |
|---|---|---|---|
| `yolo_polype_best.pt` | 1 | `poc/app.py` | Détection (binaire) |
| `best.pt` | 1 | `poc_globale/app2.py` | Détection (binaire) |
| `efficientnet_etage2.pt` | 2 | `poc/app.py` + `poc_globale/app2.py` | Classification (4 classes) |

---

## Note sur le stockage Git
Les fichiers `.pt` sont lourds (plusieurs centaines de Mo) et ne doivent **pas** être commités directement dans Git. Ils sont exclus via `.gitignore`. Pour les distribuer, utiliser **Google Drive**, **HuggingFace Hub**, ou un stockage objet (S3, GCS).
