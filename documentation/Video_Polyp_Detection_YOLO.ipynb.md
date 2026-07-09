# Video_Polyp_Detection_YOLO.ipynb

## Rôle dans le projet
Extension du pipeline de détection à l'**analyse de vidéos d'endoscopie** complètes. YOLO analyse chaque frame de la vidéo et identifie les segments temporels contenant des anomalies (polypes), avec timestamps précis. C'est le fondement technique de la fonctionnalité vidéo du POC v2.

---

## Environnement
- **Plateforme** : Google Colab (GPU T4 recommandé)
- **Entrée** : vidéos MP4 / AVI de coloscopie
- **Dataset de test** : HyperKvasir — sous-dossier `polyps/` avec vidéos annotées
  - Source : https://datasets.simula.no/hyper-kvasir/

---

## Flux de traitement

```
Vidéo (.mp4 / .avi)
        │
        ▼
┌──────────────────────────┐
│  OpenCV — Lecture frame  │  Extrait les frames une par une
│  par frame               │  fps × durée = nombre total de frames
└──────────────────────────┘
        │
        ▼
┌──────────────────────────┐
│  YOLO — Inférence        │  Analyse chaque frame
│  yolo_polype_best.pt     │  Retourne : boîtes + score de confiance
└──────────────────────────┘
        │
        ▼
┌──────────────────────────┐
│  Post-processing         │  Calcule les timestamps
│  Agrégation des segments │  Groupe les frames consécutives positives
└──────────────────────────┘
        │
        ▼
Rapport CSV + visualisation temporelle
```

---

## Sections du notebook

### 1. Chargement du modèle YOLO
```python
from ultralytics import YOLO

model = YOLO("yolo_polype_best.pt")
```

---

### 2. Chargement de la vidéo avec OpenCV
```python
import cv2

cap = cv2.VideoCapture("video_colonoscopie.mp4")

fps         = cap.get(cv2.CAP_PROP_FPS)           # Images par seconde
total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
duration    = total_frames / fps                  # Durée totale en secondes

print(f"FPS: {fps}, Frames: {total_frames}, Durée: {duration:.1f}s")
```

---

### 3. Analyse frame par frame

```python
detections = []

frame_num = 0
while cap.isOpened():
    ret, frame = cap.read()
    if not ret:
        break

    # YOLO analyse la frame
    results = model(frame, verbose=False)

    for box in results[0].boxes:
        if box.conf > CONFIDENCE_THRESHOLD:
            timestamp = frame_num / fps
            detections.append({
                "frame":     frame_num,
                "timestamp": timestamp,
                "confiance": float(box.conf),
                "x1": int(box.xyxy[0][0]), "y1": int(box.xyxy[0][1]),
                "x2": int(box.xyxy[0][2]), "y2": int(box.xyxy[0][3]),
            })

    frame_num += 1

cap.release()
```

---

### 4. Agrégation en segments temporels
Les frames positives consécutives sont regroupées en **segments** (début → fin).

```python
def frames_to_segments(detections, fps, gap_tolerance=0.5):
    """
    gap_tolerance : si 2 détections sont séparées de moins de 0.5s,
                    elles sont fusionnées dans le même segment.
    """
    segments = []
    current_start = None
    last_timestamp = None

    for d in sorted(detections, key=lambda x: x["frame"]):
        ts = d["timestamp"]
        if current_start is None:
            current_start = ts
        elif ts - last_timestamp > gap_tolerance:
            segments.append({"debut": current_start, "fin": last_timestamp})
            current_start = ts
        last_timestamp = ts

    if current_start:
        segments.append({"debut": current_start, "fin": last_timestamp})

    return segments
```

**Format de sortie d'un segment :**
```python
{
    "debut":    "00:01:23.4",
    "fin":      "00:01:26.1",
    "duree_s":  2.7,
    "n_frames": 81,
    "conf_max": 0.94
}
```

---

### 5. Export du rapport CSV

```python
import pandas as pd

df = pd.DataFrame(detections)
df["timestamp_str"] = df["timestamp"].apply(
    lambda t: f"{int(t//60):02d}:{int(t%60):02d}.{int((t%1)*10)}"
)
df.to_csv("rapport_detection_video.csv", index=False)
```

**Colonnes du CSV produit :**

| Colonne | Type | Description |
|---|---|---|
| `frame` | int | Numéro de frame dans la vidéo |
| `timestamp` | float | Secondes depuis le début |
| `timestamp_str` | str | Format lisible MM:SS.d |
| `confiance` | float | Score de confiance YOLO (0–1) |
| `x1, y1, x2, y2` | int | Coordonnées de la boîte de détection |

---

### 6. Extraction des frames clés annotées
Pour chaque segment détecté, extrait la frame avec le score de confiance le plus élevé et dessine la boîte YOLO dessus.

```python
def draw_detection(frame, box, conf):
    x1, y1, x2, y2 = box
    cv2.rectangle(frame, (x1, y1), (x2, y2), color=(0, 255, 0), thickness=2)
    cv2.putText(frame, f"Conf: {conf:.2f}", (x1, y1-10),
                cv2.FONT_HERSHEY_SIMPLEX, 0.7, (0, 255, 0), 2)
    return frame
```

---

### 7. Visualisation temporelle

Génère un graphique montrant la **présence/absence de polype** sur toute la durée de la vidéo.

```python
import matplotlib.pyplot as plt

# Axe X = temps (secondes), Axe Y = score de confiance (0 quand pas de détection)
plt.figure(figsize=(14, 4))
plt.fill_between(timeline_seconds, confidence_values, alpha=0.4, color="red")
plt.axhline(y=CONFIDENCE_THRESHOLD, color="orange", linestyle="--", label="Seuil")
plt.xlabel("Temps (secondes)")
plt.ylabel("Confiance YOLO")
plt.title("Présence de polype dans la vidéo")
plt.legend()
plt.show()
```

---

## Paramètres configurables

| Paramètre | Valeur par défaut | Description |
|---|---|---|
| `CONFIDENCE_THRESHOLD` | 0.5 | Seuil de détection YOLO |
| `gap_tolerance` | 0.5s | Intervalle max entre 2 frames pour les fusionner |
| `KEY_FRAME_EVERY` | 30 | Extrait une frame clé toutes les N frames d'un segment |

---

## Performances typiques
- **Vitesse** : ~20–30 frames/seconde sur GPU T4 (Colab)
- Une vidéo de 10 min (~18 000 frames à 30 fps) est traitée en environ 10–15 min

---

## Fichiers produits

| Fichier | Description |
|---|---|
| `rapport_detection_video.csv` | Toutes les détections avec timestamps, frames et scores |
| `frame_XXX_annotated.jpg` | Frames clés avec boîte YOLO dessinée |
| `timeline_detection.png` | Graphique de présence du polype sur la durée |

---

## Dépendances
```
ultralytics, opencv-python, pandas, matplotlib, Pillow, torch
```
