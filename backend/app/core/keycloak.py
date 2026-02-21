from keycloak import KeycloakOpenID
from app.core.config import settings
from urllib.parse import urlencode


class KeycloakClient:
    def __init__(self):
        self.keycloak_openid = KeycloakOpenID(
            server_url=settings.KEYCLOAK_SERVER_URL,
            client_id=settings.KEYCLOAK_CLIENT_ID,
            realm_name=settings.KEYCLOAK_REALM,
            client_secret_key=settings.KEYCLOAK_CLIENT_SECRET,
            verify=True
        )
    
    def get_public_key(self):
        """Get the public key from Keycloak for token verification"""
        return f"-----BEGIN PUBLIC KEY-----\n{self.keycloak_openid.public_key()}\n-----END PUBLIC KEY-----"
    
    def decode_token(self, token: str):
        """Decode and validate JWT token"""
        try:
            # Get public key and decode token
            token_info = self.keycloak_openid.decode_token(
                token,
                key=self.get_public_key(),
                options={
                    "verify_signature": True,
                    "verify_aud": False,  # Audience verification optional
                    "verify_exp": True    # Expiration verification
                }
            )
            return token_info
        except Exception as e:
            raise ValueError(f"Invalid token: {str(e)}")
    
    def introspect_token(self, token: str):
        """Introspect token with Keycloak server"""
        try:
            return self.keycloak_openid.introspect(token)
        except Exception as e:
            raise ValueError(f"Token introspection failed: {str(e)}")
    
    def get_user_info(self, token: str):
        """Get user info from Keycloak"""
        try:
            return self.keycloak_openid.userinfo(token)
        except Exception as e:
            raise ValueError(f"Failed to get user info: {str(e)}")
    
    def auth_url(self, redirect_uri: str, scope: str = "openid", state: str = None):
        """Generate Keycloak authorization URL"""
        auth_endpoint = f"{settings.KEYCLOAK_SERVER_URL}/realms/{settings.KEYCLOAK_REALM}/protocol/openid-connect/auth"
        
        params = {
            "client_id": settings.KEYCLOAK_CLIENT_ID,
            "redirect_uri": redirect_uri,
            "response_type": "code",
            "scope": scope,
        }
        
        if state:
            params["state"] = state
        
        return f"{auth_endpoint}?{urlencode(params)}"
    
    def token(self, grant_type: str, code: str = None, redirect_uri: str = None, refresh_token: str = None):
        """Exchange authorization code for tokens or refresh token"""
        if grant_type == "authorization_code":
            return self.keycloak_openid.token(
                grant_type=grant_type,
                code=code,
                redirect_uri=redirect_uri
            )
        elif grant_type == "refresh_token":
            return self.keycloak_openid.refresh_token(refresh_token)
        else:
            raise ValueError(f"Unsupported grant_type: {grant_type}")
    
    def userinfo(self, token: str):
        """Get user info from token (alias for get_user_info)"""
        return self.get_user_info(token)


# Singleton instance
keycloak_client = KeycloakClient()
