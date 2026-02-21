# Quick Start

## Problem: Validation Errors beim Start?

Stelle sicher, dass die `.env` Datei im richtigen Verzeichnis liegt:

```bash
# Von Projekt-Root aus:
cp .env.template backend/.env

# Dann backend/.env mit deinen Werten bearbeiten
cd backend
nano .env  # oder dein Editor
```

Die `.env` Datei **muss** im `backend/` Verzeichnis liegen, nicht im Projekt-Root!

## Minimale .env für lokales Testen

Wenn du nur lokal testen willst:

```bash
cd backend
cat > .env << 'EOF'
# App
DEBUG=True

# Database
DB_HOST=localhost
DB_PORT=3306
DB_USER=mediahub
DB_PASSWORD=mediahub_password
DB_NAME=mediahub

# Keycloak (Dummy-Werte für Entwicklung)
KEYCLOAK_SERVER_URL=http://localhost:8080
KEYCLOAK_REALM=master
KEYCLOAK_CLIENT_ID=mediahub
KEYCLOAK_CLIENT_SECRET=dummy-secret

# S3 (Dummy-Werte für Entwicklung)
S3_ENDPOINT_URL=http://localhost:9000
S3_ACCESS_KEY_ID=minioadmin
S3_SECRET_ACCESS_KEY=minioadmin
S3_BUCKET_NAME=mediahub
S3_REGION=us-east-1
EOF
```

**Hinweis:** Mit diesen Dummy-Werten funktioniert die Auth und S3-Upload nicht, aber die API startet und Migrations laufen durch.
