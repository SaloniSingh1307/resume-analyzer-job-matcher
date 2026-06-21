from flask import Flask, render_template, request, redirect, session
import sqlite3
import PyPDF2
from datetime import datetime

app = Flask(__name__)
app.secret_key = "secret123"

# ---------------- DATABASE ----------------
def init_db():
    conn = sqlite3.connect("database.db")
    c = conn.cursor()

    c.execute('''CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT,
        password TEXT
    )''')

    c.execute('''CREATE TABLE IF NOT EXISTS history (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        user_id INTEGER,
        score REAL,
        matched TEXT,
        missing TEXT,
        date TEXT
    )''')

    conn.commit()
    conn.close()

init_db()

# ---------------- SKILLS ----------------
SKILLS = [
    "python", "java", "c++", "javascript", "html", "css",
    "react", "node", "flask", "django", "sql", "mongodb",
    "machine learning", "data analysis"
]

REQUIRED_WEIGHT = 0.7
OPTIONAL_WEIGHT = 0.3

# ---------------- PDF ----------------
def extract_text(file):
    pdf = PyPDF2.PdfReader(file)
    text = ""
    for page in pdf.pages:
        if page.extract_text():
            text += page.extract_text()
    return text.lower()

# ---------------- MATCHING ----------------
def extract_skills(text):
    found = set()
    for skill in SKILLS:
        if skill in text:
            found.add(skill)
    return found

def match_skills(resume, job):
    resume_skills = extract_skills(resume)
    job_skills = list(extract_skills(job))

    split = int(len(job_skills) * 0.6)
    required = set(job_skills[:split])
    optional = set(job_skills[split:])

    matched_required = resume_skills & required
    matched_optional = resume_skills & optional

    score = (
        (len(matched_required) / len(required) * REQUIRED_WEIGHT if required else 0) +
        (len(matched_optional) / len(optional) * OPTIONAL_WEIGHT if optional else 0)
    ) * 100

    matched = list(matched_required | matched_optional)
    missing = list(set(job_skills) - resume_skills)

    return round(score, 2), matched, missing

# ---------------- ROUTES ----------------
@app.route('/')
def home():
    return redirect('/login')

@app.route('/register', methods=['GET','POST'])
def register():
    if request.method == 'POST':
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO users (username, password) VALUES (?, ?)",
                  (request.form['username'], request.form['password']))
        conn.commit()
        conn.close()
        return redirect('/login')
    return render_template('register.html')

@app.route('/login', methods=['GET','POST'])
def login():
    if request.method == 'POST':
        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        user = c.execute("SELECT * FROM users WHERE username=? AND password=?",
                         (request.form['username'], request.form['password'])).fetchone()

        if user:
            session['user_id'] = user[0]
            return redirect('/dashboard')

    return render_template('login.html')

@app.route('/dashboard', methods=['GET','POST'])
def dashboard():
    if 'user_id' not in session:
        return redirect('/login')

    if request.method == 'POST':
        file = request.files['resume']
        job_desc = request.form['job']

        resume_text = extract_text(file)
        score, matched, missing = match_skills(resume_text, job_desc.lower())

        conn = sqlite3.connect("database.db")
        c = conn.cursor()
        c.execute("INSERT INTO history (user_id, score, matched, missing, date) VALUES (?, ?, ?, ?, ?)",
                  (session['user_id'], score, ", ".join(matched), ", ".join(missing), str(datetime.now())))
        conn.commit()
        conn.close()

        return render_template('dashboard.html', score=score, matched=matched, missing=missing)

    return render_template('dashboard.html')

@app.route('/history')
def history():
    if 'user_id' not in session:
        return redirect('/login')

    conn = sqlite3.connect("database.db")
    c = conn.cursor()
    data = c.execute("SELECT score, matched, missing, date FROM history WHERE user_id=?",
                     (session['user_id'],)).fetchall()
    conn.close()

    return render_template('history.html', data=data)

@app.route('/logout')
def logout():
    session.clear()
    return redirect('/login')

if __name__ == '__main__':
    app.run(debug=True)