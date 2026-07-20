# medet — Application mobile (Flutter)

Squelette initial de l'app mobile : liste des examens récents (anonymes), détail d'un examen (segments détectés), et partage avec un confrère via lien.

---

## 1. Structure

```
mobile_app/
├── pubspec.yaml
└── lib/
    ├── main.dart                      # Point d'entrée
    ├── theme/
    │   └── app_theme.dart             # Couleurs/thème (cohérent avec l'app Streamlit)
    ├── models/
    │   └── record.dart                # Segment, RecordSummary, RecordDetail
    ├── services/
    │   └── api_service.dart           # Appels HTTP vers le backend FastAPI
    ├── screens/
    │   ├── home_screen.dart           # Liste des examens récents
    │   └── record_detail_screen.dart  # Détail d'un examen + segments
    └── widgets/
        ├── record_card.dart           # Carte d'un examen dans la liste
        └── share_dialog.dart          # Génération + partage du lien
```

---

## 2. Installation

Prérequis : Flutter SDK installé (`flutter --version` pour vérifier).

```bash
cd mobile_app
flutter pub get
```

---

## 3. Configurer l'URL du backend

Dans `lib/services/api_service.dart` :

```dart
ApiService({this.baseUrl = 'http://10.0.2.2:8000'});
```

- **Émulateur Android** : `10.0.2.2` pointe automatiquement vers le `localhost` de ta machine — garde tel quel si le backend tourne sur ton PC pendant les tests.
- **Simulateur iOS** : remplace par `http://localhost:8000` (fonctionne différemment de l'émulateur Android).
- **Téléphone physique / VPS déployé** : remplace par l'IP ou le domaine réel, ex `https://medet.tondomaine.com`.

---

## 4. Lancer l'app

```bash
flutter run
```

Sélectionne l'émulateur/simulateur ou l'appareil physique connecté quand Flutter te le propose.

---

## 5. Ce qui est fait dans cette première version

- ✅ Écran d'accueil : liste des examens récents (`GET /records`), avec type de source, types de polypes détectés, indicateur de partage actif.
- ✅ Écran de détail : tous les segments détectés d'un examen (`GET /records/{id}`), avec timestamps, confiance, nombre de frames.
- ✅ Partage : génère un lien via `POST /records/{id}/share`, puis ouvre le sélecteur de partage natif (Messages, Mail, WhatsApp...) via `share_plus`.
- ✅ Suppression d'un examen (`DELETE /records/{id}`).

## 6. Ce qui n'est PAS encore fait (prochaines étapes)

- Écran de capture (image/vidéo/webcam) — pour l'instant, l'app suppose que les examens sont déjà créés côté backend (ex: par l'app Streamlit ou un autre client).
- Authentification / gestion des utilisateurs médecins.
- Visionnage direct du flux vidéo depuis l'app (nécessiterait l'intégration HLS évoquée précédemment pour le Mode 4).
- Mode hors-ligne / cache local.

---

## 7. Rappel important — confidentialité

Aucun écran de cette app ne doit jamais afficher ou demander une identité réelle de patient (nom, date de naissance, numéro de dossier). Le champ `referenceLabel` est un texte libre de repérage pour le médecin uniquement (ex: "Salle 2 - matin") — à respecter dans tout développement futur sur cet écran.

---

## 8. Limite de cet environnement de développement

Ce squelette a été écrit et vérifié pour sa cohérence de structure et de syntaxe, mais **n'a pas pu être compilé ni exécuté ici** (pas de SDK Flutter/Dart disponible dans cet environnement). Lance `flutter pub get` puis `flutter analyze` en premier chez toi pour repérer d'éventuelles erreurs avant de builder — normal pour un premier passage, dis-moi les erreurs exactes si `flutter analyze` en remonte, je corrige directement.