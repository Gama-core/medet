# Model_Comparison.ipynb

## Rôle dans le projet
Notebook central de comparaison : entraîne **5 architectures Deep Learning** sur le dataset de coloscopie, les évalue sur un test set commun, puis génère un tableau comparatif complet de toutes les métriques. C'est le notebook qui produit le fichier `full_classification_metrics.csv` utilisé par les autres composants du projet.

---

## Environnement
- **Plateforme** : Google Colab (GPU T4 recommandé)
- **Dataset requis** : `deep_polypes/` sur Google Drive — 4 dossiers (une classe par dossier)
- **Classes** : `mauvaise_preparation`, `mici`, `normal`, `polype`

---

## Structure du notebook (section par section)

### 1. Dataset Exploration
Monte Google Drive et charge le dataset avec `ImageFolder` de torchvision.

```python
from google.colab import drive
drive.mount('/content/drive')

data_path = "/content/drive/MyDrive/deep_polypes"
dataset = datasets.ImageFolder(root=data_path, transform=transform)
```

**Transform appliqué à toutes les images :**
```python
transforms.Compose([
    transforms.Resize((224, 224)),   # Redimensionne à 224×224 px
    transforms.ToTensor(),           # Convertit en tenseur [0,1]
])
```

---

### 2. Dataset Splitting
Divise aléatoirement le dataset en 3 sous-ensembles avec `random_split`.

| Sous-ensemble | Proportion | Usage |
|---|---|---|
| Train | 70% | Entraînement des poids |
| Validation | 15% | Suivi du loss pendant l'entraînement |
| Test | 15% | Évaluation finale (métriques officielles) |

```python
train_size = int(0.7 * len(dataset))
val_size   = int(0.15 * len(dataset))
test_size  = len(dataset) - train_size - val_size
```

**DataLoaders** : `batch_size=32`, `shuffle=True` sur le train uniquement.

---

### 3. Model Selection and Initialization
Initialise les 5 modèles pré-entraînés sur ImageNet, tous adaptés à 4 classes de sortie en remplaçant leur couche de classification finale.

| Modèle | Modification de la tête |
|---|---|
| EfficientNet-B0 | `classifier[1]` → `Linear(in_features, 4)` |
| ResNet50 | `fc` → `Linear(in_features, 4)` |
| ConvNeXt-Tiny | `classifier[2]` → `Linear(in_features, 4)` |
| ViT-B/16 | `heads.head` → `Linear(in_features, 4)` |
| Swin-T | `head` → `Linear(in_features, 4)` |

Tous les modèles sont chargés avec `weights="IMAGENET1K_V1"` (transfer learning).

---

### 4. Fonction `train_model()`
Entraîne un modèle pendant N époques. Logique commune à tous les modèles.

```python
def train_model(model, train_loader, val_loader, name, epochs=5):
```

**Paramètres d'entraînement :**
- Optimiseur : `AdamW` avec `lr=1e-4`
- Loss : `CrossEntropyLoss`
- Époque : 5 (configurable)
- Affiche la loss train à chaque époque

**Flux par batch :**
```
zero_grad → forward → loss → backward → optimizer.step
```

---

### 5. Training Deep Learning Models
Boucle sur le dictionnaire `models_dict` et appelle `train_model` pour chaque architecture. Les modèles entraînés sont stockés dans `trained_models`.

---

### 6. Fonction `evaluate_model()`
Évalue un modèle entraîné sur le test set. Passe en mode `eval()`, désactive les gradients.

```python
def evaluate_model(model, loader, name):
    model.eval()
    with torch.no_grad():
        preds = torch.argmax(outputs, dim=1)
    print(classification_report(..., target_names=dataset.classes))
    return accuracy_score(y_true, y_pred)
```

Affiche le `classification_report` complet (precision, recall, F1 par classe).

---

### 7. Performance Evaluation on the Test Set
Lance `evaluate_model` pour chaque modèle et stocke les accuracies dans `results`.

---

### 8. Comparative Analysis of Deep Learning Models
Génère un bar chart des accuracies de tous les modèles.

```python
plt.bar(results.keys(), results.values())
plt.title("Model Comparison (Accuracy)")
```

---

### 9. Best Model Selection
Identifie automatiquement le modèle avec la meilleure accuracy.

```python
best_model_name = max(results, key=results.get)
```

---

### 10. Qualitative Prediction Analysis
Sélectionne aléatoirement 5 images par classe (20 images au total) et compare les prédictions de chaque modèle sur ces images.

**Fonction `predict(model, img_path)`** :
```python
def predict(model, img_path):
    img = Image.open(img_path).convert("RGB")
    img = transform(img).unsqueeze(0).to(device)
    outputs = model(img)
    pred = outputs.argmax(dim=1)
    return pred.item()
```

---

### 11. Ground Truth vs Model Predictions Comparison
Génère un DataFrame pandas comparatif :

| Colonne | Contenu |
|---|---|
| `Image` | Nom du fichier image |
| `True_Label` | Classe réelle |
| `[ModelName]` | Prédiction du modèle |
| `[ModelName]_Correct` | Booléen — prédiction correcte ? |

---

### 12. Visual Inspection of Model Predictions
Calcule l'accuracy de chaque modèle sur les 20 images qualitatives et génère un tableau récapitulatif.

---

## Résultats obtenus

| Modèle | Accuracy |
|---|---|
| ConvNeXt | **97.70%** |
| ViT | **97.70%** |
| EfficientNet | 96.55% |
| Swin Transformer | 96.55% |
| ResNet50 | 95.40% |

---

## Fichiers produits
| Fichier | Description |
|---|---|
| `full_classification_metrics.csv` | Tableau complet de toutes les métriques (utilisé par `poc/` et analyses futures) |

---

## Dépendances
```
torch, torchvision, scikit-learn, matplotlib, pandas, Pillow
```
