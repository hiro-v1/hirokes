import requests
import json
from config import OPENAI_API_KEY

API_URL = "https://api.openai.com/v1/chat/completions"
HEADERS = {"Authorization": f"Bearer {OPENAI_API_KEY}", "Content-Type": "application/json"}

def ai_response(user_input):
    """
    Menggunakan API OpenAI ChatGPT untuk menjawab pertanyaan (/ask).
    """
    payload = {
        "model": "gpt-3.5-turbo",
        "messages": [{"role": "user", "content": user_input}],
        "max_tokens": 200,
        "temperature": 0.7
    }
    
    try:
        response = requests.post(API_URL, headers=HEADERS, json=payload)
        
        if response.status_code == 200:
            result = response.json()
            return result["choices"][0]["message"]["content"].strip()
        elif response.status_code == 429:
            return "⚠️ Saya sedang sibuk, coba lagi nanti."
        else:
            return "Maaf, saya tidak dapat menjawab saat ini."
    
    except requests.exceptions.RequestException as e:
        return f"⚠️ Terjadi kesalahan jaringan: {e}"
