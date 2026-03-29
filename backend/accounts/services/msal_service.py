"""Microsoft OAuth service using MSAL."""

import httpx
import msal
from django.conf import settings

AUTHORITY = f"https://login.microsoftonline.com/{settings.MS_AZURE_TENANT_ID}"
SCOPES = ["User.Read"]
GRAPH_ME_ENDPOINT = "https://graph.microsoft.com/v1.0/me"


def get_msal_app() -> msal.ConfidentialClientApplication:
    """Create MSAL confidential client application."""
    return msal.ConfidentialClientApplication(
        client_id=settings.MS_AZURE_CLIENT_ID,
        client_credential=settings.MS_AZURE_SECRET,
        authority=AUTHORITY,
    )


def get_auth_url(state: str) -> str:
    """Generate Microsoft OAuth authorization URL."""
    app = get_msal_app()
    result = app.get_authorization_request_url(
        scopes=SCOPES,
        redirect_uri=settings.MS_AZURE_REDIRECT_URI,
        state=state,
    )
    return result


def exchange_code_for_tokens(code: str) -> dict:
    """Exchange authorization code for access/refresh tokens."""
    app = get_msal_app()
    result = app.acquire_token_by_authorization_code(
        code=code,
        scopes=SCOPES,
        redirect_uri=settings.MS_AZURE_REDIRECT_URI,
    )
    if "error" in result:
        raise ValueError(f"Token exchange failed: {result.get('error_description', result['error'])}")
    return result


async def fetch_user_profile(access_token: str) -> dict:
    """Fetch user profile from Microsoft Graph API."""
    async with httpx.AsyncClient() as client:
        response = await client.get(
            GRAPH_ME_ENDPOINT,
            headers={"Authorization": f"Bearer {access_token}"},
        )
        response.raise_for_status()
        return response.json()
