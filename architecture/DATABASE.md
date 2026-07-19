# medet — Structure de la base de données

Base **SQLite**, fichier unique `medet_records.db`, créé automatiquement au premier démarrage du backend (`init_db()` dans `database.py`, appelé au `startup` de `main.py`).

---

## 1. Principe de confidentialité (à respecter dans toute évolution future)

**Aucune identité réelle de patient n'est stockée** — pas de nom, pas de date de naissance, pas de numéro de dossier hospitalier, pas de photo de visage. Le seul champ de repérage est `reference_label`, un texte **libre** choisi par le médecin (ex: `"Salle 2 - matin"`, `"Examen du 19/07"`), jamais un identifiant patient.

---

## 2. Table unique : `records`

| Colonne | Type | Nullable | Description |
|---|---|---|---|
| `id` | `String` (UUID) | Non — clé primaire | Identifiant généré automatiquement à la création (ex: `efb327a9-4e4d-4b53-a1fa-1739c6c10490`) |
| `created_at` | `DateTime` | Non | Horodatage de création (UTC), généré automatiquement |
| `source_type` | `String` | Non | Origine de l'analyse : `image` / `video` / `webcam` / `stream` |
| `reference_label` | `String` | Oui | Libellé libre choisi par le médecin — **jamais une identité** |
| `notes` | `Text` | Oui | Notes libres du médecin sur l'examen |
| `summary_json` | `Text` (JSON sérialisé) | Non | Comptage des types de polypes détectés, ex: `{"1s": 1, "2": 1}` |
| `segments_json` | `Text` (JSON sérialisé) | Non | Liste complète des segments détectés (voir structure ci-dessous) |
| `share_token` | `String` | Oui — unique, indexé | Jeton généré à la demande de partage (ex: `tTz53ZFvYCJc0GGbx3925RnmKkBQtEeF`) |
| `share_enabled` | `Boolean` | Non (défaut `false`) | Indique si le lien de partage est actuellement actif |

---

## 3. Structure d'un segment (dans `segments_json`)

Chaque élément de la liste `segments_json` a cette forme (correspond au schéma Pydantic `SegmentResult`) :

```json
{
  "start_timestamp_seconds": 5.0,
  "end_timestamp_seconds": 8.5,
  "duration_seconds": 3.5,
  "polyp_type": "1s",
  "polyp_label": "Polype sessile (1s)",
  "max_confidence": 0.89,
  "frame_count": 12
}
```

`polyp_type` correspond à la nomenclature définie par le manager : `1p` (pédiculé), `1s` (sessile), `2` (lésion plane), `3` (lésion ulcérée).

---

## 4. Pourquoi `segments_json` et `summary_json` sont stockés en texte (JSON) plutôt qu'en tables séparées

Choix pragmatique pour cette première version : un examen a un nombre variable de segments, mais on ne fait jamais de recherche/filtre **à l'intérieur** des segments (ex: "tous les segments de type 1p tous examens confondus") pour l'instant — donc pas besoin de table relationnelle séparée. Si ce besoin apparaît plus tard (statistiques globales, recherche par type sur tout l'historique), il faudra migrer vers une table `segments` liée par clé étrangère à `records`.

---

## 5. Index et contraintes

- `id` : clé primaire (recherche directe par examen)
- `share_token` : indexé et unique (recherche rapide lors de la consultation via lien de partage, `GET /shared/{token}`)

---

## 6. Cycle de vie du partage

1. `share_token` est `NULL` et `share_enabled` est `false` à la création.
2. `POST /records/{id}/share` génère un token aléatoire (`secrets.token_urlsafe(24)`) s'il n'existe pas encore, et passe `share_enabled` à `true`.
3. `GET /shared/{token}` ne retourne les données que si `share_enabled = true` **et** que le token correspond exactement — sinon 404.
4. `DELETE /records/{id}/share` repasse `share_enabled` à `false` (le token reste en base mais devient inopérant, il sera réutilisé si le partage est réactivé plus tard).

---

## 7. Où se trouve le fichier de la base

À la racine du dossier `backend/`, nommé `medet_records.db` — généré automatiquement, **non versionné** (à ajouter dans `.gitignore` si ce n'est pas déjà fait, pour éviter de committer des données de test).

---

## 8. Inspecter la base manuellement

```bash
pip install --break-system-packages sqlite-utils
sqlite-utils rows medet_records.db records
```
Ou avec une interface graphique : [DB Browser for SQLite](https://sqlitebrowser.org/) (gratuit), en ouvrant directement `medet_records.db`.

---

## 9. Limite connue de cette version

Base **SQLite locale** — adaptée pour le développement et une première mise en production légère (VPS unique, CPU only). Si l'usage grandit (plusieurs serveurs, forte concurrence d'écriture), il faudra migrer vers PostgreSQL — le code utilisant SQLAlchemy, la migration ne nécessite qu'un changement de `DATABASE_URL` dans `database.py`, sans réécrire la logique métier (`services/records_service.py`).
