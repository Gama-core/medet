# full_classification_metrics.csv

## Rôle dans le projet
Fichier de référence central — contient les **métriques complètes** de tous les modèles Deep Learning évalués sur le test set du dataset `deep_polypes`. Ce fichier est produit par `Model_Comparison.ipynb` et consommé par les analyses comparatives, le POC, et les notebooks de suivi.

---

## Produit par
`notebooks/Model_Comparison.ipynb` — section *Performance Evaluation on the Test Set*

## Utilisé par
- Analyses comparatives (tableaux, graphiques)
- `VLM_vs_DL_Comparison_Colonoscopy.ipynb` (comparaison avec le VLM)
- Présentations et rapports

---

## Structure du fichier

### Colonnes — Métriques globales

| Colonne | Type | Description |
|---|---|---|
| `Model` | string | Nom de l'architecture (ConvNeXt, ViT, etc.) |
| `Accuracy` | float | Taux de classification correct global sur le test set |
| `Temps total (s)` | float | Durée totale d'inférence sur tout le test set (secondes) |
| `Temps moyen (ms/image)` | float | Temps moyen d'inférence par image (millisecondes) |

### Colonnes — Métriques par classe

Pour chaque classe (`mauvaise_preparation`, `mici`, `normal`, `polype`) :

| Colonne | Type | Description |
|---|---|---|
| `Precision_[classe]` | float | TP / (TP + FP) — parmi les prédictions de cette classe, combien sont correctes |
| `Recall_[classe]` | float | TP / (TP + FN) — parmi les vraies images de cette classe, combien sont détectées |
| `F1_[classe]` | float | Moyenne harmonique Precision/Recall pour cette classe |

### Colonnes — Métriques macro et weighted

| Colonne | Description |
|---|---|
| `Precision (macro)` | Moyenne simple des Precision de chaque classe |
| `Recall (macro)` | Moyenne simple des Recall de chaque classe |
| `F1 (macro)` | Moyenne simple des F1 de chaque classe |
| `Precision (weighted)` | Moyenne pondérée par le nombre d'images de chaque classe |
| `Recall (weighted)` | Moyenne pondérée par le nombre d'images de chaque classe |
| `F1 (weighted)` | Moyenne pondérée par le nombre d'images de chaque classe |

---

## Contenu actuel (5 modèles)

| Model | Accuracy | F1 (macro) | F1 (weighted) | Temps moy. (ms) |
|---|---|---|---|---|
| ConvNeXt | **0.9770** | 0.9716 | 0.9771 | 15.34 |
| ViT | **0.9770** | 0.9713 | 0.9770 | 20.33 |
| EfficientNet | 0.9655 | 0.9626 | 0.9658 | 14.64 |
| Swin Transformer | 0.9655 | 0.9689 | 0.9653 | **12.39** |
| ResNet50 | 0.9540 | 0.9561 | 0.9543 | 15.23 |

---

## Comment interpréter les métriques

### Precision vs Recall — trade-off médical
Dans un contexte clinique de détection de polypes :
- **Recall (sensibilité) élevé** est prioritaire : mieux vaut une fausse alarme qu'un polype manqué
- **Precision** limite les fausses alarmes et la charge de travail du médecin

### Macro vs Weighted
- **Macro** : traite toutes les classes à égalité — utile si les classes sont déséquilibrées
- **Weighted** : tient compte du nombre d'images par classe — plus proche de l'accuracy réelle

### F1-Score
Synthèse équilibrée entre Precision et Recall. **F1 = 2 × (P × R) / (P + R)**

---

## Exemple de lecture
```
ConvNeXt :
  Precision_polype = 1.0000  → Toutes les prédictions "polype" étaient correctes
  Recall_polype    = 0.9286  → 92.86% des vrais polypes ont été détectés
  F1_polype        = 0.9630  → Bon équilibre Precision/Recall sur la classe polype
```

---

## Comment régénérer ce fichier
Relancer `Model_Comparison.ipynb` dans Google Colab avec le dataset `deep_polypes` disponible. Le fichier est exporté automatiquement à la fin du notebook.
