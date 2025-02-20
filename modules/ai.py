import requests
import json
from config import HUGGINGFACE_MODEL, HUGGINGFACE_API_KEY

def ai_response(user_input):
    """Menggunakan API Hugging Face untuk merespons pengguna dalam bahasa Indonesia."""
    API_URL = f"https://api-inference.huggingface.co/models/{HUGGINGFACE_MODEL}"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    
    payload = {
        "inputs": user_input,
        "parameters": {
            "max_length": 100,  # Batas panjang jawaban
            "temperature": 0.7,  # Kontrol kreativitas jawaban
            "top_p": 0.9,  # Sampling token
            "do_sample": True  # Aktifkan sampling
        }
    }
    
    try:
        response = requests.post(API_URL, headers=headers, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            if isinstance(result, list) and len(result) > 0 and "generated_text" in result[0]:
                return result[0]["generated_text"]
            else:
                return "Hmm... saya tidak tahu jawabannya. Coba tanya bang @hiro_v1."
        elif response.status_code == 503:
            return "⚠️ Model sedang sibuk atau dalam pemrosesan ulang. Silakan coba lagi nanti."
        else:
            return "Maaf, saya tidak dapat menjawab saat ini. Hubungi bang @hiro_v1 untuk bantuan."
    
    except requests.exceptions.RequestException as e:
        return f"⚠️ Terjadi kesalahan jaringan: {e}"
