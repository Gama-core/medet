# POC Vidéo — Détection de polypes sur images et vidéos

Interface de démonstration étendue du pipeline hybride **medet**,
permettant l'analyse aussi bien d'**images statiques** que de
**vidéos d'endoscopie** (coloscopie, endoscopie digestive).

Développée suite à la demande de l'équipe médicale lors de la réunion
de présentation du POC initial.

## Contenu du dossier

```
poc_video/
├── app2.py                  interface Streamlit (images + vidéos)
├── requirements.txt         dépendances Python
├── weights/
│   ├── yolo_polype_best.pt  poids YOLO (étage 1, détection locale)
│   └── efficientnet_etage2.pt  poids EfficientNet (étage 2, cloud)
├── .streamlit/
│   └── config.toml          config Streamlit (limite upload étendue)
└── README.md
```

## Fonctionnalités

### Mode image
- Upload d'une image (JPG, PNG).
- Étage 1 (YOLO) : détection locale de présence d'anomalie.
- Étage 2 (EfficientNet) : classification précise si anomalie détectée
  (`normal`, `polype`, `mici`, `mauvaise_preparation`).
- Résultat final avec code couleur.

### Mode vidéo
- Upload de vidéos d'endoscopie (AVI, MP4, MOV), sans limite de taille.
- Analyse frame par frame avec YOLO.
- **Affichage en temps réel** des segments détectés au fur et à mesure
  de l'analyse (pas besoin d'attendre la fin de la vidéo).
- Pour chaque segment détecté :
  - Timestamp précis (début → fin)
  - Numéro de frame exacte
  - Frame clé avec boîte de localisation du polype dessinée
  - Score de confiance
- Graphique de présence du polype sur toute la durée de la vidéo.
- Export du rapport de détection en CSV (timestamps, frames, confiances).

## Dataset utilisé pour les tests

**HyperKvasir** (vidéos de colonoscopie annotées par des
gastro-entérologues) — sous-dossier `polyps/`.
Source : https://datasets.simula.no/hyper-kvasir/

## Installation et lancement

```bash
pip install -r requirements.txt
streamlit run app2.py
```

## Configuration de la limite d'upload

Le fichier `.streamlit/config.toml` étend la limite d'upload à 10 Go :

```toml
[server]
maxUploadSize = 10240
```

## Mode démo

Si les poids (`weights/`) sont absents, l'application bascule
automatiquement en mode démo (prédictions simulées) avec un avertissement
visuel — permettant de présenter l'interface sans modèle disponible.

## Avertissement

Ce POC est un outil de test interne. Il n'est pas destiné à un usage
clinique et ne doit pas être utilisé pour une décision médicale réelle.
