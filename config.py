import os
from dotenv import load_dotenv

# Memuat variabel dari file .env
load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
MONGO_URI = os.getenv("MONGO_URI")
HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "facebook/blenderbot-400M-distill")
