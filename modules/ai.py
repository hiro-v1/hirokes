from transformers import pipeline
from config import HUGGINGFACE_MODEL

# Inisialisasi model AI dari Hugging Face
try:
    ai_model = pipeline("text-generation", model=HUGGINGFACE_MODEL)
except Exception as e:
    print(f"❌ ERROR: Gagal memuat model AI: {e}")
    ai_model = None  # Hindari crash jika model gagal dimuat

def ai_response(user_input):
    """Membalas pesan menggunakan AI Hugging Face"""
    if ai_model is None:
        return "❌ Maaf, model AI tidak dapat dimuat."

    try:
        response = ai_model(user_input, max_length=100, num_return_sequences=1)
        return response[0]["generated_text"]
    except Exception as e:
        return f"❌ Error saat menjawab: {e}"
