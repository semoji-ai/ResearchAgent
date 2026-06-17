from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import meetings, contacts, finance, tax, mail_assistant, bot, rag
from app.core.config import settings

app = FastAPI(
    title=settings.PROJECT_NAME,
    description="Backend API for Kairos ERP, a B2B SaaS Multi-tenant ERP system.",
    version=settings.VERSION,
)

# Set up CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Allows all origins, configure appropriately in production
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

# Include Routers
app.include_router(meetings.router, prefix=settings.API_V1_STR)
app.include_router(contacts.router, prefix=settings.API_V1_STR)
app.include_router(finance.router, prefix=settings.API_V1_STR)
app.include_router(tax.router, prefix=settings.API_V1_STR)
app.include_router(mail_assistant.router, prefix=settings.API_V1_STR)
app.include_router(bot.router, prefix=settings.API_V1_STR)
app.include_router(rag.router, prefix=settings.API_V1_STR)

@app.get("/")
def read_root():
    return {"message": "Welcome to Kairos ERP API"}

@app.get("/health")
def health_check():
    return {"status": "ok"}
