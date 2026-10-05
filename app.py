import csv
import io
import os
import sqlite3
from datetime import datetime
from functools import wraps

from flask import Flask, flash, g, redirect, render_template, request, send_file, session, url_for
from werkzeug.security import check_password_hash, generate_password_hash
from werkzeug.utils import secure_filename
from textblob import TextBlob

BASE_DIR = os.path.abspath(os.path.dirname(__file__))
DATABASE = os.path.join(BASE_DIR, "instance", "feedback.db")

app = Flask(__name__)
app.config.update(
    SECRET_KEY=os.environ.get("SECRET_KEY", "change-this-secret-key-in-production"),
    DATABASE=DATABASE,
    MAX_CONTENT_LENGTH=2 * 1024 * 1024,
)


def get_db():
    if "db" not in g:
        os.makedirs(os.path.dirname(app.config["DATABASE"]), exist_ok=True)
        g.db = sqlite3.connect(app.config["DATABASE"])
        g.db.row_factory = sqlite3.Row
    return g.db


@app.teardown_appcontext
def close_db(_error=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_db():
    db = get_db()
    db.executescript("""
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL UNIQUE,
            email TEXT NOT NULL UNIQUE,
            password_hash TEXT NOT NULL,
            created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS feedback (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            text TEXT NOT NULL,
            sentiment TEXT NOT NULL,
            polarity REAL NOT NULL,
            subjectivity REAL NOT NULL,
            created_at TEXT NOT NULL,
            FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
        );
        CREATE INDEX IF NOT EXISTS idx_feedback_user ON feedback(user_id);
        CREATE INDEX IF NOT EXISTS idx_feedback_sentiment ON feedback(sentiment);
    """)
    db.commit()


def analyze_sentiment(text):
    result = TextBlob(text).sentiment
    polarity = round(result.polarity, 4)
    subjectivity = round(result.subjectivity, 4)
    if polarity > 0.05:
        sentiment = "Positive"
    elif polarity < -0.05:
        sentiment = "Negative"
    else:
        sentiment = "Neutral"
    return sentiment, polarity, subjectivity


def login_required(view):
    @wraps(view)
    def wrapped(*args, **kwargs):
        if "user_id" not in session:
            flash("Please log in to continue.", "warning")
            return redirect(url_for("login", next=request.path))
        return view(*args, **kwargs)
    return wrapped


@app.context_processor
def inject_user():
    return {"current_username": session.get("username")}


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form.get("username", "").strip()
        email = request.form.get("email", "").strip().lower()
        password = request.form.get("password", "")
        confirm = request.form.get("confirm_password", "")
        if len(username) < 3:
            flash("Username must contain at least 3 characters.", "danger")
        elif "@" not in email:
            flash("Enter a valid email address.", "danger")
        elif len(password) < 6:
            flash("Password must contain at least 6 characters.", "danger")
        elif password != confirm:
            flash("Passwords do not match.", "danger")
        else:
            db = get_db()
            try:
                db.execute(
                    "INSERT INTO users (username,email,password_hash,created_at) VALUES (?,?,?,?)",
                    (username, email, generate_password_hash(password), datetime.utcnow().isoformat(timespec="seconds")),
                )
                db.commit()
                flash("Account created successfully. Please log in.", "success")
                return redirect(url_for("login"))
            except sqlite3.IntegrityError:
                flash("Username or email already exists.", "danger")
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form.get("identifier", "").strip().lower()
        password = request.form.get("password", "")
        user = get_db().execute(
            "SELECT * FROM users WHERE lower(username)=? OR lower(email)=?", (identifier, identifier)
        ).fetchone()
        if user and check_password_hash(user["password_hash"], password):
            session.clear()
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Welcome back!", "success")
            return redirect(request.args.get("next") or url_for("dashboard"))
        flash("Invalid username/email or password.", "danger")
    return render_template("login.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("You have been logged out.", "info")
    return redirect(url_for("index"))


def save_feedback(text, user_id):
    text = text.strip()
    if not text:
        raise ValueError("Feedback cannot be empty.")
    if len(text) > 5000:
        raise ValueError("Feedback must be 5,000 characters or fewer.")
    sentiment, polarity, subjectivity = analyze_sentiment(text)
    get_db().execute(
        "INSERT INTO feedback (user_id,text,sentiment,polarity,subjectivity,created_at) VALUES (?,?,?,?,?,?)",
        (user_id, text, sentiment, polarity, subjectivity, datetime.utcnow().isoformat(timespec="seconds")),
    )


@app.route("/feedback", methods=["GET", "POST"])
@login_required
def feedback():
    if request.method == "POST":
        try:
            save_feedback(request.form.get("text", ""), session["user_id"])
            get_db().commit()
            flash("Feedback analyzed and saved successfully.", "success")
            return redirect(url_for("dashboard"))
        except ValueError as exc:
            flash(str(exc), "danger")
    return render_template("feedback.html")


@app.route("/upload-csv", methods=["POST"])
@login_required
def upload_csv():
    uploaded = request.files.get("file")
    if not uploaded or not uploaded.filename:
        flash("Please choose a CSV file.", "danger")
        return redirect(url_for("feedback"))
    if not secure_filename(uploaded.filename).lower().endswith(".csv"):
        flash("Only CSV files are supported.", "danger")
        return redirect(url_for("feedback"))
    try:
        raw = uploaded.read().decode("utf-8-sig")
        reader = csv.reader(io.StringIO(raw))
        rows = list(reader)
        if not rows:
            raise ValueError("The CSV file is empty.")
        header = [x.strip().lower() for x in rows[0]]
        if "feedback" in header:
            index = header.index("feedback")
            data_rows = rows[1:]
        elif "text" in header:
            index = header.index("text")
            data_rows = rows[1:]
        else:
            index = 0
            data_rows = rows
        count = 0
        db = get_db()
        for row in data_rows:
            if index < len(row) and row[index].strip():
                text_value = row[index].strip()[:5000]
                sentiment, polarity, subjectivity = analyze_sentiment(text_value)
                db.execute(
                    "INSERT INTO feedback (user_id,text,sentiment,polarity,subjectivity,created_at) VALUES (?,?,?,?,?,?)",
                    (session["user_id"], text_value, sentiment, polarity, subjectivity, datetime.utcnow().isoformat(timespec="seconds")),
                )
                count += 1
        db.commit()
        flash(f"Imported and analyzed {count} feedback item(s).", "success")
    except UnicodeDecodeError:
        flash("CSV must be UTF-8 encoded.", "danger")
    except Exception as exc:
        flash(f"Could not process CSV: {exc}", "danger")
    return redirect(url_for("dashboard"))


@app.route("/dashboard")
@login_required
def dashboard():
    search = request.args.get("search", "").strip()
    sentiment = request.args.get("sentiment", "All")
    sort = request.args.get("sort", "newest")
    db = get_db()
    conditions = ["user_id = ?"]
    params = [session["user_id"]]
    if search:
        conditions.append("text LIKE ?")
        params.append(f"%{search}%")
    if sentiment in {"Positive", "Negative", "Neutral"}:
        conditions.append("sentiment = ?")
        params.append(sentiment)
    order = "created_at DESC" if sort == "newest" else "created_at ASC"
    feedback_rows = db.execute(
        f"SELECT * FROM feedback WHERE {' AND '.join(conditions)} ORDER BY {order}", params
    ).fetchall()
    counts = db.execute(
        "SELECT sentiment, COUNT(*) count FROM feedback WHERE user_id=? GROUP BY sentiment", (session["user_id"],)
    ).fetchall()
    count_map = {row["sentiment"]: row["count"] for row in counts}
    total = sum(count_map.values())
    avg = db.execute("SELECT AVG(polarity) value FROM feedback WHERE user_id=?", (session["user_id"],)).fetchone()["value"]
    recent = db.execute(
        "SELECT * FROM feedback WHERE user_id=? ORDER BY created_at DESC LIMIT 5", (session["user_id"],)
    ).fetchall()
    return render_template(
        "dashboard.html",
        feedback_rows=feedback_rows,
        recent=recent,
        total=total,
        positive=count_map.get("Positive", 0),
        negative=count_map.get("Negative", 0),
        neutral=count_map.get("Neutral", 0),
        average_polarity=round(avg or 0, 2),
        search=search,
        selected_sentiment=sentiment,
        selected_sort=sort,
    )


@app.route("/delete-feedback/<int:feedback_id>", methods=["POST"])
@login_required
def delete_feedback(feedback_id):
    db = get_db()
    db.execute("DELETE FROM feedback WHERE id=? AND user_id=?", (feedback_id, session["user_id"]))
    db.commit()
    flash("Feedback deleted.", "success")
    return redirect(url_for("dashboard"))


@app.route("/export-csv")
@login_required
def export_csv():
    rows = get_db().execute(
        "SELECT id,text,sentiment,polarity,subjectivity,created_at FROM feedback WHERE user_id=? ORDER BY created_at DESC",
        (session["user_id"],),
    ).fetchall()
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["ID", "Feedback", "Sentiment", "Polarity", "Subjectivity", "Created At"])
    for row in rows:
        writer.writerow([row["id"], row["text"], row["sentiment"], row["polarity"], row["subjectivity"], row["created_at"]])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode("utf-8-sig")), mimetype="text/csv", as_attachment=True, download_name="feedback_analysis.csv")


@app.cli.command("init-db")
def init_db_command():
    init_db()
    print("Database initialized.")


with app.app_context():
    init_db()


if __name__ == "__main__":
    app.run(debug=os.environ.get("FLASK_DEBUG", "0") == "1")
