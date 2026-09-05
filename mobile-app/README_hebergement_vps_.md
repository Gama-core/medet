# Déploiement et test sur VPS 

Guide complet pour installer et tester l'application `medet` directement sur un VPS.

---

## 0. Prérequis avant de commencer
- (Optionnel mais recommandé) Un nom de domaine ou sous-domaine pointé vers l'IP du VPS — même un sous-domaine gratuit type **DuckDNS** fonctionne, à préparer la veille pour laisser le temps à la propagation DNS.

---

## 1. Se connecter au VPS

Depuis PowerShell (Windows 10/11 inclut déjà un client SSH) :
```powershell
ssh root@IP_DU_VPS
```
Remplace `IP_DU_VPS` par l'adresse fournie par ton hébergeur. Accepte l'empreinte de connexion (`yes`) au premier essai, puis entre le mot de passe.

---

## 2. Mettre à jour le système et installer les dépendances de base

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3-pip python3-venv git tmux ufw nginx
```

---

## 3. Sécuriser l'accès réseau (avant d'exposer quoi que ce soit)

```bash
sudo ufw allow OpenSSH
sudo ufw allow 80/tcp
sudo ufw allow 443/tcp
sudo ufw enable
```
Confirme avec `y` si demandé. Vérifie l'état :
```bash
sudo ufw status
```
⚠️ Ne pas ouvrir le port `8501` (Streamlit) publiquement — on passe par Nginx en façade (étape 7).

---

## 4. Récupérer le code du projet

**via Git (recommandé si le repo est accessible depuis le VPS) :**
```bash
git clone https://github.com/Gama-core/medet.git
cd medet/poc_globale
```

---

## 5. Créer l'environnement Python et installer les dépendances

```bash
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```
⏱️ Cette étape peut prendre **plusieurs minutes** (PyTorch et ses dépendances sont volumineux à télécharger). C'est normal.

Vérifie que les poids des modèles sont bien présents :
```bash
ls -lh weights/
```

---

## 6. Premier test manuel (avant de rendre ça permanent)

```bash
streamlit run app2.py --server.port 8501 --server.address 0.0.0.0
```
Depuis ton PC, ouvre un navigateur et va sur :
```
http://IP_DU_VPS:8501
```
✅ Si l'app s'affiche, la base fonctionne. Arrête ensuite avec `Ctrl+C` — on va la faire tourner proprement en continu (étape 7).

⚠️ Si rien ne s'affiche : vérifie que le firewall du VPS n'a pas déjà bloqué le port 8501 (normal si tu as suivi l'étape 3 à la lettre), ou teste temporairement `sudo ufw allow 8501/tcp` pour ce diagnostic uniquement, puis referme-le ensuite (`sudo ufw delete allow 8501/tcp`).

---

## 7. Faire tourner l'app en continu avec `systemd` (redémarre automatiquement)

Crée un fichier de service :
```bash
sudo nano /etc/systemd/system/medet.service
```
Colle ce contenu (adapte les chemins si besoin) :
```ini
[Unit]
Description=medet Streamlit app
After=network.target

[Service]
User=root
WorkingDirectory=/root/medet/poc_globale
ExecStart=/root/medet/poc_globale/venv/bin/streamlit run app2.py --server.port 8501 --server.address 127.0.0.1
Restart=always
RestartSec=5

[Install]
WantedBy=multi-user.target
```
Sauvegarde (`Ctrl+O`, Entrée, `Ctrl+X`), puis active :
```bash
sudo systemctl daemon-reload
sudo systemctl enable medet
sudo systemctl start medet
```
Vérifie que ça tourne :
```bash
sudo systemctl status medet
```
Note : ici l'app écoute sur `127.0.0.1` (local uniquement) car Nginx va la exposer proprement à l'étape suivante.

**Commandes utiles pour la suite :**
```bash
sudo systemctl restart medet   # redémarrer après une mise à jour du code
sudo journalctl -u medet -f    # voir les logs en direct (équivalent du terminal Streamlit)
```

---

## 8. Exposer l'app proprement avec Nginx (+ HTTPS gratuit)

Crée la config Nginx :
```bash
sudo nano /etc/nginx/sites-available/medet
```
Contenu (remplace `medet.tondomaine.com` par ton domaine/sous-domaine) :
```nginx
server {
    listen 80;
    server_name medet.tondomaine.com;

    location / {
        proxy_pass http://127.0.0.1:8501;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
        proxy_set_header Host $host;
        proxy_read_timeout 86400;
    }
}
```
Active-la :
```bash
sudo ln -s /etc/nginx/sites-available/medet /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl reload nginx
```
Ajoute le HTTPS gratuit avec Let's Encrypt :
```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot --nginx -d medet.tondomaine.com
```
Suis les instructions (email, acceptation des conditions). Certbot configure automatiquement le renouvellement.

**Test final** : ouvre `https://medet.tondomaine.com` dans un navigateur, depuis n'importe quel appareil.

---

## 9. Checklist de validation finale

- [ ] `sudo systemctl status medet` → actif (`running`)
- [ ] L'app s'ouvre via `https://ton-domaine` depuis un autre appareil que le VPS
- [ ] Mode Image fonctionne
- [ ] Mode Vidéo fonctionne (upload + traitement)
- [ ] Mode Webcam : ⚠️ ne fonctionnera pas sur le VPS lui-même (pas de webcam physique) — normal, à tester uniquement en local
- [ ] Mode URL (RTSP) : à tester avec un flux accessible depuis le VPS (le VPS doit pouvoir atteindre l'IP RTSP réseau)
- [ ] `sudo journalctl -u medet -f` → aucune erreur au chargement

---

## 10. Dépannage rapide

| Symptôme | Cause probable | Solution |
|---|---|---|
| `Connection refused` sur le port 8501 | Firewall bloque, ou app pas démarrée | `sudo systemctl status medet` puis `sudo ufw status` |
| Page blanche via le domaine, mais OK en `http://IP:8501` | Nginx mal configuré | `sudo nginx -t` pour voir l'erreur exacte |
| `502 Bad Gateway` | L'app Streamlit n'est pas active | `sudo systemctl restart medet`, vérifier les logs |
| Certbot échoue | Le domaine ne pointe pas encore vers l'IP du VPS | Vérifier la propagation DNS (`nslookup medet.tondomaine.com`) |
| App très lente | Normal en CPU only avec YOLO + EfficientNet | Augmenter `FRAME_SKIP`, prévoir export ONNX plus tard |
| `pip install` très long ou échoue | RAM insuffisante pendant l'installation de PyTorch | Vérifier avec `free -h`, ajouter du swap si besoin (`sudo fallocate -l 2G /swapfile && sudo chmod 600 /swapfile && sudo mkswap /swapfile && sudo swapon /swapfile`) |

---

## 11. Mettre à jour le code plus tard (workflow habituel)

```bash
cd /root/medet/poc_globale
git pull                     # ou re-transférer via scp
source venv/bin/activate
pip install -r requirements.txt   # si les dépendances ont changé
sudo systemctl restart medet
```

---

*medet — Pipeline hybride YOLO (étage 1, local) + EfficientNet (étage 2, cloud) · Déploiement VPS.*
