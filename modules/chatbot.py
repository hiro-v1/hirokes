import os
import random

# **📌 Lokasi file respon**
RESPON_FILE = "modules/respon.txt"

# **📌 Fungsi untuk membaca file respon.txt**
def load_responses():
    """
    Membaca file respon.txt dan menyimpan dalam bentuk dictionary.
    Format: {"kata_kunci": ["respon1", "respon2", "respon3"]}
    """
    responses = {}
    
    if not os.path.exists(RESPON_FILE):
        return responses  # Jika file tidak ada, kembalikan dict kosong

    with open(RESPON_FILE, "r", encoding="utf-8") as file:
        for line in file:
            line = line.strip()
            if "=" in line:
                key, values = line.split("=", 1)
                key = key.strip().lower()
                values = [v.strip() for v in values.split("|")]
                responses[key] = values
    
    return responses

# **📌 Muat data dari file saat startup**
RESPONSES = load_responses()

# **📌 Fungsi untuk mencari jawaban berdasarkan kata kunci**
def chatbot_response(message):
    """
    Mencari kata kunci dalam pesan dan memberikan respons random.
    Jika tidak ada kata kunci yang cocok, bot akan menjawab default.
    """
    message = message.lower()

    # Cek setiap kata kunci di dalam pesan
    for keyword in RESPONSES:
        if keyword in message:  # Jika ada kata kunci dalam pesan
            return random.choice(RESPONSES[keyword])

    return "maksud?. bang @hiro_v1 tau ngga?"
