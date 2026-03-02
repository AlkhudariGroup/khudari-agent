import os
from dotenv import load_dotenv

load_dotenv()

from flask import Flask, jsonify, render_template, request
from openai import OpenAI
from groq import Groq
import httpx
import google.generativeai as genai

app = Flask(__name__)

import json
import time

# Load Settings
SETTINGS_FILE = 'settings.json'

def load_settings():
    try:
        with open(SETTINGS_FILE, 'r') as f:
            data = json.load(f)
            # Fallback to env vars if empty in file
            if not data.get("openai_api_key"):
                data["openai_api_key"] = os.getenv("OPENAI_API_KEY", "")
            if not data.get("gemini_api_key"):
                data["gemini_api_key"] = os.getenv("GEMINI_API_KEY", "")
            if not data.get("groq_api_key"):
                data["groq_api_key"] = os.getenv("GROQ_API_KEY", "")
            return data
    except FileNotFoundError:
        return {
            "agent_name": "e-Commero",
            "wake_words": "e-commero, commerco, commercial, belal, doctor",
            "response_phrase": "Yes Dr. Belal, I am here.",
            "system_prompt": "You are e-Commero, a helpful and intelligent AI assistant. Answer briefly in one sentence.",
            "ollama_model": "llama2-uncensored",
            "ollama_base_url": os.getenv("OLLAMA_BASE_URL", "http://localhost:11434/v1"),
            "openai_api_key": os.getenv("OPENAI_API_KEY", ""),
            "gemini_api_key": os.getenv("GEMINI_API_KEY", ""),
            "groq_api_key": os.getenv("GROQ_API_KEY", ""),
            "providers": {
                "openai": True,
                "gemini": True,
                "ollama": True,
                "groq": False
            },
            "temperature": 0.7,
            "max_tokens": 150
        }

def save_settings(new_settings):
    with open(SETTINGS_FILE, 'w') as f:
        json.dump(new_settings, f, indent=4)

def ai_bot_response(prompt):
    settings = load_settings()
    providers = settings.get("providers", {})
    temp = float(settings.get("temperature", 0.7))
    max_tok = int(settings.get("max_tokens", 150))
    start_time = time.time()
    
    # Priority 1: Groq (Cloud) - Ultra Fast
    if providers.get("groq") and settings.get("groq_api_key"):
        try:
            print(f"Using Groq Cloud for: {prompt[:30]}...")
            client = Groq(api_key=settings["groq_api_key"])
            response = client.chat.completions.create(
                model="mixtral-8x7b-32768",
                messages=[
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tok,
                temperature=temp,
                timeout=5.0
            )
            duration = time.time() - start_time
            print(f"Groq response in {duration:.2f}s")
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Groq Error: {e}")
            # Fall through to next provider

    # Priority 2: Gemini (Cloud) - Fast & Smart
    if providers.get("gemini") and settings.get("gemini_api_key"):
        try:
            print(f"Using Gemini Cloud for: {prompt[:30]}...")
            genai.configure(api_key=settings["gemini_api_key"])
            model = genai.GenerativeModel('gemini-pro')
            
            # Use raw prompt without system instruction wrapper
            full_prompt = prompt
            
            # Configure minimal safety blocking (as permissive as possible)
            safety_settings = [
                {
                    "category": "HARM_CATEGORY_HARASSMENT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_HATE_SPEECH",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_SEXUALLY_EXPLICIT",
                    "threshold": "BLOCK_NONE"
                },
                {
                    "category": "HARM_CATEGORY_DANGEROUS_CONTENT",
                    "threshold": "BLOCK_NONE"
                }
            ]
            
            generation_config = genai.types.GenerationConfig(
                temperature=temp,
                max_output_tokens=max_tok
            )
            
            response = model.generate_content(full_prompt, safety_settings=safety_settings, generation_config=generation_config)
            duration = time.time() - start_time
            print(f"Gemini response in {duration:.2f}s")
            return response.text.strip()
        except Exception as e:
            print(f"Gemini Error: {e}")
            # Fall through to next provider

    # Priority 3: OpenAI (Cloud) - Reliable
    if providers.get("openai") and settings.get("openai_api_key"):
        try:
            print(f"Using OpenAI Cloud for: {prompt[:30]}...")
            client = OpenAI(api_key=settings["openai_api_key"])
            response = client.chat.completions.create(
                model="gpt-3.5-turbo",
                messages=[
                    # Raw user input only, no system role
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tok,
                temperature=temp,
                timeout=5.0
            )
            duration = time.time() - start_time
            print(f"OpenAI response in {duration:.2f}s")
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"OpenAI Error: {e}")
            # Fall through to next provider

    # Priority 4: Ollama (Local/Remote) - Fallback
    if providers.get("ollama"):
        try:
            base_url = settings.get("ollama_base_url") or "http://localhost:11434/v1"
            print(f"Using Ollama at {base_url}...")
            client = OpenAI(base_url=base_url, api_key="ollama")
            
            response = client.chat.completions.create(
                model=settings.get("ollama_model", "llama2"),
                messages=[
                    # Raw user input only, no system role
                    {"role": "user", "content": prompt},
                ],
                max_tokens=max_tok,
                temperature=temp,
                timeout=20.0 # Local models can be slow
            )
            duration = time.time() - start_time
            print(f"Ollama response in {duration:.2f}s")
            return response.choices[0].message.content.strip()
        except Exception as e:
            print(f"Ollama Error: {e}")

    # Fallback if everything fails
    return "I am currently offline. Please check my internet connection or API keys."


@app.route("/")
def home():
    settings = load_settings()
    # Pass settings to template for dynamic wake word and custom response
    return render_template("index.html", settings=settings)

@app.route("/dashboard")
def dashboard():
    return render_template("dashboard.html", settings=load_settings())

@app.route("/api/settings", methods=["GET", "POST"])
def settings_api():
    if request.method == "POST":
        incoming = request.json or {}
        current = load_settings()
        if not isinstance(current.get("providers"), dict):
            current["providers"] = {"openai": True, "gemini": True, "ollama": True}
        if isinstance(incoming.get("providers"), dict):
            current["providers"].update(incoming["providers"])
            incoming.pop("providers", None)
        current.update(incoming)
        save_settings(current)
        return jsonify({"status": "success", "settings": current})
    return jsonify(load_settings())

def check_openai_status(key: str):
    if not key:
        return {"configured": False, "connected": False}
    try:
        headers = {"Authorization": f"Bearer {key}"}
        r = httpx.get("https://api.openai.com/v1/models", headers=headers, timeout=5)
        return {"configured": True, "connected": r.status_code == 200}
    except Exception:
        return {"configured": True, "connected": False}

def check_gemini_status(key: str):
    if not key:
        return {"configured": False, "connected": False}
    try:
        url = f"https://generativelanguage.googleapis.com/v1/models?key={key}"
        r = httpx.get(url, timeout=5)
        return {"configured": True, "connected": r.status_code == 200}
    except Exception:
        return {"configured": True, "connected": False}

def check_ollama_status(base_url: str):
    if not base_url:
        base_url = "http://localhost:11434/v1"
    try:
        url = base_url.rstrip("/") + "/models"
        r = httpx.get(url, timeout=5)
        if r.status_code == 200:
            return {"configured": True, "connected": True}
        alt = base_url.replace("/v1", "/api/tags")
        rr = httpx.get(alt, timeout=5)
        return {"configured": True, "connected": rr.status_code == 200}
    except Exception:
        return {"configured": True, "connected": False}

def check_groq_status(key: str):
    if not key:
        return {"configured": False, "connected": False}
    try:
        headers = {"Authorization": f"Bearer {key}"}
        r = httpx.get("https://api.groq.com/openai/v1/models", headers=headers, timeout=5)
        return {"configured": True, "connected": r.status_code == 200}
    except Exception:
        return {"configured": True, "connected": False}

@app.route("/api/provider_status", methods=["GET"])
def provider_status():
    settings = load_settings()
    providers = settings.get("providers", {})
    
    status = {
        "openai": {
            "active": providers.get("openai", False),
            **check_openai_status(settings.get("openai_api_key"))
        },
        "gemini": {
            "active": providers.get("gemini", False),
            **check_gemini_status(settings.get("gemini_api_key"))
        },
        "ollama": {
            "active": providers.get("ollama", False),
            **check_ollama_status(settings.get("ollama_base_url"))
        },
        "groq": {
            "active": providers.get("groq", False),
            **check_groq_status(settings.get("groq_api_key"))
        }
    }
    return jsonify(status)

@app.route("/get_response", methods=["POST"])
def get_response():
    data = request.json
    user_input = data.get("user_input")
    bot_response = ai_bot_response(user_input)
    return jsonify({"response": bot_response})

@app.route("/transcribe", methods=["POST"])
def transcribe_audio():
    if 'file' not in request.files:
        return jsonify({"error": "No file uploaded"}), 400
    
    file = request.files['file']
    settings = load_settings()
    
    # Use Groq Whisper Large V3 for ultra-fast transcription
    if settings.get("providers", {}).get("groq") and settings.get("groq_api_key"):
        try:
            print("Transcribing with Groq Whisper Large V3...")
            client = Groq(api_key=settings["groq_api_key"])
            
            # Save temp file for API
            temp_filename = "temp_audio.webm"
            file.save(temp_filename)
            
            with open(temp_filename, "rb") as audio_file:
                transcription = client.audio.transcriptions.create(
                    file=(temp_filename, audio_file.read()),
                    model="whisper-large-v3-turbo",
                    response_format="json",
                    language="en", # Auto-detect or user pref
                    temperature=0.0
                )
            
            # Cleanup
            os.remove(temp_filename)
            print(f"Transcription: {transcription.text[:50]}...")
            return jsonify({"text": transcription.text})
            
        except Exception as e:
            print(f"Groq Transcription Error: {e}")
            return jsonify({"error": str(e)}), 500
    
    return jsonify({"error": "Groq provider not configured"}), 503



if __name__ == "__main__":
    app.run(debug=True, port=os.getenv("HTTP_PORT", 5000))
