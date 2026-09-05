# poc_globale/app2.py

## Rôle dans le projet
Interface utilisateur du **POC v2** — version étendue de `app.py` avec support des **vidéos d'endoscopie** en plus des images statiques. Ajoute l'analyse frame par frame, l'affichage en temps réel des détections, un graphique temporel, et l'export CSV du rapport.

---

## Lancement
```bash
cd poc_globale/
streamlit run app2.py
# → http://localhost:8501
```

---

## Différences clés avec `poc/app.py`

| Fonctionnalité | app.py (POC v1) | app2.py (POC v2) |
|---|---|---|
| Images JPG/PNG | ✅ | ✅ |
| Vidéos MP4/AVI | ❌ | ✅ |
| Affichage temps réel | ❌ | ✅ |
| Graphique temporel | ❌ | ✅ |
| Export CSV | ❌ | ✅ |
| Limite upload | 200 MB (défaut) | 10 GB (configuré) |
| Modèle YOLO | yolo_polype_best.pt | best.pt |

---

## Architecture de l'application

```
app2.py
  │
  ├── Sélecteur de mode : [Image] [Vidéo]
  │
  ├── MODE IMAGE (identique à app.py)
  │     ├── Upload JPG/PNG
  │     ├── YOLO → EfficientNet
  │     └── Résultat + boîte annotée
  │
  └── MODE VIDÉO
        ├── Upload MP4/AVI/MOV
        ├── Barre de progression (frame par frame)
        ├── Affichage en temps réel des segments détectés
        ├── Graphique temporel de présence du polype
        ├── Tableau des segments (début → fin → confiance)
        └── Bouton export CSV
```

---

## Fonctions principales

### `load_models()`
```python
@st.cache_resource
def load_models():
    """
    Charge best.pt (YOLO) et efficientnet_etage2.pt.
    Utilise best.pt au lieu de yolo_polype_best.pt (modèle plus récent).
    """
    yolo = YOLO("weights/best.pt")
    
    effnet = models.efficientnet_b0()
    effnet.classifier[1] = nn.Linear(effnet.classifier[1].in_features, 4)
    effnet.load_state_dict(torch.load("weights/efficientnet_etage2.pt", map_location="cpu"))
    effnet.eval()
    return yolo, effnet
```

---

### `analyze_video(video_path, yolo_model, effnet_model, progress_bar)`
Fonction principale du mode vidéo.

```python
def analyze_video(video_path, yolo_model, effnet_model, progress_bar):
    """
    Analyse une vidéo frame par frame.
    Retourne : (detections_list, segments_list, timeline_data)
    
    detections_list : liste de toutes les frames avec détection
    segments_list   : liste des segments temporels regroupés
    timeline_data   : données pour le graphique (temps, confiance)
    """
    cap = cv2.VideoCapture(video_path)
    fps = cap.get(cv2.CAP_PROP_FPS)
    total_frames = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
    
    detections = []
    frame_num  = 0
    
    # Placeholder Streamlit pour la mise à jour en temps réel
    live_placeholder = st.empty()
    
    while cap.isOpened():
        ret, frame = cap.read()
        if not ret:
            break
        
        results = yolo_model(frame, verbose=False)
        
        for box in results[0].boxes:
            if float(box.conf) > CONF_THRESHOLD:
                detections.append({
                    "frame":     frame_num,
                    "timestamp": frame_num / fps,
                    "confiance": float(box.conf),
                })
                # Mise à jour en temps réel de l'interface
                live_placeholder.info(
                    f"🔴 Détection à {frame_num/fps:.1f}s — Confiance : {float(box.conf):.1%}"
                )
        
        # Mise à jour de la barre de progression
        progress_bar.progress(frame_num / total_frames)
        frame_num += 1
    
    cap.release()
    segments = group_into_segments(detections, fps)
    return detections, segments
```

---

### `group_into_segments(detections, fps, gap=0.5)`
Regroupe les frames positives consécutives en segments temporels continus.

```python
def group_into_segments(detections, fps, gap=0.5):
    """
    gap : si deux détections sont séparées de moins de `gap` secondes,
          elles appartiennent au même segment.
    Retourne une liste de dicts :
      {"debut_s": float, "fin_s": float, "debut_str": str,
       "fin_str": str, "n_frames": int, "conf_max": float}
    """
```

---

### `plot_timeline(timeline_data, segments, duration)`
```python
def plot_timeline(timeline_data, segments, duration):
    """
    Génère un graphique matplotlib :
    - Axe X : temps en secondes
    - Axe Y : score de confiance YOLO (0 = pas de détection)
    - Zones rouges : segments avec anomalie
    - Ligne orange : seuil de confiance
    """
    fig, ax = plt.subplots(figsize=(14, 3))
    ax.fill_between(times, confs, alpha=0.5, color="red", label="Anomalie")
    ax.axhline(y=CONF_THRESHOLD, color="orange", linestyle="--", label="Seuil")
    for seg in segments:
        ax.axvspan(seg["debut_s"], seg["fin_s"], alpha=0.1, color="red")
    ax.set_xlabel("Temps (secondes)")
    ax.set_ylabel("Confiance")
    ax.set_xlim(0, duration)
    ax.legend()
    return fig
```

---

### `export_csv(detections)`
```python
def export_csv(detections):
    """
    Convertit la liste de détections en CSV téléchargeable via Streamlit.
    Colonnes : frame, timestamp, timestamp_str, confiance
    """
    df = pd.DataFrame(detections)
    df["timestamp_str"] = df["timestamp"].apply(
        lambda t: f"{int(t//60):02d}:{t%60:05.2f}"
    )
    csv_bytes = df.to_csv(index=False).encode("utf-8")
    st.download_button(
        label="📥 Télécharger le rapport CSV",
        data=csv_bytes,
        file_name="rapport_detection.csv",
        mime="text/csv"
    )
```

---

## Interface Streamlit (UI)

### Sélecteur de mode
```python
mode = st.radio("Mode d'analyse", ["🖼️ Image", "🎬 Vidéo"], horizontal=True)
```

### Mode vidéo — affichage résultat
```python
# Tableau des segments
st.subheader(f"✅ {len(segments)} segment(s) détecté(s)")
df_segments = pd.DataFrame(segments)
st.dataframe(df_segments[["debut_str", "fin_str", "n_frames", "conf_max"]])

# Graphique temporel
fig = plot_timeline(timeline_data, segments, duration)
st.pyplot(fig)

# Export
export_csv(detections)
```

---

## Configuration Streamlit (`.streamlit/config.toml`)

```toml
[server]
maxUploadSize = 10240   # 10 Go — pour les vidéos longues
```

Ce fichier est lu automatiquement par Streamlit au démarrage.

---

## Fichiers requis

| Fichier | Requis ? | Description |
|---|---|---|
| `weights/best.pt` | Oui (ou mode démo) | Poids YOLO principal |
| `weights/efficientnet_etage2.pt` | Oui (ou mode démo) | Poids EfficientNet |
| `.streamlit/config.toml` | Oui | Limite upload 10 Go |

---

## Dépendances (`requirements_poc2.txt`)
```
streamlit
torch
torchvision
ultralytics
Pillow
numpy
opencv-python
pandas
matplotlib
```
