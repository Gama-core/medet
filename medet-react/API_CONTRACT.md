# Contrat API attendu par le frontend React

Ce document liste **toutes les hypothèses** faites sur le backend FastAPI
dans `src/lib/api.js`. Comme je n'ai pas le code exact de `routers/`,
j'ai calé le frontend sur ce qui est décrit dans `JOURNAL_SESSION.md` et
sur le comportement de `app2.py`. Si un endpoint ou un champ diffère
côté backend, **`src/lib/api.js` est le seul fichier à modifier** — tous
les composants consomment uniquement les fonctions de ce fichier, jamais
`fetch` directement.

## Réglages envoyés à chaque appel (query params)

| Paramètre | Origine (sidebar) | Description |
|---|---|---|
| `yolo_low` | Seuil minimum | En dessous → ignoré |
| `yolo_high` | Seuil de confiance élevée | Au-dessus → classification directe |
| `frame_skip` | Analyser 1 frame sur N | Vidéo / webcam / flux |
| `min_segment_duration` | Durée minimale d'un segment | Filtre le bruit |

## `GET /health`
Non utilisé activement dans l'UI pour l'instant (prévu pour un futur bandeau de statut backend).

## `POST /predict/image` (multipart: `file`)
**Réponse attendue :**
```json
{
  "detected": true,
  "max_conf": 0.87,
  "polyp_type": "1s",
  "type_conf": 0.76,
  "annotated_image_base64": "data:image/png;base64,...."
}
```
`annotated_image_base64` doit être une **data URL prête à mettre dans un `<img src>`**
(l'image avec les boîtes déjà dessinées côté serveur, comme dans `app2.py`).
Si le backend renvoie plutôt des `boxes: [[x1,y1,x2,y2,conf], ...]` sans image
annotée, il faudra dessiner les boîtes côté frontend sur un `<canvas>` — dites-le
moi et j'ajoute ce rendu.

## `POST /predict/video` (multipart: `file`)
**Réponse attendue :**
```json
{
  "duration_s": 42.5,
  "n_frames_analyzed": 320,
  "rows": [
    { "timestamp_s": 1.2, "detected": true, "max_conf": 0.81, "polyp_type": "1s", "type_conf": 0.7 }
  ],
  "segments": [
    {
      "start_s": 1.0, "end_s": 3.4, "start_ts": "00:01", "end_ts": "00:03",
      "max_conf": 0.9, "polyp_type": "1s", "type_conf": 0.8,
      "n_frames": 12, "best_frame_url": "data:image/png;base64,...."
    }
  ]
}
```
`rows` alimente la timeline (nuage de points), `segments` alimente la liste et
les zones colorées sur la timeline.

**Export CSV :** mêmes paramètres + `?export=csv` → réponse `text/csv` brute
(le frontend la télécharge directement).

## `POST /predict/webcam` (multipart: `frame`, JPEG)
Appelé environ toutes les 400ms depuis le navigateur (frame capturée via
`<canvas>` depuis `getUserMedia`). **Réponse attendue identique à `/predict/image`.**
Le regroupement en segments est fait **côté frontend** (`src/lib/segments.js`),
pas besoin que le backend gère un état de session pour ce mode.

## `POST /predict/stream/*` — ⚠️ à confirmer côté backend
Le flux RTSP ne peut pas être lu par le navigateur : le décodage doit rester
côté serveur (`cv2.VideoCapture(url)`, comme `app2.py`). J'ai supposé un
contrat par **session + polling**, à adapter selon `routers/stream.py` réel :

```
POST /predict/stream/start   { "url": "...", "frame_skip": 5, ... } -> { "session_id": "..." }
GET  /predict/stream/{id}/next -> { "status": "ok"|"ended", "elapsed_s": 12.3,
                                     "detected": true, "max_conf": 0.8,
                                     "polyp_type": "1s", "type_conf": 0.7,
                                     "annotated_image_base64": "..." }
POST /predict/stream/{id}/stop -> { "segments": [...] }
```
Si le backend actuel expose plutôt un seul endpoint bloquant ou un WebSocket,
dites-le moi — j'adapterai `pollStreamSession` en conséquence (WebSocket ou
Server-Sent Events plutôt que polling REST).

## `/records` (historique)
```
GET    /records                -> { "records": [{ "id", "reference_label", "created_at" }, ...] }
GET    /records/{id}           -> { "id", "reference_label", "segments": [...] }
DELETE /records/{id}
POST   /records/{id}/share     -> { "share_token": "..." }
DELETE /records/{id}/share
```

## Ce qu'il reste à faire une fois le contrat confirmé
1. Comparer chaque section ci-dessus au code réel dans `backend/routers/`.
2. Ajuster les noms de champs dans `src/lib/api.js` (un seul endroit).
3. Si `/predict/stream` n'existe pas encore sous cette forme, le mode
   "Flux réseau" affichera une erreur explicite tant que l'endpoint n'est
   pas branché — le reste de l'app (Image / Vidéo / Webcam / Historique)
   fonctionne indépendamment.
