import os
import logging

LOG_FILE = "logs/bot.log"

def clean_logs():
    """Menghapus log otomatis setiap 7 hari"""
    try:
        if os.path.exists(LOG_FILE):
            open(LOG_FILE, "w").close()  # Kosongkan file log
            logging.info("Log berhasil dibersihkan.")
    except Exception as e:
        logging.error(f"Error saat membersihkan log: {e}")
