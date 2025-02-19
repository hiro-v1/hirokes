import requests
import json
from config import HUGGINGFACE_MODEL, HUGGINGFACE_API_KEY

def ai_response(user_input):
    """Menggunakan API Hugging Face untuk merespons pengguna."""
    API_URL = f"https://api-inference.huggingface.co/models/{HUGGINGFACE_MODEL}"
    headers = {"Authorization": f"Bearer {HUGGINGFACE_API_KEY}"}
    
    payload = {"inputs": user_input}
    response = requests.post(API_URL, headers=headers, json=payload)
    
    if response.status_code == 200:
        result = response.json()
        return result[0]['generated_text'] if result else "Saya tidak tahu bagaimana menjawab itu."
    else:
        return "Maaf, saya ga tau bingung tanya bang @hiro_v1 tuh."
