from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.routes import auth, otp
from app.database import Base, engine
from app.middleware.error_handler import setup_error_handlers
from app.utils.logger import setup_logger

# Setup logging
logger = setup_logger(log_file="logs/app.log")

# Create database tables
try:
    Base.metadata.create_all(bind=engine)
    logger.info("Database tables created successfully")
except Exception as e:
    logger.error(f"Failed to create database tables: {str(e)}", exc_info=True)

app = FastAPI(
    title="Auth Service",
    description="backend for fAIk React Native app",
    version="0.1.0"
)

# Setup error handlers
setup_error_handlers(app)

# CORS configuration for React Native app
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, replace with your app's exact origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Include routers
app.include_router(auth.router)
app.include_router(otp.router, prefix="/auth/otp")

@app.get("/")
def read_root():
    logger.info("Root endpoint accessed")
    return {"message": "fAIk's backend is running"}

@app.on_event("startup")
async def startup_event():
    logger.info("Application starting up")

@app.on_event("shutdown")
async def shutdown_event():
    logger.info("Application shutting down")