# Mode 4 — Flux réseau (URL) : guide d'utilisation

Ce mode permet d'analyser un flux vidéo **en continu**, en temps réel, à partir d'une URL réseau — sans upload de fichier. C'est le mode conçu pour se connecter directement à la tour d'endoscopie le jour où elle sera branchée sur le réseau.

---

## 1. Ce que le médecin doit faire (usage quotidien)

1. Ouvrir l'app → sélectionner **"🔗 Flux réseau (URL)"**.
2. Coller l'URL du flux dans le champ **"URL du flux"**.
3. Ajuster si besoin :
   - **"Analyser 1 frame sur N"** : plus la valeur est haute, moins ça consomme de CPU (utile sur un VPS sans GPU).
   - **"Tentatives de reconnexion automatique"** : nombre d'essais avant d'abandonner si le flux coupe.
4. Cocher **"▶️ Se connecter et démarrer l'analyse"**.
5. Le flux live s'affiche à gauche, les segments détectés à droite, la timeline en bas.
6. À la fin, télécharger le **rapport CSV** de la session.

**Le médecin n'a besoin d'aucune compétence technique pour cette étape** — coller une URL et cliquer, comme n'importe quel lecteur vidéo en ligne.

---

## 2. Deux types d'URL supportées

| Type | Exemple | Comportement |
|---|---|---|
| **RTSP** (flux live) | `rtsp://192.168.1.50:554/stream1` | Flux continu, sans fin — celui utilisé par une vraie tour d'endoscopie ou caméra IP |
| **HTTP/HTTPS** (fichier vidéo) | `http://serveur/video.mp4` | Lit le fichier une fois ; en pratique le mécanisme de reconnexion du code le relit automatiquement en boucle |

---

## 3. Comment obtenir une URL à tester (pas de vrai matériel branché pour l'instant)

### Option A — Simuler un flux RTSP avec vos propres vidéos (recommandé, réaliste)

**Terminal 1 — lancer le serveur RTSP local (mediamtx) :**
```powershell
cd mediamtx
.\mediamtx.exe
```
Laisser cette fenêtre ouverte.

**Terminal 2 — diffuser une vidéo en boucle vers ce serveur :**
```powershell
ffmpeg -re -stream_loop -1 -i "chemin\vers\video.avi" -an -c:v libx264 -preset ultrafast -tune zerolatency -f rtsp rtsp://localhost:8554/mystream
```
Attendre de voir `frame= ... fps=25 ...` défiler.

**Dans l'app**, coller :
```
rtsp://127.0.0.1:8554/mystream
```
> Utiliser `127.0.0.1` plutôt que `localhost` — plus fiable sous Windows.

### Option B — Servir une vidéo locale en HTTP (plus simple, pas de serveur RTSP requis)

```powershell
cd "chemin\vers\dossier\videos"
python -m http.server 8000
```

**Dans l'app**, coller :
```
http://localhost:8000/nom_de_la_video.avi
```

### Option C — Tester la connexion avec un lien public (validation technique uniquement)
```
https://raw.githubusercontent.com/chthomos/video-media-samples/master/big-buck-bunny-480p-30sec.mp4
```
⚠️ Contenu non médical — sert uniquement à vérifier que la connexion HTTPS fonctionne techniquement, pas à évaluer la détection.

---

## 4. Dépannage

| Symptôme | Cause probable | Solution |
|---|---|---|
| `Connexion impossible après N tentatives` (RTSP) | Transport UDP bloqué localement | Ajouter en haut du fichier : `os.environ["OPENCV_FFMPEG_CAPTURE_OPTIONS"] = "rtsp_transport;tcp"`, redémarrer Streamlit |
| `Connexion impossible` (HTTPS) | FFmpeg embarqué dans OpenCV sans support TLS complet | Télécharger le fichier au préalable avec `requests` puis l'ouvrir en local |
| Le flux RTSP ne se lit pas du tout, même dans VLC | Le flux FFmpeg ne publie pas correctement | Vérifier les logs de la fenêtre `mediamtx` (chercher une ligne `is publishing to path`) |
| Erreur de codec (`vc1` non supporté) | Vidéo source dans un codec non supporté par RTSP | Réencoder à la volée avec `-c:v libx264 -preset ultrafast -tune zerolatency` dans la commande FFmpeg |
| Test rapide indépendant de l'app | — | Ouvrir l'URL dans **VLC** (Média → Ouvrir un flux réseau) pour confirmer que le flux existe avant de blâmer le code Python |

---

## 5. Le jour où la vraie tour d'endoscopie est branchée (usage desktop / VPS)

Aucun changement de code nécessaire côté détection :
1. Obtenir l'adresse IP / URL RTSP de la tour auprès du service biomédical.
2. La coller dans le champ URL de l'app.
3. Démarrer.

Le seul prérequis technique : le serveur qui fait tourner l'app doit être sur le même réseau (ou avoir un accès autorisé) que la tour d'endoscopie.

**Important — ce qui change entre test et production :**

| | Aujourd'hui (test local) | Demain (production) |
|---|---|---|
| Qui émet le flux RTSP ? | Toi, via `mediamtx` + FFmpeg | La tour d'endoscopie elle-même (déjà un serveur RTSP) |
| Ce qu'il faut lancer | `mediamtx` + `ffmpeg` + Streamlit | Seulement Streamlit |
| Ce que fait l'utilisateur | Rien (c'est un test technique) | Coller l'URL fournie par l'IT + cliquer "Démarrer" |

---

## 6. Cas particulier — accès depuis une app mobile (Flutter)

Le Mode 4 est **compatible mobile par conception**, mais pas de la même façon que sur desktop — l'app Flutter ne peut pas exécuter Python/Streamlit ni le pipeline IA elle-même. L'architecture se sépare en deux blocs :

```
[Tour d'endoscopie] --RTSP--> [Backend Python / VPS]  --HLS + API-->  [App Flutter]
                                (YOLO + EfficientNet,                  (lecture vidéo +
                                 mediamtx en passerelle)                affichage résultats)
```

**Côté backend (VPS)** — logique inchangée, avec un ajout :
- se connecte au flux RTSP de la tour (comme aujourd'hui),
- fait tourner YOLO + EfficientNet,
- **`mediamtx` republie automatiquement le même flux en HLS** (`http://serveur:8888/mystream/index.m3u8`) — sans configuration supplémentaire, c'est une fonctionnalité native de mediamtx,
- expose les résultats de détection (label, confiance, segments) via une API/WebSocket à créer.

**Côté app Flutter** :
- lit la vidéo via le package `video_player` (format HLS, nativement supporté),
- affiche les résultats de détection reçus de l'API, en overlay ou à côté de la vidéo.
- **ne fait aucun calcul IA** — tout reste centralisé sur le serveur.

**Point d'attention — latence** : HLS introduit un délai de quelques secondes (acceptable en relecture, à valider pour un usage strictement temps réel pendant l'examen). Pour une latence quasi nulle, `mediamtx` supporte aussi le WebRTC nativement — option à évaluer si la latence HLS pose problème en usage clinique réel.

**Ce point est un chantier d'architecture à part entière** (API à créer, intégration Flutter), à planifier séparément — il ne bloque pas la démo desktop actuelle.

---

*medet — Pipeline hybride YOLO (étage 1, local) + EfficientNet (étage 2, cloud) · Usage interne, pas d'utilisation clinique.*
