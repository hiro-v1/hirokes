import pymongo
import os

# Koneksi ke MongoDB
client = pymongo.MongoClient(os.getenv("MONGO_URI"))
db = client["hirokesbot"]

# Koleksi database
banned_words = db["banned_words"]
admin_list = db["admin_list"]
banned_users = db["banned_users"]
admin_groups = db["admin_groups"]  # ➕ Koleksi untuk menyimpan daftar grup admin

# ID Pemilik Bot (HARDCODE agar selalu bisa mengakses kontrol)
OWNER_ID = 5432983527

### ✅ Fungsi untuk Mengatur Admin ###
def add_admin(user_id):
    """Menambahkan admin ke database."""
    if user_id == OWNER_ID:
        return  # Pemilik bot tidak perlu ditambahkan sebagai admin
    
    if not admin_list.find_one({"user_id": user_id}):
        admin_list.insert_one({"user_id": user_id})

def remove_admin(user_id):
    """Menghapus admin dari database."""
    if user_id == OWNER_ID:
        return  # Pemilik bot tidak bisa dihapus sebagai admin
    
    admin_list.delete_one({"user_id": user_id})

def get_admins():
    """Mengambil daftar admin dari database dan menambahkan OWNER_ID."""
    admins = {admin["user_id"] for admin in admin_list.find({}, {"user_id": 1, "_id": 0})}
    admins.add(OWNER_ID)  # Pastikan pemilik bot selalu ada di daftar admin
    return admins

def is_admin(user_id):
    """Memeriksa apakah pengguna adalah admin."""
    return user_id in get_admins()

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

def is_banned(user_id):
    """Memeriksa apakah pengguna diblokir."""
    return user_id in get_banned_users()

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

### ✅ Fungsi untuk Mengatur Daftar Grup Admin ###
def add_admin_group(chat_id, chat_name):
    """Menambahkan grup ke daftar di mana bot adalah admin."""
    if not admin_groups.find_one({"chat_id": chat_id}):
        admin_groups.insert_one({"chat_id": chat_id, "chat_name": chat_name})
        
def save_admin_group(chat_id, chat_name):
    admin_groups.update_one(
         {"chat_id": chat_id},
         {"$set": {"chat_name": chat_name}},
         upsert=True
    )
    
def remove_admin_group(chat_id):
    """Menghapus grup dari daftar admin jika bot keluar atau dihapus sebagai admin."""
    admin_groups.delete_one({"chat_id": chat_id})

def get_admin_groups():
    """Mengambil daftar grup di mana bot menjadi admin."""
    return list(admin_groups.find({}, {"chat_id": 1, "chat_name": 1, "_id": 0}))

### ✅ Fungsi untuk Peringatan Pengguna ###
user_warnings = db["user_warnings"]

def add_warning(user_id):
    """Menambahkan peringatan untuk pengguna."""
    warning = user_warnings.find_one({"user_id": user_id})
    if warning:
        user_warnings.update_one({"user_id": user_id}, {"$inc": {"warnings": 1}})
    else:
        user_warnings.insert_one({"user_id": user_id, "warnings": 1})

def get_warnings(user_id):
    """Mengambil jumlah peringatan untuk pengguna."""
    warning = user_warnings.find_one({"user_id": user_id})
    return warning["warnings"] if warning else 0

def reset_warnings(user_id):
    """Mereset jumlah peringatan untuk pengguna."""
    user_warnings.delete_one({"user_id": user_id})
