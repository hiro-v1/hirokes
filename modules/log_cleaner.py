import os
import time

def clean_logs():
    """Menghapus log yang lebih lama dari 7 hari"""
    log_file = "logs/bot.log"
    if os.path.exists(log_file):
        os.remove(log_file)
        open(log_file, "w").close()
