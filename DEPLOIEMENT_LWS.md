# Guide de déploiement — Children's Fruit sur LWS

## Option A — LWS VPS (recommandé)

### 1. Connexion au VPS
```bash
ssh root@VOTRE_IP_LWS
```

### 2. Installation des dépendances système
```bash
apt update && apt upgrade -y
apt install -y python3 python3-pip python3-venv nginx git
```

### 3. Créer un utilisateur dédié
```bash
adduser childrensfruit
su - childrensfruit
```

### 4. Uploader le projet
Depuis votre PC (PowerShell ou terminal) :
```bash
# Compressez le projet (sans venv/)
# Envoyez via FileZilla ou scp :
scp -r e:/childrensfruit/ root@VOTRE_IP:/home/childrensfruit/app
```
OU via Git :
```bash
# Sur le serveur :
git clone https://github.com/VOTRE_USER/childrensfruit.git /home/childrensfruit/app
```

### 5. Environnement Python
```bash
cd /home/childrensfruit/app
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

### 6. Fichier .env sur le serveur
Créez `/home/childrensfruit/app/.env` :
```env
DEBUG=False
SECRET_KEY=GENEREZ_UNE_NOUVELLE_CLE_ICI
ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com
```

### 7. Migrations et statiques
```bash
source venv/bin/activate
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser   # créer l'admin
```

### 8. Test Gunicorn
```bash
gunicorn childrensfruit.wsgi:application --bind 127.0.0.1:8000
# Ctrl+C pour stopper
```

### 9. Service systemd (démarrage automatique)
Créez `/etc/systemd/system/childrensfruit.service` :
```ini
[Unit]
Description=Children's Fruit Django App
After=network.target

[Service]
User=childrensfruit
Group=www-data
WorkingDirectory=/home/childrensfruit/app
ExecStart=/home/childrensfruit/app/venv/bin/gunicorn \
          childrensfruit.wsgi:application \
          --bind 127.0.0.1:8000 \
          --workers 2 \
          --timeout 120
Restart=always

[Install]
WantedBy=multi-user.target
```
```bash
systemctl daemon-reload
systemctl enable childrensfruit
systemctl start childrensfruit
systemctl status childrensfruit   # vérifier
```

### 10. Configuration Nginx
Créez `/etc/nginx/sites-available/childrensfruit` :
```nginx
server {
    listen 80;
    server_name votre-domaine.com www.votre-domaine.com;

    # Fichiers statiques (servis directement par Nginx)
    location /static/ {
        alias /home/childrensfruit/app/staticfiles/;
        expires 30d;
    }

    # Fichiers médias (uploads)
    location /media/ {
        alias /home/childrensfruit/app/media/;
        expires 7d;
    }

    # Application Django via Gunicorn
    location / {
        proxy_pass http://127.0.0.1:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        client_max_body_size 20M;
    }
}
```
```bash
ln -s /etc/nginx/sites-available/childrensfruit /etc/nginx/sites-enabled/
nginx -t        # tester la config
systemctl restart nginx
```

### 11. SSL gratuit avec Let's Encrypt
```bash
apt install -y certbot python3-certbot-nginx
certbot --nginx -d votre-domaine.com -d www.votre-domaine.com
```
Mettre à jour `.env` :
```env
ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com
```

---

## Option B — LWS Hébergement mutualisé (cPanel + Passenger)

> LWS mutualisé Pro ou Business supporte Python via cPanel.

### 1. Connexion cPanel
Connectez-vous à votre cPanel LWS → **"Setup Python App"**

### 2. Créer l'application Python
- Python version : **3.12**
- Application root : `childrensfruit`
- Application URL : votre domaine
- Application startup file : `passenger_wsgi.py`
- Application Entry point : `application`

### 3. Uploader les fichiers
Via le **Gestionnaire de fichiers cPanel** ou **FileZilla** (FTP/SFTP) :
- Uploadez tout le contenu du projet dans le dossier `childrensfruit/`
- **Ne pas uploader** : `venv/`, `.env`, `.git/`, `.claude/`

### 4. Installer les dépendances
Dans cPanel → **Terminal** (ou SSH) :
```bash
cd ~/childrensfruit
source /home/USER/virtualenv/childrensfruit/3.12/bin/activate
pip install -r requirements.txt
```

### 5. Créer le fichier .env
```bash
nano ~/.env   # ou via Gestionnaire de fichiers
```
Contenu :
```env
DEBUG=False
SECRET_KEY=GENEREZ_UNE_NOUVELLE_CLE_ICI
ALLOWED_HOSTS=votre-domaine.com,www.votre-domaine.com
```

### 6. Migrations
```bash
python manage.py migrate
python manage.py collectstatic --noinput
python manage.py createsuperuser
```

### 7. Redémarrer l'application
Dans cPanel → **Setup Python App** → cliquer **Restart**

---

## Commandes utiles (après déploiement)

```bash
# Voir les logs
journalctl -u childrensfruit -f          # VPS
tail -f ~/logs/error_log                  # cPanel

# Mettre à jour le site
cd /home/childrensfruit/app
git pull                                   # si Git
source venv/bin/activate
pip install -r requirements.txt
python manage.py migrate
python manage.py collectstatic --noinput
systemctl restart childrensfruit           # VPS

# Créer un superuser admin
python manage.py createsuperuser
```

---

## Checklist finale

- [ ] `.env` créé sur le serveur avec les bonnes valeurs
- [ ] `DEBUG=False` dans `.env`
- [ ] `ALLOWED_HOSTS` contient votre domaine LWS
- [ ] `python manage.py migrate` exécuté
- [ ] `python manage.py collectstatic` exécuté
- [ ] Superuser admin créé
- [ ] SSL/HTTPS activé (Let's Encrypt ou LWS SSL)
- [ ] Tester `/admin/`, `/`, `/webtv/`, `/don/`
