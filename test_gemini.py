import os
from dotenv import load_dotenv
import google.generativeai as genai

load_dotenv()
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY")

genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel("gemini-2.0-flash")

try:
    chat = model.start_chat()
    response = chat.send_message("Salom")
    print("Gemini Response:", response.text)
except Exception as e:
    print("Gemini Error:", e)
