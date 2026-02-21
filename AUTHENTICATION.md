# MediaHub - Authentication Testing

## Authentifizierung testen

Um die API zu testen, benötigst du einen JWT Token von Keycloak.

### 1. Token von Keycloak erhalten

```bash
# Mit Client Credentials Flow (für Tests)
curl -X POST "${KEYCLOAK_SERVER_URL}/realms/${KEYCLOAK_REALM}/protocol/openid-connect/token" \
  -H "Content-Type: application/x-www-form-urlencoded" \
  -d "client_id=${KEYCLOAK_CLIENT_ID}" \
  -d "client_secret=${KEYCLOAK_CLIENT_SECRET}" \
  -d "grant_type=client_credentials"
```

### 2. API mit Token aufrufen

```bash
# Token in Variable speichern
TOKEN="your_jwt_token_here"

# Current User Info abrufen
curl -X GET "http://localhost:8000/auth/me" \
  -H "Authorization: Bearer ${TOKEN}"
```

### 3. API Dokumentation

Besuche http://localhost:8000/docs für die interaktive API Dokumentation.
Dort kannst du auch den Token im "Authorize" Button hinterlegen.

## Geschützte Endpoints

Alle Endpoints außer `/` und `/health` erfordern Authentifizierung.

Der JWT Token muss im `Authorization` Header mit dem `Bearer` Schema gesendet werden:

```
Authorization: Bearer <your_token>
```

## User Synchronisation

Beim ersten API-Aufruf mit einem neuen Token wird der User automatisch in der Datenbank angelegt.
Die User-Informationen werden bei jedem Request mit den Token-Claims synchronisiert.
