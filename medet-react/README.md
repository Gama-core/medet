# medet — Interface React

Interface web React (Vite) reproduisant les 4 modes de `app2.py` (Streamlit),
branchée sur le backend FastAPI existant.

## Démarrage

```bash
npm install
cp .env.example .env      # ajuster VITE_API_BASE_URL si besoin
npm run dev
```

Par défaut, le frontend appelle `http://localhost:8000` (votre backend FastAPI).
Assurez-vous que le backend local tourne et a été redémarré après toute
modification de `backend/routers/stream.py`.

Si vous utilisez le mode Flux réseau avec un flux RTSP local, le backend doit
être sur la même machine que le flux. Dans ce cas, utilisez une URL locale comme :

```text
rtsp://localhost:8554/mystream
```

ou bien :

```text
rtsp://127.0.0.1:8554/mystream
```

Si le backend est sur un autre ordinateur ou serveur, `localhost`/`127.0.0.1`
ne fonctionnera pas pour le flux RTSP. Utilisez alors l'adresse IP accessible
depuis le serveur, par exemple :

```text
rtsp://192.168.x.y:8554/mystream
```

CORS doit être activé côté backend pour l'origine `http://localhost:5173`
(ou votre domaine de prod) :

```python
# backend/main.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", "https://votre-domaine.fr"],
    allow_methods=["*"],
    allow_headers=["*"],
)
```

## Ce qui est implémenté

| Mode | Description |
|---|---|
| 🖼️ Image | Upload, appel `/predict/image`, image annotée + résultat |
| 🎬 Vidéo | Upload, `/predict/video`, timeline interactive cliquable (segments colorés par type), export CSV, lecteur vidéo qui se positionne sur le segment sélectionné |
| 📷 Webcam | Capture caméra du navigateur, envoi image par image à `/predict/webcam`, regroupement en segments **côté frontend** |
| 🔗 Flux réseau | Saisie d'une URL RTSP/HTTP, session côté backend (polling), segments live |
| 🗂️ Historique | Liste/détail des examens via `/records`, partage par lien |

Les seuils YOLO (bas/haut), le sous-échantillonnage vidéo et la durée
minimale de segment sont réglables dans la barre latérale, comme dans
`app2.py`, et transmis à chaque appel API.

## ⚠️ Avant de considérer ça "branché"

Le contrat exact des réponses backend (noms de champs, format de l'image
annotée, etc.) est une **hypothèse documentée dans `API_CONTRACT.md`** —
je n'avais pas le code de `backend/routers/` sous la main. Le mode le plus
incertain est **Flux réseau** (RTSP), qui suppose un système de session +
polling à confirmer/adapter selon `routers/stream.py`.

Étapes suivantes recommandées :
1. Lancer `npm run dev`, tester le mode Image en premier (le plus simple)
   face à votre vrai backend, et comparer aux hypothèses de `API_CONTRACT.md`.
2. Ajuster `src/lib/api.js` si les champs diffèrent (un seul fichier à toucher).
3. Une fois Image/Vidéo/Webcam validés, on affine le mode Flux réseau ensemble.

## Design

Palette et typographie reprises de `app2.py` (navy `#0B2545` / teal `#0F8B8D`,
IBM Plex Sans/Mono) pour garder une identité visuelle cohérente entre les
deux interfaces pendant la transition.

## Prochaine étape naturelle

Une fois cette version React validée contre le vrai backend, on pourra
répliquer les mêmes écrans côté Flutter (mobile) en réutilisant le même
contrat d'API — dites-moi quand vous voulez enchaîner.
