# medet — Backend FastAPI

Backend de détection et classification fine des polypes (pipeline hybride YOLO + EfficientNet), structuré en architecture modulaire (routers / services / models / utils).

---

## 1. Structure du projet

```
backend/
├── main.py                  # Point d'entrée — assemble l'app, charge les modèles au démarrage
│
├── routers/                 # Couche API — validation d'entrée + appel aux services
│   ├── image.py             # POST /predict/image
│   ├── video.py             # POST /predict/video
│   ├── webcam.py            # POST /predict/webcam
│   └── stream.py            # POST /predict/stream
│
├── services/                # Logique métier
│   ├── detector.py          # Étage 1 — YOLO (chargement + détection)
│   ├── classifier.py        # Étage 2 — EfficientNet binaire + type de polype
│   ├── pipeline.py          # Orchestre detector + classifier selon les seuils 50%/90%
│   ├── video_processor.py   # Boucle générique de lecture/analyse frame par frame
│   └── stream_processor.py  # Connexion + analyse d'un flux RTSP/HTTP/HTTPS
│
├── models/
│   └── schemas.py           # Modèles Pydantic (requêtes et réponses)
│
├── utils/
│   ├── transforms.py        # Preprocessing image partagé (resize, normalisation)
│   ├── draw.py               # Dessin de boîte englobante (debug / usage futur)
│   └── helpers.py            # Constantes (seuils, classes, chemins) + validation d'upload
│
└── weights/                 # Poids des 3 modèles (non versionnés — voir weights/README.md)
```

---

## 2. Installation

```bash
python3 -m venv venv
source venv/bin/activate        # Windows : venv\Scripts\activate
pip install -r requirements.txt
```

Place les 3 fichiers de poids dans `weights/` (voir `weights/README.md` pour le détail des noms attendus).

---

## 3. Lancer le serveur

```bash
uvicorn main:app --reload --port 8000
```

Interface interactive (Swagger) : `http://localhost:8000/docs`

---

## 4. Pipeline de décision

| Score YOLO | Comportement |
|---|---|
| **< 50%** | Détection ignorée |
| **50% – 90%** | EfficientNet (binaire) vérifie si c'est un vrai polype, puis classifie le type si oui |
| **> 90%** | Classification du type directement, sans vérification binaire |

Types de polypes retournés : `1p` (pédiculé), `1s` (sessile), `2` (lésion plane), `3` (lésion ulcérée).

---

## 5. Endpoints

### `GET /health`
Vérifie l'état de chargement des 3 modèles.

### `POST /predict/image`
Upload d'une image (`multipart/form-data`, champ `file`). Retourne une `PredictionResponse` (voir section 6).

### `POST /predict/video`
Upload d'une vidéo (`multipart/form-data`, champ `file`), paramètre optionnel `frame_skip` (défaut `5`). Analyse la vidéo en entier, frame par frame, retourne un résumé (`VideoResult`) avec la liste des détections.

### `POST /predict/webcam`
Identique à `/predict/image` — endpoint dédié pour une frame envoyée par le client depuis sa webcam locale, postée à intervalle régulier.

### `POST /predict/stream`
Corps JSON :
```json
{
  "url": "rtsp://192.168.1.50:554/stream1",
  "duration_seconds": 30,
  "frame_skip": 5
}
```
Se connecte au flux et l'analyse pendant `duration_seconds` secondes maximum. Retourne un `StreamResult`.

> ⚠️ Analyse **bornée dans le temps** (adaptée à un usage API synchrone classique). Pour un affichage live continu côté client, prévoir un WebSocket ou des appels répétés sur des segments courts.

---

## 6. Format de réponse (`PredictionResponse`)

```json
{
  "is_polyp": true,
  "polyp_type": "1s",
  "polyp_label": "Polype sessile (1s)",
  "confidence": 0.87,
  "all_probabilities": {"1p": 0.05, "1s": 0.87, "2": 0.06, "3": 0.02},
  "yolo_confidence": 0.76,
  "yolo_zone": "uncertain",
  "bounding_box": {"x1": 120, "y1": 80, "x2": 340, "y2": 290},
  "action": "verified_and_classified",
  "processing_time_ms": 142.3
}
```

---

## 7. Points d'attention connus

- **CPU only** : le déploiement cible n'a pas de GPU — surveiller `processing_time_ms` en production, ajuster `frame_skip` si nécessaire.
- **Déséquilibre du dataset de classification fine** : `1s` est largement mieux reconnu que `1p`, `2` et `3` (voir historique d'entraînement) — le recall sur ces 3 classes reste à améliorer avec plus de données annotées.
- **Transport RTSP forcé en TCP** (`OPENCV_FFMPEG_CAPTURE_OPTIONS`) — nécessaire pour éviter les erreurs `Unsupported Transport` observées en test avec certains flux.
