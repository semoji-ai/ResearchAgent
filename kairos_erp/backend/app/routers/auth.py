import os
import json
from fastapi import APIRouter, Request
from fastapi.responses import RedirectResponse
from google_auth_oauthlib.flow import Flow

router = APIRouter(
    prefix="/auth",
    tags=["Authentication"]
)

# Load client secrets.
# We need `drive.file` to upload parsing triggers, and potentially `gmail.modify` or `calendar` for other modules.
SCOPES = [
    'openid',
    'https://www.googleapis.com/auth/userinfo.email',
    'https://www.googleapis.com/auth/userinfo.profile',
    'https://www.googleapis.com/auth/drive.file'
]

CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), "..", "client_secret.json")

# Note: In production, redirect_uri must match exactly what is registered in the Google Cloud Console.
# And we must use a secure session mechanism to store the state.
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1' # For local development HTTP

def get_flow():
    # We must use the exact redirect_uri registered in Google Cloud Console.
    # The frontend running on port 3000 will need to handle this route,
    # or the user needs to update Google Console to point to the backend directly (e.g. 8000).
    return Flow.from_client_secrets_file(
        CLIENT_SECRETS_FILE,
        scopes=SCOPES,
        redirect_uri='http://localhost:3000/api/auth/callback/google'
    )

@router.get("/login/google")
def login_google():
    """
    Initiates the Google OAuth2 flow.
    Redirects the user to the Google consent screen.
    """
    if not os.path.exists(CLIENT_SECRETS_FILE):
        return {"error": "client_secret.json not found."}

    flow = get_flow()
    authorization_url, state = flow.authorization_url(
        access_type='offline',
        include_granted_scopes='true',
        prompt='consent' # Force consent to get refresh_token
    )

    # Normally we would save `state` to the user's session here to prevent CSRF.
    # For MVP, we will directly redirect.
    return RedirectResponse(authorization_url)

@router.get("/callback/google")
def auth_callback_google(request: Request, state: str = None, code: str = None, error: str = None):
    """
    Callback endpoint for Google OAuth.
    Exchanges the authorization code for access and refresh tokens.
    """
    if error:
        return {"error": error}

    flow = get_flow()
    flow.fetch_token(authorization_response=str(request.url))

    credentials = flow.credentials

    # Save the credentials to a local file database (simulating DB storage per company)
    # Using os.environ is thread-unsafe in a web server.
    token_path = os.path.join(os.path.dirname(__file__), "..", "..", "company_1_token.json")
    with open(token_path, "w") as f:
        f.write(credentials.to_json())

    # Redirect back to the frontend (which is now running on port 3000)
    return RedirectResponse("http://localhost:3000/?auth=success")

# Note: Because the user's provided JSON strictly requires the callback to be on port 3000,
# to make this work locally without changing their Google Cloud settings,
# they should either run the frontend on port 3000 or proxy requests from 3000 to 8000.
# For demonstration purposes, we are adding a route here that matches the exact URI path.
# If they point their redirect to the backend (http://localhost:8000/api/auth/callback/google),
# we add an alias router (we use FastAPI's main app to bypass the /api/v1/auth prefix):
# This will be registered directly in main.py instead.
