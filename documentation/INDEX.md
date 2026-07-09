# documentation/ — Index

Dossier de documentation technique du projet **MEDET**.  
Chaque fichier `.md` documente un fichier de code spécifique : son rôle, ses fonctions, sa logique interne, et son utilisation.

---

## 📁 Arborescence

```
documentation/
│
├── INDEX.md                                              ← ce fichier
│
├── Notebooks
│   ├── deep_polypes.ipynb.md
│   ├── Model_Comparison.ipynb.md
│   ├── Pipeline_Hybride_detection_YOLO_classification_EfficientNet.ipynb.md
│   └── Video_Polyp_Detection_YOLO.ipynb.md
│
├── Applications POC
│   ├── poc_app.py.md
│   └── poc_globale_app2.py.md
│
├── Architecture
│   └── architecture_objectif_global.mmd.md
│
└── Données & Modèles
    ├── full_classification_metrics.csv.md
    └── weights.md
```

---

## 📄 Description rapide de chaque fichier

| Fichier de doc | Fichier documenté | Description courte |
|---|---|---|
| `deep_polypes.ipynb.md` | `notebooks/deep_polypes.ipynb` | Exploration et chargement du dataset |
| `Model_Comparison.ipynb.md` | `notebooks/Model_Comparison.ipynb` | Entraînement et comparaison de 5 modèles DL |
| `Pipeline_Hybride_...ipynb.md` | `notebooks/Pipeline_Hybride_....ipynb` | Pipeline 2 étages YOLO → EfficientNet |
| `Video_Polyp_Detection_YOLO.ipynb.md` | `notebooks/Video_Polyp_Detection_YOLO.ipynb` | Détection sur vidéo frame par frame |
| `poc_app.py.md` | `poc/app.py` | Interface Streamlit images (POC v1) |
| `poc_globale_app2.py.md` | `poc_globale/app2.py` | Interface Streamlit images + vidéos (POC v2) |
| `architecture_objectif_global.mmd.md` | `architecture/architecture_objectif_global.mmd` | Schéma Mermaid de l'architecture globale |
| `full_classification_metrics.csv.md` | `full_classification_metrics.csv` | Métriques complètes des 5 modèles |
| `weights.md` | `poc/weights/*.pt` + `poc_globale/weights/*.pt` | Poids YOLO et EfficientNet |
