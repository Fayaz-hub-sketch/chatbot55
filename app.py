import os
from pathlib import Path

from dotenv import load_dotenv
from flask import Flask, jsonify, render_template, request
from google import genai
from google.genai import types

from chatbot_config import SYSTEM_PROMPT, MODEL_NAME

load_dotenv()

app = Flask(__name__)
app.config["JSON_SORT_KEYS"] = False

api_key = os.getenv("GEMINI_API_KEY")
if not api_key:
    raise RuntimeError("GEMINI_API_KEY is not set in the environment.")

client = genai.Client(api_key=api_key)


@app.get("/")
def index():
    return render_template("index.html")


@app.post("/api/chat")
def chat():
    data = request.get_json(silent=True) or {}
    message = str(data.get("message", "")).strip()
    history = data.get("history", [])

    if not message:
        return jsonify({"error": "Please enter a question."}), 400

    # Keep the model focused on the selected study domain.
    conversation = []
    if isinstance(history, list):
        for item in history[-12:]:
            if not isinstance(item, dict):
                continue
            role = "Student" if item.get("role") == "user" else "Tutor"
            content = str(item.get("content", "")).strip()
            if content:
                conversation.append(f"{role}: {content}")

    context = "\n".join(conversation)
    user_prompt = (
        f"{context}\nStudent: {message}\nTutor:"
        if context
        else f"Student: {message}\nTutor:"
    )

    try:
        response = client.models.generate_content(
            model=MODEL_NAME,
            contents=user_prompt,
            config=types.GenerateContentConfig(
                system_instruction=SYSTEM_PROMPT,
                temperature=1.0,
            ),
        )
        answer = (response.text or "").strip()
        if not answer:
            answer = "I couldn't generate a response. Please try the study question again."
        return jsonify({"answer": answer})
    except Exception as exc:
        app.logger.exception("Gemini request failed")
        return jsonify({"error": "The AI service could not process the request right now."}), 502


if __name__ == "__main__":
    app.run()
