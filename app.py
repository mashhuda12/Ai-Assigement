from flask import Flask, render_template, request, jsonify
import os
import PyPDF2
import pytesseract
from pdf2image import convert_from_path
import language_tool_python

# =========================
# CONFIG
# =========================
app = Flask(__name__)
app.config["UPLOAD_FOLDER"] = "uploads"

# 🔥 Tesseract path (already installed by you)
pytesseract.pytesseract.tesseract_cmd = r"C:\Program Files\Tesseract-OCR\tesseract.exe"

# 🔥 Poppler path
POPPLER_PATH = r"C:\poppler\Library\bin"

# =========================
# GRAMMAR TOOL (SAFE)
# =========================
try:
    tool = language_tool_python.LanguageToolPublicAPI('en-US')
except:
    tool = None


# =========================
# HOME
# =========================
@app.route("/")
def index():
    return render_template("index.html")


# =========================
# TEXT EXTRACTION FUNCTION
# =========================
def extract_text_from_pdf(filepath):
    text = ""

    # Try normal extraction first
    try:
        with open(filepath, "rb") as f:
            reader = PyPDF2.PdfReader(f)
            for page in reader.pages:
                text += page.extract_text() or ""
    except:
        pass

    # 🔥 If no text → use OCR
    if len(text.strip()) < 20:
        print("Using OCR fallback...")

        try:
            images = convert_from_path(filepath, poppler_path=POPPLER_PATH)

            for img in images:
                text += pytesseract.image_to_string(img)

        except Exception as e:
            print("OCR Error:", e)
            return None

    return text


# =========================
# CHECK ASSIGNMENT
# =========================
@app.route("/check", methods=["POST"])
def check_assignment():

    if "file" not in request.files:
        return jsonify({"error": "No file uploaded"})

    file = request.files["file"]

    if file.filename == "":
        return jsonify({"error": "No selected file"})

    filepath = os.path.join(app.config["UPLOAD_FOLDER"], file.filename)
    file.save(filepath)

    # =========================
    # TEXT EXTRACTION
    # =========================
    text = ""

    if file.filename.endswith(".pdf"):
        text = extract_text_from_pdf(filepath)

        if text is None:
            return jsonify({"error": "OCR failed. Check Poppler installation."})

    elif file.filename.endswith(".txt"):
        with open(filepath, "r", encoding="utf-8") as f:
            text = f.read()

    else:
        return jsonify({"error": "Only PDF or TXT allowed"})

    # =========================
    # BASIC METRICS
    # =========================
    words = text.split()
    word_count = len(words)
    sentence_count = max(1, text.count(".") + text.count("!") + text.count("?"))

    # =========================
    # GRAMMAR CHECK (SAFE)
    # =========================
    grammar_errors = 0
    matches = []

    if tool:
        try:
            safe_text = text[:1500]  # limit for API
            matches = tool.check(safe_text)
            grammar_errors = len(matches)
        except:
            grammar_errors = 0
            matches = []

    # =========================
    # TOP MISTAKES
    # =========================
    mistakes = []
    for m in matches[:5]:
        mistakes.append({
            "message": m.message,
            "suggestion": m.replacements[:2]
        })

    # =========================
    # READABILITY
    # =========================
    avg_words = word_count / sentence_count

    if avg_words < 10:
        readability = "Easy"
    elif avg_words < 18:
        readability = "Medium"
    else:
        readability = "Hard"

    # =========================
    # SCORING
    # =========================
    score = 100

    score -= grammar_errors * 2

    if word_count < 150:
        score -= 20

    if avg_words > 20:
        score -= 10

    score = max(score, 0)

    # =========================
    # GRADE
    # =========================
    if score >= 85:
        grade = "A"
    elif score >= 70:
        grade = "B"
    elif score >= 50:
        grade = "C"
    else:
        grade = "D"

    # =========================
    # FEEDBACK
    # =========================
    feedback = []

    if grammar_errors > 10:
        feedback.append("Too many grammar mistakes. Improve sentence structure.")

    if word_count < 150:
        feedback.append("Assignment is too short. Add more explanation.")

    if readability == "Hard":
        feedback.append("Sentences are too long. Improve readability.")

    if score > 80:
        feedback.append("Well written assignment 👍")

    if not feedback:
        feedback.append("Good effort. Minor improvements needed.")

    # =========================
    # RESPONSE
    # =========================
    return jsonify({
        "word_count": word_count,
        "sentences": sentence_count,
        "grammar_errors": grammar_errors,
        "readability": readability,
        "score": score,
        "grade": grade,
        "mistakes": mistakes,
        "feedback": feedback
    })


# =========================
# RUN
# =========================
if __name__ == "__main__":
    os.makedirs("uploads", exist_ok=True)
    app.run(debug=True)