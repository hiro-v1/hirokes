import pymongo
import os

# Koneksi ke MongoDB
client = pymongo.MongoClient(os.getenv("MONGO_URI"))
db = client["hirokesbot"]
banned_words = db["banned_words"]

# Daftar karakter Unicode terlarang
RESTRICTED_CHARS = "€¥£¢𝑎𝑏𝑐𝑑𝑒𝑓𝑔𝒉𝑖𝑗𝑘𝑙𝑚𝑛𝑜𝑝𝑞𝑟..."

def contains_restricted_chars(text):
    """Memeriksa apakah teks mengandung karakter terlarang"""
    return any(char in text for char in RESTRICTED_CHARS)

async def check_message(message):
    """Memeriksa apakah pesan mengandung kata terlarang"""
    text = message.text.lower()

    # Periksa database kata terlarang
    banned_list = banned_words.find({}, {"word": 1, "_id": 0})
    banned_set = {entry["word"] for entry in banned_list}

    # Periksa file `bl.txt`
    try:
        with open("bl.txt", "r", encoding="utf-8") as f:
            file_banned_words = set(f.read().splitlines())
        banned_set.update(file_banned_words)
    except FileNotFoundError:
        pass

    return any(word in text for word in banned_set)
