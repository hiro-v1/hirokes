from transformers import pipeline
from config import HUGGINGFACE_MODEL

# Inisialisasi model AI dari Hugging Face
ai_model = pipeline("conversational", model=HUGGINGFACE_MODEL)

def ai_response(user_input):
    """Membalas pesan menggunakan AI Hugging Face"""
    try:
        response = ai_model(user_input)
        return response[0]["generated_text"]
    except Exception as e:
        return "Maaf, saya tidak bisa menjawab coba tanya bang hiro."
