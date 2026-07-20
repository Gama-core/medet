# Backend Requirements — medet

**Statut : implémenté** (voir correspondance avec le code livré, section 8)

---

## 1. Objectif

Développer un backend FastAPI capable de traiter différentes sources d'entrée pour la détection et la classification fine de polypes gastro-intestinaux.

---

## 2. Entrées supportées

| Entrée | Format | Endpoint |
|---|---|---|
| Images | JPG, PNG | `POST /predict/image` |
| Vidéos | MP4, AVI | `POST /predict/video` |
| Webcam | Frame envoyée par le client | `POST /predict/webcam` |
| Flux RTSP | URL RTSP | `POST /predict/stream` |
| Flux HTTP/HTTPS | URL HTTP/HTTPS | `POST /predict/stream` |

---

## 3. Pipeline IA

1. Réception de l'entrée (image, vidéo, frame webcam, ou flux).
2. Détection des polypes avec YOLO (étage 1).
3. Si score YOLO entre 50% et 90% : vérification par EfficientNet (étage 2) que la détection est un vrai polype.
4. Classification du type de polype (`1p`, `1s`, `2`, `3`) — directement si score YOLO > 90%, ou après vérification si 50–90%.
5. Retour des prédictions au format JSON structuré.

**Seuils de décision :**

| Score YOLO | Comportement |
|---|---|
| < 50% | Ignoré |
| 50% – 90% | Vérification (vrai/faux polype) + classification du type |
| > 90% | Classification directe du type |

---

## 4. Endpoints API

| Méthode | Route | Description |
|---|---|---|
| GET | `/health` | État de chargement des modèles |
| POST | `/predict/image` | Analyse d'une image |
| POST | `/predict/video` | Analyse d'une vidéo complète |
| POST | `/predict/webcam` | Analyse d'une frame webcam |
| POST | `/predict/stream` | Analyse d'un flux RTSP/HTTP/HTTPS |

---

## 5. Sortie attendue

Chaque prédiction retourne :

- **Résultat de détection** (`is_polyp` : booléen)
- **Score de confiance** (`confidence`, `yolo_confidence`)
- **Type de polype** (`polyp_type` : `1p` / `1s` / `2` / `3`, ou `null` si non applicable)
- **Boîte englobante** (`bounding_box` : x1, y1, x2, y2)
- **Temps de traitement** (`processing_time_ms`)

Pour `/predict/video` et `/predict/stream`, sortie agrégée : liste des détections par frame, nombre de frames lues/analysées, FPS source, temps de traitement total.

---

## 6. Technologies

- **FastAPI** — framework API
- **PyTorch** — moteur d'inférence des modèles EfficientNet
- **YOLO** (Ultralytics) — détection (étage 1)
- **EfficientNet** (torchvision) — classification binaire et classification du type (étage 2)
- **OpenCV** — lecture vidéo et flux réseau
- **Pillow** — manipulation d'images

---

## 7. Exigences de performance

| Exigence | Statut | Notes |
|---|---|---|
| Support image | ✅ | `/predict/image` |
| Support vidéo | ✅ | `/predict/video`, paramètre `frame_skip` ajustable |
| Support webcam | ✅ (frame par frame) | Le traitement webcam en direct nécessite que le **client** capture et poste les frames — le backend ne peut pas accéder à une webcam physique directement |
| Support RTSP | ✅ (borné dans le temps) | `/predict/stream`, analyse synchrone sur une durée définie (`duration_seconds`) |
| Traitement CPU (sans GPU) | ✅ | Modèles chargés sur `device = "cpu"` ; performance à surveiller en production (voir section 9) |

---

## 8. Correspondance avec le code livré

| Exigence | Fichier(s) |
|---|---|
| Étage 1 — YOLO | `services/detector.py` |
| Étage 2 — EfficientNet (binaire + type) | `services/classifier.py` |
| Logique des seuils | `services/pipeline.py` |
| Traitement vidéo | `services/video_processor.py`, `routers/video.py` |
| Traitement flux réseau | `services/stream_processor.py`, `routers/stream.py` |
| Traitement image / webcam | `routers/image.py`, `routers/webcam.py` |
| Schémas de réponse | `models/schemas.py` |
| Point d'entrée / assemblage | `main.py` |

---

## 9. Limites connues et points ouverts

- **`/predict/stream` est une analyse bornée dans le temps**, pas un flux continu illimité — adapté à un usage API synchrone. Un affichage live continu côté frontend nécessiterait un WebSocket ou un polling répété (non couvert par cette version).
- **Performance CPU non encore benchmarkée en conditions réelles de production** (VPS cible) — `frame_skip` est ajustable pour compenser si nécessaire.
- **Classification fine du type de polype** : le modèle actuel présente un déséquilibre de performance entre classes (`1s` bien reconnu, `1p`/`2`/`3` à renforcer avec davantage de données annotées) — voir suivi séparé sur l'entraînement du modèle.
- **Webcam** : le endpoint `/predict/webcam` traite une frame à la fois envoyée par le client ; il n'y a pas d'accès direct à un périphérique webcam depuis le serveur (limitation architecturale normale pour un backend distant).