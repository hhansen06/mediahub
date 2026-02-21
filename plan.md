# ziel 
dieses projekt soll ein webbasierter mediaserver werden. angemeldete benutzer sollen medien (fotos, videos) in sammlungen hochladen können. Benutzer sollen gelerien anlegen können und dann per simplem drag & drop mediendaten hochladen können.

# techstack
- erstelle das projekt in python mit FastAPI
- als datenbank verwenden wir mariadb
- alle notwendigen einstellungsparameter werden in einer .env gespeichert
- als quelle für authentification dient ein keycloak (bereits vorhanden)
- mediendaten werden in einem s3 kompatiblen Bucket bei ovh gespeichert (bereits vorhanden)
- frontend: einfaches HTML/CSS/JavaScript

# projektentscheidungen
- alle benutzer können alle sammlungen sehen
- videos ohne thumbnail-generierung (erstmal)
- videos nur als download, kein streaming
- metadaten speichern: EXIF, GPS, Datum, Kamera-Info + Upload-User

# key features
- user login
- CRUD von sammlungen (name, ort, datum) 
- hochladen von medien per drag & drop
- anzeige der medien in einer galerie unterhalb der sammlung
- auslesen und speichern der metadaten von fotos
- detail anzeige von bildern mit darstellung der metadaten in einer seitenleiste

# projektphasen

## Phase 1: Projekt Setup ✅
- [x] Python Projekt-Struktur erstellen (FastAPI/Flask)
- [x] requirements.txt mit Dependencies anlegen
- [x] .env Template erstellen für Konfiguration
- [x] Docker Compose Setup für lokale Entwicklung (MariaDB, Keycloak)
- [x] Basis-Verzeichnisstruktur anlegen

## Phase 2: Datenbank Setup ✅
- [x] SQLAlchemy Models definieren (User, Collection, Media)
- [x] Alembic für Datenbank-Migrationen einrichten
- [x] Basis-Schema für MariaDB erstellen
- [x] Datenbank-Connection und Session Management

## Phase 3: Authentifizierung ✅
- [x] Keycloak Client Konfiguration
- [x] JWT Token Validierung implementieren
- [x] Authentication Middleware/Dependency
- [x] User Context aus Token extrahieren

## Phase 4: Collection API ✅
- [x] POST /collections - Sammlung erstellen
- [x] GET /collections - Liste aller Sammlungen
- [x] GET /collections/{id} - Einzelne Sammlung abrufen
- [x] PUT /collections/{id} - Sammlung aktualisieren
- [x] DELETE /collections/{id} - Sammlung löschen

## Phase 5: S3 Storage Integration ✅
- [x] Boto3 Client für OVH S3 konfigurieren
- [x] Upload-Funktionen für Bilder und Videos
- [x] Thumbnail-Generierung implementieren
- [x] Pre-signed URLs für sicheren Zugriff

## Phase 6: Media Upload ✅
- [x] POST /collections/{id}/media - Multipart Upload Endpoint
- [x] Datei-Validierung (Typ, Größe)
- [x] Upload zu S3 und Datenbank-Eintrag
- [x] Batch-Upload Unterstützung

## Phase 7: Metadata Extraktion ✅
- [x] EXIF-Daten aus Fotos auslesen (Pillow/exifread)
- [x] GPS-Koordinaten extrahieren und speichern
- [x] Aufnahmedatum, Kamera-Info extrahieren
- [x] Video-Metadaten auslesen (duration, codec)

## Phase 8: Media API & Gallery ✅
- [x] GET /collections/{id}/media - Medien einer Sammlung
- [x] GET /media/{id} - Einzelnes Medium mit Metadaten
- [x] Pagination und Sorting implementieren
- [x] Thumbnail-URLs bereitstellen

## Phase 9: Frontend Basis ✅
- [x] HTML/CSS/JavaScript Setup (oder React/Vue)
- [x] Login-Seite mit Keycloak Integration
- [x] Collections-Übersicht (Liste, Erstellen)
- [x] Gallery-View mit Grid-Layout

## Phase 10: Drag & Drop Upload ✅
- [x] Drag & Drop Zone in Gallery implementieren
- [x] Upload-Progress Anzeige
- [x] Multiple Files gleichzeitig hochladen
- [x] Error Handling und User Feedback

## Phase 11: Detail-Ansicht ✅
- [x] Modal/Page für Bild-Detail-Ansicht
- [x] Metadaten-Sidebar mit allen Infos
- [x] Navigation zwischen Bildern
- [x] Download-Option

## Phase 12: Testing & Deployment ✅
- [x] Unit Tests für Backend-Logik
- [x] Integration Tests für APIs
- [x] Docker Images erstellen
- [x] Deployment-Dokumentation

## Phase 13: Face Recognition Backend ✅
- [x] Person und FaceDetection Datenbank-Modelle erstellen
- [x] OpenCV Haar Cascades für Face Detection
- [x] Face Encoding Service (Histogram-basiert)
- [x] Person-Verwaltungs-API (CRUD)
- [x] Face Detection Trigger API (/persons/detect-faces/{media_id})
- [x] Database Migration (003_add_face_recognition)
- [x] Face Matching & Comparison Funktionen

## Phase 14: Face Recognition Frontend ✅
- [x] Person Gallery UI mit Face-Thumbnails
- [x] loadPersons() Funktion für Personen-Liste
- [x] Person-Karten mit Name-Eingabe
- [x] Detections-Counter für jede Person
- [x] "Fotos anzeigen" View mit Face-Bounding-Boxes
- [x] Person löschen Funktionalität
- [x] CSS Styling für Personen-Galerie
- [x] Detection-Info mit Konfidenz und Datum
- [x] Face-Thumbnail Endpoint (/media/face-thumbnail/{s3_key})
- [x] Name-Update über API (PUT /persons/{id})
- [x] Navigation Link "👥 Personen" hinzugefügt

## Phase 15: Face Recognition Integration ✅
- [x] Auto-Face-Detection beim Media Upload
- [x] Face-Crop Extraktion und S3 Speicherung
- [x] Face-Crop Anzeige in Personen-Galerie (Thumbnails)
- [x] Detections-Cleanup beim Media-Löschen
- [x] Person-Löschen mit robuster Authentifizierung
- [x] Auto-Löschen von Personen ohne Detections
- [x] Batch-Face-Detection für existierende Medien (/persons/batch/detect-faces)
- [x] Face-Similarity Matching für Detections (POST /persons/find-similar/{detection_id})
- [x] Detection-zu-Person Zuweisung (POST /persons/{person_id}/assign-detection)

## Phase 16: Erweiterte Features (Geplant) ⏳
- [ ] Face-Similarity Matching (Python `face_recognition` Lib oder deepface)
- [ ] Automatische Person-Vorschläge für neue Detections
- [ ] Gesichter-Cluster-Analyse
- [ ] Batch-Operations (mehrere Medien auf einmal zu Collection verschieben)
- [ ] Search-Funktion (nach Person, Ort, Datum, Kamera)
- [ ] Export-Funktionalität (zip mit ausgewählten Medien)
- [ ] Share-Links mit Ablaufdatum
- [ ] Berechtigungen / Multi-User-Unterstützung pro Collection
