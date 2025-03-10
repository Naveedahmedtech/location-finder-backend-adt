import os
from dotenv import load_dotenv

load_dotenv()  # Loads environment variables from .env if present

class Config:
    DEBUG = os.getenv("DEBUG", "False").lower() == "true"
    SECRET_KEY = os.getenv("SECRET_KEY", "dev_secret")
    
    # External services
    NOMINATIM_URL = os.getenv("NOMINATIM_URL", "https://nominatim.openstreetmap.org")
    OSRM_URL = os.getenv("OSRM_URL", "https://router.project-osrm.org")
    DATABASE_URI = os.getenv("DATABASE_URL")    # Possibly more config settings...
