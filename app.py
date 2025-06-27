import os
import uuid
import re
from datetime import datetime
from flask import Flask, render_template, redirect, url_for, flash, request, session, send_from_directory
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager, login_user, logout_user, login_required, current_user
from flask_bcrypt import Bcrypt
from flask_migrate import Migrate
from fpdf import FPDF
from deep_translator import GoogleTranslator
from bs4 import BeautifulSoup
import pdfplumber
from weasyprint import HTML, CSS
from models import User, Translation
from extensions import db, bcrypt, login_manager

TRANSLATED_FOLDER = os.path.join(os.getcwd(), 'translated')

# Create Flask app
app = Flask(__name__)
app.config['SECRET_KEY'] = 'your_secret_key'
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///site.db'
migrate = Migrate()

db.init_app(app)
bcrypt.init_app(app)
login_manager.init_app(app)
migrate.init_app(app, db)

from models import User, Translation  # ✅ import after init_app

app.config['MAX_CONTENT_LENGTH'] = 50 * 1024 * 1024  # 50MB upload limit

import tempfile
TEMP_FOLDER = os.path.join(tempfile.gettempdir(), "pdfgenie-temp")
os.makedirs(TEMP_FOLDER, exist_ok=True)

def inject_user_info():
    from flask_login import current_user
    name = None
    if current_user.is_authenticated:
        name = current_user.name or current_user.username
    return {'current_user_info': name}

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
UPLOAD_FOLDER = os.path.join(BASE_DIR, "uploads")
TRANSLATED_FOLDER = os.path.join(BASE_DIR, "translated_pdfs")

os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRANSLATED_FOLDER, exist_ok=True)

TECHNICAL_TERMS = [
    "PDF", "API", "Python", "Flask", "HTML", "CSS", "JavaScript", "SQL", "JSON", "XML",
    "POST", "GET", "PUT", "DELETE", "UUID", "URL", "HTTP", "HTTPS", "TXT", "DOCX"
]

def extract_text(file_path, ext):
    ext = ext.lower()
    if ext == ".txt":
        with open(file_path, "r", encoding="utf-8") as f:
            return f.read()
    elif ext in [".html", ".htm"]:
        with open(file_path, "r", encoding="utf-8") as f:
            soup = BeautifulSoup(f, "html.parser")
            return soup.get_text(separator="\n")
    elif ext == ".pdf":
        extracted_text = ""
        with pdfplumber.open(file_path) as pdf:
            for page in pdf.pages:
                page_text = page.extract_text() or ""
                extracted_text += page_text + "\n"
        return extracted_text
    return None

def preserve_terms(text, terms):
    placeholders = {}
    for idx, term in enumerate(terms):
        placeholder = f"[[TECH_TERM_{idx}]]"
        pattern = r'\b' + re.escape(term) + r'\b'
        text, count = re.subn(pattern, placeholder, text)
        if count > 0:
            placeholders[placeholder] = term
    return text, placeholders

def restore_terms(text, placeholders):
    for placeholder, term in placeholders.items():
        text = re.sub(re.escape(placeholder), term, text, flags=re.IGNORECASE)
    return text

import os
os.environ["FONTCONFIG_FILE"] = "/dev/null"
import os
import html
from base64 import b64encode
from weasyprint import HTML

def generate_pdf(text, output_path, lang="en"):
    if not text.strip():
        print("⚠️ Translated text is empty. Skipping PDF generation.")
        return

    # Step 1: Escape HTML entities and format line breaks
    cleaned_text = html.escape(text).replace('\n', '<br>')

    # Step 2: Define font based on language
    font_map = {
        "hi": "NotoSansDevanagari",
        "mr": "NotoSansDevanagari",
        "ne": "NotoSansDevanagari",
        "default": "InterDisplay"
    }
    font_family = font_map.get(lang, font_map["default"])
    font_file = f"{font_family}-Regular.ttf"
    font_path = os.path.abspath(os.path.join("static", "fonts", font_file))

    print(f"🔤 Font selected: {font_family}")
    print(f"📁 Font path: {font_path}")

    # Step 3: Embed font with base64 or fallback to system default
    if not os.path.exists(font_path):
        print("❌ Font file is missing. Falling back to system sans-serif.")
        font_css = """
        body {
            font-family: sans-serif;
            font-size: 16px;
            line-height: 1.6;
            color: #1e293b;
        }
        """
    else:
        if any(ord(char) > 127 for char in cleaned_text):
            print("🧪 Non-Latin characters detected. Embedding Unicode font.")

        with open(font_path, "rb") as f:
            encoded_font = b64encode(f.read()).decode("utf-8")

        font_css = f"""
        @font-face {{
            font-family: '{font_family}';
            src: url(data:font/truetype;charset=utf-8;base64,{encoded_font}) format('truetype');
        }}
        body {{
            font-family: '{font_family}', sans-serif;
            font-size: 16px;
            line-height: 1.6;
            color: #1e293b;
        }}
        """

    # Step 4: Build the HTML content
    html_content = f"""
    <html>
        <head>
            <meta charset="utf-8">
            <style>{font_css}</style>
        </head>
        <body>{cleaned_text}</body>
    </html>
    """

    # Step 5: Write the PDF
    try:
        print(f"📝 Writing PDF to: {output_path}")
        HTML(string=html_content, base_url=os.getcwd()).write_pdf(output_path)

        if os.path.exists(output_path):
            print(f"✅ PDF created at {output_path}")
            print(f"📦 Size: {os.path.getsize(output_path):,} bytes")
        else:
            print("⚠️ No error thrown, but output file not found.")

    except Exception as e:
        print("❌ PDF generation failed:", type(e).__name__)
        print("🪵 Details:", str(e))

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        password = bcrypt.generate_password_hash(request.form["password"]).decode("utf-8")

        if db.session.query(User).filter((User.username == username) | (User.email == email)).first():
            flash("Username or email already exists.")
            return render_template("register.html")

        user = User(username=username, email=email, password=password)
        db.session.add(user)
        db.session.commit()
        flash("Registration successful! Please log in.")
        return redirect(url_for("login"))

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        user = db.session.query(User).filter_by(username=request.form["username"]).first()
        if user and bcrypt.check_password_hash(user.password, request.form["password"]):
            login_user(user)
            flash("Login successful!")
            return redirect(url_for("home"))
        flash("Invalid credentials")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    return redirect(url_for("login"))

from concurrent.futures import ThreadPoolExecutor
@app.route("/", methods=["GET", "POST"])
@login_required
def home():
    error = None
    SUPPORTED_FONT_LANGUAGES = {
        "en": "English",
        "fr": "French",
        "de": "German",
        "es": "Spanish",
        "it": "Italian",
        "hi": "Hindi",
        "mr": "Marathi",
        "ne": "Nepali",
        "zh-CN": "Chinese (Simplified)"
    }

    if request.method == "POST":
        file = request.files.get("pdfs")
        output_lang = request.form.get("output_lang", "en")

        if not file:
            error = "No file uploaded"
            return render_template("index.html", error=error, languages=SUPPORTED_FONT_LANGUAGES)

        filename = file.filename
        ext = os.path.splitext(filename)[1].lower()
        unique_id = uuid.uuid4().hex[:6]
        file_path = os.path.join(UPLOAD_FOLDER, f"{unique_id}_{filename}")
        file.save(file_path)

        extracted_text = extract_text(file_path, ext)
        if not extracted_text or not extracted_text.strip():
            error = "Unsupported or unreadable file type, or no text found."
            return render_template("index.html", error=error, languages=SUPPORTED_FONT_LANGUAGES)

        prepped_text, placeholders = preserve_terms(extracted_text, TECHNICAL_TERMS)

        try:
            chunk_size = 4800
            chunks = [prepped_text[i:i + chunk_size] for i in range(0, len(prepped_text), chunk_size)]
            chunks = [c for c in chunks if c.strip()]

            def translate_chunk(chunk):
                return GoogleTranslator(source="auto", target=output_lang).translate(chunk)

            with ThreadPoolExecutor(max_workers=4) as executor:
                results = list(executor.map(translate_chunk, chunks))

            translated_text = "\n".join(results)
        except Exception as e:
            error = f"Translation failed: {str(e)}"
            return render_template("index.html", error=error, languages=SUPPORTED_FONT_LANGUAGES)

        translated_text = restore_terms(translated_text, placeholders)

        # 🗂️ Save translated text to a temp file instead of session
        temp_id = uuid.uuid4().hex
        temp_file_path = os.path.join(TEMP_FOLDER, f"{temp_id}.txt")

        try:
            with open(temp_file_path, "w", encoding="utf-8") as f:
                f.write(translated_text)
        except Exception as e:
            error = f"Failed to store translated file: {str(e)}"
            return render_template("index.html", error=error, languages=SUPPORTED_FONT_LANGUAGES)

        # ✅ Store references only
        session["translated_file_id"] = temp_id
        session["output_lang"] = output_lang
        session["original_name"] = filename

        return redirect(url_for("rename"))

    return render_template("index.html", error=error, languages=SUPPORTED_FONT_LANGUAGES)
import time
from datetime import datetime

def run_translation_async(app, translation_id, translated_text, translated_pdf_path, output_lang, db, Translation):
    with app.app_context():
        start = time.time()
        print(f"🧞 Starting async thread for ID: {translation_id}")

        try:
            print("🌍 Translated text preview:", translated_text[:150], "...")
            generate_pdf(translated_text, translated_pdf_path, output_lang)
            duration = time.time() - start
            file_ok = os.path.exists(translated_pdf_path)

            translation = Translation.query.get(translation_id)
            if translation:
                translation.timestamp = datetime.utcnow()
                translation.duration_seconds = round(duration, 4) if file_ok else None
                db.session.commit()

            if file_ok:
                print(f"✅ Translation completed for ID {translation_id} in {duration:.2f}s")
            else:
                print("⚠️ PDF not found after generation — marked as pending.")
        except Exception as e:
            print("❌ Translation thread crashed:", type(e).__name__)
            print("🪵 Error details:", str(e))
            translation = Translation.query.get(translation_id)
            if translation:
                translation.timestamp = datetime.utcnow()
                translation.duration_seconds = None
                db.session.commit()


@app.route("/rename", methods=["GET", "POST"])
@login_required
def rename():
    temp_file_id = session.get("translated_file_id")
    output_lang = session.get("output_lang")
    original_name = session.get("original_name")

    if not temp_file_id or not output_lang or not original_name:
        flash("Session expired or missing data. Please try again.", "danger")
        return redirect(url_for("home"))

    temp_file_path = os.path.join(TEMP_FOLDER, f"{temp_file_id}.txt")

    try:
        with open(temp_file_path, "r", encoding="utf-8") as f:
            translated_text = f.read()
    except Exception as e:
        flash(f"Could not load translated text: {str(e)}", "danger")
        return redirect(url_for("home"))

    if request.method == "POST":
        custom_name = request.form.get("custom_name", "").strip()
        if not custom_name:
            flash("Please provide a filename.", "warning")
            return redirect(url_for("rename"))

        safe_name = secure_filename(custom_name)
        translated_filename = f"{safe_name}.pdf"

        existing = Translation.query.filter_by(
            user_id=current_user.id,
            translated_name=translated_filename
        ).first()
        if existing:
            flash("You’ve already used this file name. Please choose a different one.", "danger")
            return redirect(url_for("rename"))

        translated_pdf_path = os.path.join(TRANSLATED_FOLDER, translated_filename)

        translation = Translation(
            user_id=current_user.id,
            original_name=original_name,
            translated_name=translated_filename,
            language=output_lang,
            timestamp=datetime.utcnow()
        )
        db.session.add(translation)
        db.session.commit()

        # Start background thread using translated text content
        thread = Thread(
            target=run_translation_async,
            args=(app, translation.id, translated_text, translated_pdf_path, output_lang, db, Translation)
        )
        thread.start()

        session["processing_file_id"] = translation.id

        # Clean up
        session.pop("translated_file_id", None)
        session.pop("original_name", None)
        session.pop("output_lang", None)

        try:
            os.remove(temp_file_path)
        except Exception as e:
            print(f"⚠️ Could not delete temp file: {str(e)}")

        flash("Your file is being prepared...", "info")
        return redirect(url_for("processing"))

    return render_template("rename.html", original_name=original_name, output_lang=output_lang)

from datetime import timezone

try:
    from zoneinfo import ZoneInfo  # Python 3.9+
except ImportError:
    from pytz import timezone as ZoneInfo  # fallback for older versions

@app.route("/dashboard")
@login_required
def dashboard():
    translations = (
        db.session.query(Translation)
        .filter_by(user_id=current_user.id)
        .order_by(Translation.timestamp.desc())
        .all()
    )

    ist = ZoneInfo("Asia/Kolkata")

    for t in translations:
        # Handle timestamp conversion
        if t.timestamp:
            if t.timestamp.tzinfo is None:
                utc_timestamp = t.timestamp.replace(tzinfo=timezone.utc)
            else:
                utc_timestamp = t.timestamp
            t.local_time = utc_timestamp.astimezone(ist)
            t.date_only = t.local_time.date()
            # Ensure all timestamps show seconds consistently
            t.local_time_str = t.local_time.strftime("%d %b %Y, %I:%M:%S %p")
        else:
            t.local_time = None
            t.local_time_str = "—"

        # File existence check
        translated_path = os.path.join(TRANSLATED_FOLDER, t.translated_name)
        t.file_exists = os.path.exists(translated_path)

        # Duration display
        t.duration_display = (
            f"{t.duration_seconds:.2f}s" if t.duration_seconds else "⏳ pending"
        )

        print(">> DASHBOARD DATA:", {
            "original_name": t.original_name,
            "translated_name": t.translated_name,
            "language": t.language,
            "local_time": t.local_time_str,
            "duration": t.duration_display,
            "file_exists": t.file_exists,
            "id": t.id
        })

    return render_template("dashboard.html", translations=translations)

@app.route("/profile")
@login_required
def profile():
    documents = Translation.query.filter_by(user_id=current_user.id).all()
    return render_template("profile.html", user=current_user, documents=documents)

@app.route("/delete/<int:file_id>", methods=["POST"])
@login_required
def delete_file(file_id):
    translation = Translation.query.filter_by(id=file_id, user_id=current_user.id).first()

    if not translation:
        flash("File not found or access denied.", "danger")
        return redirect(url_for("profile"))

    # Delete the translated PDF file
    try:
        file_path = os.path.join(TRANSLATED_FOLDER, translation.translated_name)
        if os.path.exists(file_path):
            os.remove(file_path)
    except Exception as e:
        print("⚠️ Error deleting file:", e)

    db.session.delete(translation)
    db.session.commit()

    flash("File deleted successfully.", "success")
    return redirect(url_for("profile"))

@app.route("/processing")
@login_required
def processing():
    file_id = session.get("processing_file_id")
    print("🧭 Processing ID from session:", file_id)

    if not file_id:
        flash("Processing session expired.", "warning")
        return redirect(url_for("dashboard"))

    translation = Translation.query.filter_by(
        id=file_id,
        user_id=current_user.id
    ).first()

    if not translation:
        flash("Translation not found.", "danger")
        return redirect(url_for("dashboard"))

    translated_path = os.path.join(TRANSLATED_FOLDER, translation.translated_name)
    file_ready = os.path.exists(translated_path)

    if file_ready:
        session.pop("processing_file_id", None)

    return render_template(
        "processing.html",
        still_processing=not file_ready,
        translated_output=translation.translated_name if file_ready else None,
        original_name=translation.original_name,
        output_lang=translation.language,
        duration=translation.duration_seconds
    )

from datetime import datetime
from threading import Thread
from flask import (
    Flask, request, redirect, url_for, flash, session,
    send_from_directory, render_template
)
from werkzeug.utils import secure_filename
import traceback
from weasyprint import HTML

UPLOAD_FOLDER = os.path.join(os.getcwd(), "uploads")
TRANSLATED_FOLDER = os.path.join(os.getcwd(), "translated")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(TRANSLATED_FOLDER, exist_ok=True)

def run_translation_async(app, translation_id, content, translated_path, target_lang, db, Translation):
    with app.app_context():
        try:
            start_time = datetime.utcnow()
            os.makedirs(os.path.dirname(translated_path), exist_ok=True)

            try:
                print("🌍 Translated text preview:", content[:150])
                generate_pdf(content, translated_path, lang=target_lang)
            except Exception as e:
                print("❌ Error generating PDF:", e)

            # SQLAlchemy 2.x compatible way:
            translation = db.session.get(Translation, translation_id)
            if translation:
                translation.timestamp = datetime.utcnow()
                translation.duration_seconds = (translation.timestamp - start_time).total_seconds()
                db.session.commit()
                print(f"📦 Updated DB for ID {translation_id}")
            else:
                print(f"⚠️ Translation ID {translation_id} not found")

        except Exception:
            print("❌ Error in async translation thread:")
            traceback.print_exc()

# === Upload + Start Translation Route ===
@app.route("/translate", methods=["POST"])
@login_required
def translate_file():
    uploaded_file = request.files.get("file")
    target_lang = request.form.get("target_lang")
    new_filename = (request.form.get("new_filename") or "").strip()

    if not uploaded_file or not target_lang:
        flash("Missing file or language.")
        return redirect(url_for("dashboard"))

    filename = secure_filename(uploaded_file.filename)
    original_path = os.path.join(UPLOAD_FOLDER, filename)
    try:
        uploaded_file.save(original_path)
    except Exception as e:
        flash("Failed to save uploaded file.")
        print("❌ File save error:", e)
        return redirect(url_for("dashboard"))

    name_root, ext = os.path.splitext(filename)
    timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
    translated_name = f"{new_filename or name_root}_translated_{timestamp}{ext}"
    translated_path = os.path.join(TRANSLATED_FOLDER, translated_name)

    new_translation = Translation(
        original_name=filename,
        translated_name=translated_name,
        language=target_lang,
        timestamp=datetime.utcnow(),
        user_id=current_user.id
    )
    db.session.add(new_translation)
    db.session.commit()

    print("✅ Translation saved:", new_translation.id, translated_name)

    Thread(target=run_translation_async, args=(
        app,
        new_translation.id,
        original_path,
        translated_path,
        translated_name,
        target_lang,
        db
    )).start()

    session["processing_file_id"] = new_translation.id
    return redirect(url_for("processing"))

from flask import send_file, make_response, flash, redirect, url_for

@app.route("/translated/<filename>")
@login_required
def translated_pdf(filename):
    safe_filename = secure_filename(filename)
    full_path = os.path.join(TRANSLATED_FOLDER, safe_filename)
    if not os.path.exists(full_path):
        flash("Translated file not found or still processing.")
        return redirect(url_for("dashboard"))

    print("📁 Serving file:", full_path)
    response = make_response(send_from_directory(TRANSLATED_FOLDER, safe_filename))
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Pragma"] = "no-cache"
    response.headers["Expires"] = "0"
    return response

@login_required
def force_processing():
    translation = Translation.query.filter_by(user_id=current_user.id).order_by(Translation.id.desc()).first()

    if not translation:
        flash("No translation found for current user.")
        return redirect(url_for("dashboard"))

    session["processing_file_id"] = translation.id
    flash("Session set. Redirecting to processing preview...")
    return redirect(url_for("processing"))

from flask import jsonify
@app.route('/assistant', methods=['POST'])
def assistant():
    data = request.get_json()
    message = data.get('message', '').lower().strip()

    name = current_user.name if current_user.is_authenticated else "there"

    if "how" in message and "work" in message:
        response = f"It’s super easy, {name}! Just upload your document, pick a language, and I’ll handle the translation 💫"
    elif "languages" in message:
        response = f"We support plenty of languages, {name} — from Hindi to Japanese to French and more 🌍"
    elif "file" in message and ("type" in message or "format" in message):
        response = "I accept PDF, DOCX, TXT, and HTML files. Bring ’em on 😎"
    elif "login" in message or "register" in message:
        response = "You can log in or register at the top — that unlocks translation features 🔐"
    elif "who" in message and "made" in message:
        response = "I was crafted by a brilliant dev — that’s you, Shridipa! And I exist to help your users ✨"
    else:
        response = f"Great question, {name}! I’ll do my best to help with: “{message}”"

    return jsonify({'reply': response})

@app.route("/view/<int:file_id>")
@login_required
def view_pdf(file_id):
    translation = db.session.get(Translation, file_id)
    if not translation or translation.user_id != current_user.id:
        flash("Unauthorized or not found.")
        return redirect(url_for("dashboard"))
    pdf_exists = os.path.exists(os.path.join(TRANSLATED_FOLDER, translation.translated_name))
    return render_template("view_pdf.html", translation=translation, pdf_exists=pdf_exists)

@app.route("/download/<int:file_id>")
@login_required
def download_pdf(file_id):
    translation = db.session.get(Translation, file_id)
    if not translation or translation.user_id != current_user.id:
        flash("Unauthorized or not found.")
        return redirect(url_for("dashboard"))
    return send_from_directory(TRANSLATED_FOLDER, translation.translated_name, as_attachment=True)

@app.route("/delete/<int:file_id>", methods=["POST"])
@login_required
def delete_pdf(file_id):
    translation = db.session.get(Translation, file_id)
    if not translation or translation.user_id != current_user.id:
        flash("You don't have permission to delete this file.")
        return redirect(url_for("dashboard"))

    # Delete translated file from disk
    translated_path = os.path.join(TRANSLATED_FOLDER, translation.translated_name)
    if os.path.exists(translated_path):
        os.remove(translated_path)

    # Remove database entry
    db.session.delete(translation)
    db.session.commit()
    flash("Translation deleted.")
    return redirect(url_for("dashboard"))


@app.route("/retranslate/<int:file_id>", methods=["GET", "POST"])
@login_required
def retranslate(file_id):
    translation = db.session.get(Translation, file_id)
    if not translation or translation.user_id != current_user.id:
        flash("Unauthorized or not found.")
        return redirect(url_for("dashboard"))

    SUPPORTED_FONT_LANGUAGES = {
        "en": "🇺🇸 English", "fr": "🇫🇷 French", "de": "🇩🇪 German",
        "es": "🇪🇸 Spanish", "it": "🇮🇹 Italian", "hi": "🇮🇳 Hindi",
        "mr": "🇮🇳 Marathi", "ne": "🇳🇵 Nepali", "zh-CN": "🇨🇳 Chinese (Simplified)"
    }

    technical_terms = globals().get("TECHNICAL_TERMS", [])
    FAQ_RESPONSES = {
    "upload": "You can upload PDF, DOCX, TXT, or HTML files from the homepage. Avoid password-protected or corrupted files.",
    "file type": "Supported formats include .pdf, .docx, .txt, and .html. Scanned files without selectable text aren't ideal unless OCR is supported.",
    "language": "We currently support English, Hindi, Marathi, Nepali, French, German, Italian, Chinese (Simplified), and Spanish.",
    "translate": "We extract text from your file, use Google Translate to convert it into your selected language, and generate a styled PDF with matching fonts.",
    "retranslate": "Retranslation allows you to fix errors, choose a new language, or regenerate a clearer version of your document. Use the 🔁 button on your dashboard.",
    "font": "Fonts like DejaVu Sans are automatically chosen based on the selected output language to ensure proper rendering.",
    "view": "Your translated files appear in the Dashboard. You can view, download, retranslate, or delete them at any time.",
    "account": "Login is required to upload and manage files to ensure your content stays private and secure.",
    "download": "Use the ⬇ Download button in your Dashboard to save translated documents to your device.",
    "missing file": "If your original file is missing, re-upload it from the homepage to enable retranslation.",
    "book": "Yes, you can translate entire books up to 32MB in size. Longer texts are split into chunks to preserve flow and formatting.",
    "file size": "Currently, uploads up to 32MB are supported. We recommend keeping file sizes below that to ensure fast and stable performance.",
    "help": "I'm here to assist with uploading, translating, font issues, errors, and how to use the Dashboard — just ask!"
}
    # Reupload handler (before checking if file exists)
    if "reupload_submit" in request.form and "reupload_file" in request.files:
        file = request.files["reupload_file"]
        filename = translation.original_name
        save_path = os.path.join(UPLOAD_FOLDER, filename)
        file.save(save_path)
        flash("Original file re-uploaded successfully. You can now retranslate.")
        return redirect(url_for("retranslate", file_id=file_id))

    if request.method == "POST":
        # Assistant response mode
        if "user_query" in request.form:
            user_query = request.form.get("user_query", "").lower()
            assistant_reply = None

            for keyword, response in FAQ_RESPONSES.items():
                if keyword in user_query:
                    assistant_reply = response
                    break

            if not assistant_reply:
                assistant_reply = (
                    "I'm here to assist with PDF Genie — uploading, translating, retranslation, fonts, and dashboard questions. "
                    "I can't answer questions beyond this app."
                )

            return render_template(
                "retranslate.html",
                translation=translation,
                languages=SUPPORTED_FONT_LANGUAGES,
                assistant_reply=assistant_reply
            )

        # Retranslation intent
        reason = request.form.get("retranslate_reason")
        language = request.form.get("output_lang")
        orig_file_path = os.path.join(UPLOAD_FOLDER, translation.original_name)
        ext = os.path.splitext(translation.original_name)[1].lower()

        if not os.path.exists(orig_file_path):
            flash("The original file for retranslation is missing. Please upload it again below.")
            return render_template(
                "retranslate.html",
                translation=translation,
                languages=SUPPORTED_FONT_LANGUAGES,
                assistant_reply=None,
                require_reupload=True
            )

        extracted_text = extract_text(orig_file_path, ext)
        prepped_text, placeholders = preserve_terms(extracted_text, technical_terms)

        try:
            if len(prepped_text) > 4000:
                chunks = [prepped_text[i:i+4000] for i in range(0, len(prepped_text), 4000)]
                translated_text = "\n".join(
                    GoogleTranslator(source="auto", target=language).translate(chunk)
                    for chunk in chunks
                )
            else:
                translated_text = GoogleTranslator(source="auto", target=language).translate(prepped_text)
        except Exception as e:
            flash(f"Retranslation failed: {str(e)}")
            return render_template(
                "retranslate.html",
                translation=translation,
                languages=SUPPORTED_FONT_LANGUAGES
            )

        translated_text = restore_terms(translated_text, placeholders)

        new_filename = f"retranslated_{uuid.uuid4().hex[:6]}_{language}.pdf"
        new_path = os.path.join(TRANSLATED_FOLDER, new_filename)
        generate_pdf(translated_text, new_path, language)

        new_translation = Translation(
            user_id=current_user.id,
            original_name=translation.original_name,
            translated_name=new_filename,
            language=language,
            timestamp=datetime.utcnow(),
            retranslate_reason=reason
        )
        db.session.add(new_translation)
        db.session.commit()

        flash("Retranslation successful!")
        return redirect(url_for("dashboard"))

    return render_template(
        "retranslate.html",
        translation=translation,
        languages=SUPPORTED_FONT_LANGUAGES
    )




if __name__ == '__main__':
    app.run(debug=True)

