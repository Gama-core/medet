# POC — Détection et classification d'anomalies digestives

Preuve de concept (POC) de l'architecture hybride proposée pour le projet
**medet** : détection de polypes du tube digestif par computer vision.

## Contexte

Ce POC démontre le pipeline en deux étages validé avec l'équipe projet :

1. **Étage 1 (local)** — un modèle YOLO léger détecte si une anomalie est
   présente dans l'image. Si rien n'est détecté, le résultat est immédiat
   (`normal`), sans appel réseau.
2. **Étage 2 (cloud)** — si une anomalie est suspectée, l'image est envoyée
   à un modèle EfficientNet (transfer learning) qui classe précisément
   parmi les 4 catégories : `normal`, `polype`, `mici`, `mauvaise_preparation`.

Cette interface Streamlit sert uniquement à **tester et démontrer** ce
pipeline avec l'équipe métier et l'équipe médicale, avant tout
développement de l'application mobile finale (Flutter) et du backend de
production.

## Contenu du dossier

```
poc/
├── app.py              interface Streamlit
├── requirements.txt    dépendances Python
├── weights/
│   ├── yolo_polype_best.pt          poids du modèle YOLO (étage 1)
│   └── efficientnet_etage2.pt       poids du modèle EfficientNet (étage 2)
└── README.md            ce fichier
```

## Installation

```bash
pip install -r requirements.txt
```

## Lancer l'application

```bash
streamlit run app.py
```

Une page s'ouvre automatiquement dans le navigateur à l'adresse
`http://localhost:8501`.

## Utilisation

1. Déposer une image (prise de vue endoscopique/coloscopique).
2. L'application affiche le résultat de l'étage 1 (YOLO) : anomalie
   détectée ou non.
3. Si une anomalie est détectée, l'image est automatiquement envoyée à
   l'étage 2 (EfficientNet), qui affiche la classe précise et le niveau
   de confiance.
4. Le résultat final est affiché en bas de l'écran.

## Mode démo

Si les fichiers de poids (`weights/yolo_polype_best.pt` et
`weights/efficientnet_etage2.pt`) sont absents ou ne se chargent pas,
l'application bascule automatiquement en **mode démo** : un bandeau
orange l'indique clairement, et les prédictions affichées sont simulées.
Cela permet de présenter l'interface même sans modèle entraîné disponible.

## Limites connues (statut actuel)

- Précision mesurée sur le jeu de test interne : 100 % (aucune fausse
  alerte).
- Rappel mesuré : environ 78–80 % (certains polypes ne sont pas encore
  détectés par l'étage 1). C'est l'axe d'amélioration prioritaire avant
  un déploiement plus large — voir la section suivante.

## Prochaines étapes proposées

- **Enrichissement du dataset** par l'équipe médicale (nouvelles images,
  cas difficiles) pour relancer l'entraînement avec une base plus riche.
- **Évaluation des résultats d'inférence** par l'équipe médicale
  (validation ou correction des prédictions), pour constituer une base
  d'exemples en vue d'un futur cycle de reinforcement learning.
- Amélioration du rappel de l'étage 1 (ajustement du seuil de confiance,
  ré-entraînement sur dataset enrichi).
- Développement de l'application mobile (Flutter) et du backend de
  production (FastAPI), une fois le POC validé.

## Avertissement

Ce POC est un outil de test interne. Il n'est pas destiné à un usage
clinique et ne doit pas être utilisé pour une décision médicale réelle.
