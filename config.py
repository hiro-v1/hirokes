import os
from dotenv import load_dotenv

load_dotenv()

API_ID = int(os.getenv("API_ID"))
API_HASH = os.getenv("API_HASH")
BOT_TOKEN = os.getenv("BOT_TOKEN")
OWNER_ID = 5432983527  # Pemilik bot tetap
MONGO_URI = os.getenv("MONGO_URI")
HUGGINGFACE_MODEL = os.getenv("HUGGINGFACE_MODEL", "cahya/gpt2-small-indonesian-522M")
HUGGINGFACE_API_KEY = os.getenv("HUGGINGFACE_API_KEY")
