import pymongo
import os

# Koneksi ke MongoDB
client = pymongo.MongoClient(os.getenv("MONGO_URI"))
db = client["hirokesbot"]

# Koleksi database
banned_words = db["banned_words"]
admin_list = db["admin_list"]
banned_users = db["banned_users"]

### ✅ Fungsi untuk Mengatur Admin ###
def add_admin(user_id):
    """Menambahkan admin ke database."""
    if not admin_list.find_one({"user_id": user_id}):
        admin_list.insert_one({"user_id": user_id})

def remove_admin(user_id):
    """Menghapus admin dari database."""
    admin_list.delete_one({"user_id": user_id})

def get_admins():
    """Mengambil daftar admin dari database."""
    return {admin["user_id"] for admin in admin_list.find({}, {"user_id": 1, "_id": 0})}

### ✅ Fungsi untuk Blokir & Unblokir Pengguna ###
def add_banned_user(user_id):
    """Menambahkan pengguna ke daftar blokir."""
    if not banned_users.find_one({"user_id": user_id}):
        banned_users.insert_one({"user_id": user_id})

def remove_banned_user(user_id):
    """Menghapus pengguna dari daftar blokir."""
    banned_users.delete_one({"user_id": user_id})

def get_banned_users():
    """Mengambil daftar pengguna yang diblokir."""
    return {user["user_id"] for user in banned_users.find({}, {"user_id": 1, "_id": 0})}

### ✅ Fungsi untuk Mengatur Kata Terlarang ###
def add_banned_word(word):
    """Menambahkan kata terlarang ke database."""
    if not banned_words.find_one({"word": word.lower()}):
        banned_words.insert_one({"word": word.lower()})

def remove_banned_word(word):
    """Menghapus kata terlarang dari database."""
    banned_words.delete_one({"word": word.lower()})

def get_banned_words():
    """Mengambil daftar kata terlarang."""
    return {entry["word"] for entry in banned_words.find({}, {"word": 1, "_id": 0})}
