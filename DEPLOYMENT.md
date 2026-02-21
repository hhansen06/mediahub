# MediaHub Deployment Guide

## Voraussetzungen

- Docker & Docker Compose installiert
- Zugriff auf Keycloak Server
- OVH S3 Bucket eingerichtet
- Domain (optional, für SSL)

## 1. Umgebungsvariablen konfigurieren

Erstelle eine `.env` Datei im `backend/` Verzeichnis:

```bash
cp .env.template backend/.env
```

Bearbeite `backend/.env` mit deinen Werten:

```bash
# Database
DB_ROOT_PASSWORD=secure_root_password
DB_USER=mediahub
DB_PASSWORD=secure_db_password
DB_NAME=mediahub

# Keycloak
KEYCLOAK_SERVER_URL=https://your-keycloak.com
KEYCLOAK_REALM=your-realm
KEYCLOAK_CLIENT_ID=mediahub-client
KEYCLOAK_CLIENT_SECRET=your-client-secret

# S3 Storage
S3_ENDPOINT_URL=https://s3.gra.io.cloud.ovh.net
S3_ACCESS_KEY_ID=your-access-key
S3_SECRET_ACCESS_KEY=your-secret-key
S3_BUCKET_NAME=mediahub-bucket
S3_REGION=gra
```

## 2. Keycloak Client Setup

1. Erstelle einen neuen Client in Keycloak
2. Client Protocol: `openid-connect`
3. Access Type: `confidential`
4. Valid Redirect URIs: `http://your-domain/*`
5. Web Origins: `http://your-domain`
6. Notiere Client Secret

## 3. S3 Bucket erstellen (OVH)

1. Erstelle S3 Container in OVH Cloud
2. Erstelle S3 User mit Read/Write Rechten
3. Notiere Access Key und Secret Key
4. Bucket sollte privat sein (Pre-signed URLs werden verwendet)

## 4. Datenbank initialisieren

```bash
# Starte MariaDB
docker-compose up -d mariadb

# Warte bis DB bereit ist
docker-compose logs -f mariadb

# Führe Migrationen aus
docker-compose run --rm backend alembic upgrade head
```

## 5. Anwendung starten

### Entwicklung (Lokal)

```bash
# Nur Datenbank starten
docker-compose up -d mariadb

# Python Virtual Environment erstellen und aktivieren
cd backend
python -m venv venv
source venv/bin/activate  # Linux/Mac
# oder: venv\Scripts\activate  # Windows

# Dependencies installieren
pip install -r requirements.txt

# Zurück zum Projektroot
cd ..

# Migrationen ausführen (vom Root aus)
alembic upgrade head

# Backend starten
cd backend
python -m app.main

# Zugriff: http://localhost:8000
```

### Production

```bash
# Build und starte mit production config
docker-compose -f docker-compose.prod.yml up -d

# Nginx für Frontend/Reverse Proxy läuft auf Port 80
# Backend API über /api/
```

## 6. SSL/TLS einrichten (Production)

### Mit Let's Encrypt

```bash
# Installiere certbot
sudo apt install certbot python3-certbot-nginx

# Generiere Zertifikat
sudo certbot --nginx -d your-domain.com

# Zertifikate werden automatisch erneuert
```

### Manuelle Zertifikate

```bash
# Kopiere Zertifikate nach ssl/
mkdir -p ssl
cp your-cert.pem ssl/cert.pem
cp your-key.pem ssl/key.pem

# Uncomment HTTPS block in nginx.conf
```

## 7. Backup

### Datenbank Backup

```bash
# Backup erstellen
docker-compose exec mariadb mysqldump -u root -p${DB_ROOT_PASSWORD} mediahub > backup/mediahub_$(date +%Y%m%d).sql

# Restore
docker-compose exec -T mariadb mysql -u root -p${DB_ROOT_PASSWORD} mediahub < backup/mediahub_20240101.sql
```

### S3 Backup

S3 Daten sind bereits in OVH gesichert. Für zusätzliche Backups:
- Nutze OVH Object Storage Snapshots
- Oder sync zu anderem S3-kompatiblen Storage

## 8. Monitoring

### Logs

```bash
# Alle Logs
docker-compose logs -f

# Nur Backend
docker-compose logs -f backend

# Nur Fehler
docker-compose logs -f | grep ERROR
```

### Health Checks

```bash
# Backend Health
curl http://localhost:8000/health

# Datenbank
docker-compose exec mariadb mysqladmin ping -h localhost
```

### Prometheus/Grafana (Optional)

Erweitere `docker-compose.prod.yml` mit Monitoring-Stack.

## 9. Updates

```bash
# Code aktualisieren
git pull

# Images neu bauen
docker-compose -f docker-compose.prod.yml build

# Services neu starten
docker-compose -f docker-compose.prod.yml up -d

# Migrationen
docker-compose exec backend alembic upgrade head
```

## 10. Troubleshooting

### Backend startet nicht

```bash
# Logs prüfen
docker-compose logs backend

# Container neu starten
docker-compose restart backend

# .env Variablen prüfen
docker-compose config
```

### Datenbank Connection Error

```bash
# DB Status prüfen
docker-compose ps mariadb
docker-compose logs mariadb

# DB neu starten
docker-compose restart mariadb
```

### S3 Upload Fehler

- Prüfe S3 Credentials in .env
- Teste Verbindung mit AWS CLI
- Prüfe Bucket Permissions

### Keycloak Auth Fehler

- Prüfe Keycloak erreichbar
- Validiere Client ID und Secret
- Prüfe Realm Name
- Token im Browser Console prüfen

## Sicherheit Best Practices

1. **Starke Passwörter** für DB und Keycloak
2. **HTTPS** in Production (Let's Encrypt)
3. **Firewall** Regeln (nur 80/443 öffentlich)
4. **Rate Limiting** in nginx für API
5. **Regelmäßige Updates** von Dependencies
6. **Backup-Strategie** implementieren
7. **Monitoring** und Alerting einrichten

## Performance Optimierung

1. **Nginx Caching** für statische Files
2. **Database Indexes** prüfen
3. **S3 CDN** (OVH CDN) für Media
4. **Redis** für Session/Cache (optional)
5. **Horizontal Scaling** mit Load Balancer

## Support

- GitHub Issues: https://github.com/your-repo/mediahub
- Dokumentation: README.md
- API Docs: http://your-domain/docs
