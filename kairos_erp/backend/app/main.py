from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import meetings, contacts, finance, tax, mail_assistant, bot, rag, auth
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Kairos ERP, a B2B SaaS Multi-tenant ERP system.",
    version=settings.VERSION,
)

# Set up CORS middleware
# Setting allow_origins to ["*"] with allow_credentials=True is disallowed by Starlette.
# We explicitly set the origins that might hit this local backend.
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:5173",
        "http://127.0.0.1:5173",
        "http://localhost:3000"
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include Routers
app.include_router(meetings.router, prefix=settings.API_V1_STR)
app.include_router(contacts.router, prefix=settings.API_V1_STR)
app.include_router(finance.router, prefix=settings.API_V1_STR)
app.include_router(tax.router, prefix=settings.API_V1_STR)
app.include_router(mail_assistant.router, prefix=settings.API_V1_STR)
app.include_router(bot.router, prefix=settings.API_V1_STR)
app.include_router(rag.router, prefix=settings.API_V1_STR)
app.include_router(auth.router, prefix=settings.API_V1_STR)

from fastapi import Request
from app.routers.auth import auth_callback_google

# Alias for strict Google OAuth redirect URI matching port 8000
@app.get("/api/auth/callback/google")
def auth_callback_google_alias(request: Request, state: str = None, code: str = None, error: str = None):
    return auth_callback_google(request, state, code, error)

@app.get("/")
def read_root():
    return {"message": "Welcome to Kairos ERP API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
