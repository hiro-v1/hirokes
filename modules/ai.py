import requests
import json
from config import HUGGINGFACE_MODEL, HUGGINGFACE_API_KEY

# Konfigurasi API Hugging Face
API_URL = f"https://api-inference.huggingface.co/models/{HUGGINGFACE_MODEL}"
headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}

def ai_response(user_input):
    """Menggunakan API Hugging Face untuk menjawab pertanyaan detail (/ask)."""
    payload = {
        "inputs": user_input,
        "parameters": {
            "max_length": 200,  # Jawaban lebih panjang
            "temperature": 0.7,  # Kontrol kreativitas
            "top_p": 0.9,
            "do_sample": True
        }
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0 and "generated_text" in result[0]:
                return result[0]["generated_text"].strip()
            else:
                return "Hmm... saya tidak tahu jawabannya. Coba tanya bang @hiro_v1."
        elif response.status_code == 503:
            return "⚠️ aduh saya sibuk tunggu bentar. coba tanya bang @hiro_v1 aja."
        else:
            return "Maaf, saya tidak dapat menjawab saat ini. Hubungi bang @hiro_v1 untuk bantuan."
    
    except requests.exceptions.RequestException as e:
        return f"⚠️ Terjadi kesalahan jaringan: {e}"
        

def simple_ai_response(user_input):
    """Menghasilkan respons singkat untuk percakapan umum (tanpa /ask)."""
    payload = {
        "inputs": user_input,
        "parameters": {
            "max_length": 50,  # Jawaban lebih pendek
            "temperature": 0.6,  # Kurangi variasi jawaban agar lebih natural
            "top_p": 0.8,
            "do_sample": True
        }
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0 and "generated_text" in result[0]:
                response_text = result[0]["generated_text"].split(".")[0]  # Ambil 1 kalimat pertama
                return response_text.strip() if response_text else "Maksudnya?"
        elif response.status_code == 503:
            return "⚠️ gatau yah, coba lagi nanti."
        else:
            return "Maksudnya?"
    
    except requests.exceptions.RequestException as e:
        return f"⚠️ Terjadi kesalahan jaringan: {e}"
