# MediaHub

Webbasierter Mediaserver für Fotos und Videos mit Sammlung-Verwaltung.

## Features

✅ **Sammlungen:** Organisiere Medien in Sammlungen mit Name, Ort, Datum
✅ **Upload:** Drag & Drop für Bilder und Videos (bis 100MB)
✅ **Metadaten:** Automatische EXIF, GPS und Kamera-Info Extraktion
✅ **Thumbnails:** Automatische Thumbnail-Generierung für Bilder
✅ **Galerie:** Responsive Grid-Ansicht mit Navigation
✅ **Detail-View:** Vollbild-Ansicht mit allen Metadaten
✅ **Authentifizierung:** Keycloak Integration
✅ **Storage:** S3-kompatible Speicherung (OVH)
✅ **Teilen:** Alle User sehen alle Sammlungen

## Quick Start

1. **Kopiere .env.template zu .env und konfiguriere die Werte**
   ```bash
   cp .env.template backend/.env
   # Bearbeite backend/.env mit deinen Werten
   ```

2. **Starte MariaDB für lokale Entwicklung**
   ```bash
   docker-compose up -d mariadb
   ```
   
   *Hinweis: Die docker-compose.yml enthält nur die Datenbank. Backend läuft lokal mit Python.*

3. **Installiere Python Dependencies**
   ```bash
   cd backend
   python -m venv venv                    # Erstelle Virtual Environment
   source venv/bin/activate               # Linux/Mac
   # oder: venv\Scripts\activate          # Windows
   pip install -r requirements.txt
   ```

4. **Führe Datenbank-Migrationen aus**
   ```bash
   alembic upgrade head
   ```

5. **Starte die Anwendung**
   ```bash
   cd backend
   python -m app.main
   ```

   Die API ist erreichbar unter: http://localhost:8000
   
   API Dokumentation: http://localhost:8000/docs

## Deployment

Siehe [DEPLOYMENT.md](DEPLOYMENT.md) für Production-Deployment mit Docker.

## Testen

```bash
# Installiere Test-Dependencies
pip install -r requirements-dev.txt

# Führe Tests aus
pytest

# Mit Coverage
pytest --cov=app --cov-report=html
```

## Projektstruktur

```
mediahub/
├── backend/
│   ├── app/
│   │   ├── api/          # API Routes
│   │   ├── core/         # Config, Database
│   │   ├── models/       # SQLAlchemy Models
│   │   ├── services/     # Business Logic
│   │   └── main.py       # FastAPI App
│   └── requirements.txt
├── frontend/
│   ├── static/           # CSS, JS
│   └── templates/        # HTML
├── .env                  # Konfiguration (nicht in Git)
├── .env.template         # Template für .env
└── docker-compose.yml    # MariaDB Container
```

## Technologie-Stack

- **Backend:** FastAPI (Python)
- **Database:** MariaDB
- **Auth:** Keycloak
- **Storage:** S3 (OVH)
- **Frontend:** HTML/CSS/JavaScript
