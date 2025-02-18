import os
from dotenv import load_dotenv

# Memuat variabel dari file .env
load_dotenv()

def get_env_variable(name, default=None, is_int=False):
    """Mengambil variabel dari environment, jika tidak ada pakai default"""
    value = os.getenv(name, default)
    if value is None:
        raise ValueError(f"❌ ERROR: Variabel lingkungan {name} belum diatur di .env")
    return int(value) if is_int else value

# Pastikan API_ID harus berupa integer
API_ID = get_env_variable("API_ID", is_int=True)
API_HASH = get_env_variable("API_HASH")
BOT_TOKEN = get_env_variable("BOT_TOKEN")
MONGO_URI = get_env_variable("MONGO_URI")
HUGGINGFACE_MODEL = get_env_variable("HUGGINGFACE_MODEL", "facebook/blenderbot-400M-distill")
