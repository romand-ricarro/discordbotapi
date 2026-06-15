# config.py
import os
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Discord Bot Configuration
DISCORD_BOT_TOKEN = os.getenv("DISCORD_BOT_TOKEN")
if not DISCORD_BOT_TOKEN:
    raise ValueError("DISCORD_BOT_TOKEN is required in .env file")

# API Configuration
API_HOST = os.getenv("API_HOST", "0.0.0.0")

# Handle PORT from cloud platforms (AWS, Railway, Heroku, etc.) or fallback to API_PORT
API_PORT = int(os.getenv("PORT") or os.getenv("API_PORT", "8000"))

# AWS-specific environment variables
AWS_REGION = os.getenv("AWS_REGION", "us-east-1")
ENVIRONMENT = os.getenv("ENVIRONMENT", "production")

API_KEY = os.getenv("API_KEY")
if not API_KEY:
    raise ValueError("API_KEY is required in .env file")