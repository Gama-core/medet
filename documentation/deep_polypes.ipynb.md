# deep_polypes.ipynb

## Rôle dans le projet
Notebook d'**exploration et de preprocessing** du dataset `deep_polypes`. C'est le point d'entrée du pipeline ML : il prépare les données, visualise la distribution des classes, et valide que le chargement fonctionne avant l'entraînement.

---

## Environnement
- **Plateforme** : Google Colab (GPU T4 recommandé)
- **Dataset** : `deep_polypes/` stocké sur Google Drive
- **Format** : `ImageFolder` — un dossier par classe

---

## Structure du dataset attendue
```
deep_polypes/
├── mauvaise_preparation/    # Images de mauvaise préparation intestinale
├── mici/                    # Maladie Inflammatoire Chronique de l'Intestin
├── normal/                  # Muqueuse saine
└── polype/                  # Polypes détectés
```

---

## Sections du notebook

### 1. Montage Google Drive
```python
from google.colab import drive
drive.mount('/content/drive')
!cp -r "/content/drive/MyDrive/deep_polypes" /content/
```
Copie le dataset en local dans `/content/` pour accélérer les I/O pendant l'entraînement.

---

### 2. Exploration du dataset
```python
import os
print(os.listdir("deep_polypes"))
```
Affiche les 4 dossiers de classes. Permet de vérifier l'intégrité de la structure avant de continuer.

---

### 3. Chargement avec ImageFolder
```python
from torchvision import datasets, transforms

transform = transforms.Compose([
    transforms.Resize((224, 224)),
    transforms.ToTensor(),
])

dataset = datasets.ImageFolder(root=data_path, transform=transform)

print("Classes:", dataset.classes)
print("Nb images:", len(dataset))
```

`ImageFolder` lit automatiquement les sous-dossiers comme classes et assigne un index entier à chaque classe (ordre alphabétique).

**Mapping classes → index :**
```
mauvaise_preparation → 0
mici                 → 1
normal               → 2
polype               → 3
```

---

### 4. Split Train / Val / Test
```python
train_size = int(0.7 * len(dataset))
val_size   = int(0.15 * len(dataset))
test_size  = len(dataset) - train_size - val_size

train_ds, val_ds, test_ds = random_split(dataset, [train_size, val_size, test_size])
```

**Règle de split :**
- 70% → entraînement
- 15% → validation
- 15% → test final

Les DataLoaders sont créés avec `batch_size=32`.

---

### 5. Visualisation d'un batch
```python
images, labels = next(iter(train_loader))
plt.imshow(images[0].permute(1, 2, 0))
plt.title(dataset.classes[labels[0]])
plt.show()
```

Affiche la première image du premier batch d'entraînement pour contrôle visuel. `.permute(1,2,0)` convertit le format PyTorch `(C, H, W)` → `(H, W, C)` pour matplotlib.

---

## Paramètres techniques

| Paramètre | Valeur |
|---|---|
| Taille d'image | 224 × 224 pixels |
| Normalisation | ToTensor() → valeurs entre 0 et 1 |
| Batch size | 32 |
| Split | 70 / 15 / 15 % |
| Format entrée | RGB (3 canaux) |

---

## Rôle dans la chaîne complète
Ce notebook sert de **validation préliminaire** : il confirme que le dataset est bien formé, que les classes sont correctement lues, et que le pipeline de chargement fonctionne. Les paramètres définis ici (taille, split, batch) sont repris à l'identique dans `Model_Comparison.ipynb` pour garantir la cohérence des résultats.

---

## Dépendances
```
torch, torchvision, matplotlib, os
```
