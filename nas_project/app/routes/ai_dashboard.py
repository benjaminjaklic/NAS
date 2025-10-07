from flask import Blueprint, render_template, request, current_app
from flask_login import login_required, current_user
import os
import requests

import fitz  # PyMuPDF
import docx  # python-docx

ai_bp = Blueprint('ai', __name__)
AI_API_URL = "http://192.168.1.23:8000/summarize"

SUPPORTED_EXTENSIONS = [".txt", ".pdf", ".docx"]

def extract_text(filepath):
    ext = os.path.splitext(filepath)[1].lower()
    try:
        if ext == ".txt":
            with open(filepath, "r", encoding="utf-8", errors="ignore") as f:
                return f.read()
        elif ext == ".pdf":
            text = ""
            with fitz.open(filepath) as doc:
                for page in doc:
                    text += page.get_text()
            return text
        elif ext == ".docx":
            doc = docx.Document(filepath)
            return "\n".join([para.text for para in doc.paragraphs])
        else:
            return f"[Unsupported file type: {ext}]"
    except Exception as e:
        return f"[Error reading {ext} file: {str(e)}]"

@ai_bp.route("/ai", methods=["GET", "POST"])
@login_required
def ai_dashboard():
    summary = None
    error = None
    used_text = ""
    selected_file = ""
    all_files = []

    user_dir = os.path.join(current_app.config["UPLOAD_FOLDER"], str(current_user.id))

    if os.path.exists(user_dir):
        all_files = sorted([
            f for f in os.listdir(user_dir)
            if os.path.isfile(os.path.join(user_dir, f)) and os.path.splitext(f)[1].lower() in SUPPORTED_EXTENSIONS
        ])

    if request.method == "POST":
        language = request.form.get("language", "English")
        detail = request.form.get("detail", "medium")
        mode = request.form.get("mode", "summary")
        selected_file = request.form.get("selected_file", "")
        pasted_text = request.form.get("text", "")

        max_tokens = {
            "short": 100,
            "medium": 300,
            "long": 600
        }.get(detail, 300)

        instructions = {
            "summary": "Summarize the following text",
            "bullet": "List the key points of the following text",
            "analysis": "Analyze the text and summarize the author's argument",
            "opinion": "Summarize and provide your opinion on this text"
        }.get(mode, "Summarize the following text")

        if selected_file:
            filepath = os.path.join(user_dir, selected_file)
            if os.path.exists(filepath):
                used_text = extract_text(filepath)
            else:
                error = f"File '{selected_file}' not found."
        else:
            used_text = pasted_text

        prompt = f"{instructions} in {language}:\n{used_text.strip()}"

        try:
            res = requests.post(AI_API_URL, json={
                "text": prompt,
                "max_tokens": max_tokens,
                "language": language
            }, timeout=90)
            res.raise_for_status()
            summary = res.json().get("summary", "[No output]")
        except Exception as e:
            error = str(e)

    return render_template("ai/dashboard.html",
        summary=summary,
        error=error,
        all_txt_files=all_files,
        selected_file=selected_file
    )
