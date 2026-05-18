from flask import Flask, render_template, request, redirect, url_for, flash, session
import joblib
import numpy as np
import sqlite3
import re
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "super_secret_key_123"  # change this in production


model = joblib.load("linear_model.pkl")

def predict_price(Open, High, Low, Volume):
    test_data = np.array([[Open, High, Low, Volume]])
    prediction = model.predict(test_data)
    return prediction



DB_PATH = "users.db"

def init_db():
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            phone TEXT NOT NULL,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT NOT NULL
        )
    ''')
    conn.commit()
    conn.close()

init_db()


def add_user(username, phone, email, password):
    pw_hash = generate_password_hash(password)
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    try:
        c.execute("""
            INSERT INTO users (username, phone, email, password_hash)
            VALUES (?, ?, ?, ?)
        """, (username, phone, email, pw_hash))
        conn.commit()
        return True, None
    except sqlite3.IntegrityError:
        return False, "Username or Email already exists"
    finally:
        conn.close()


def get_user_by_email(email):
    conn = sqlite3.connect(DB_PATH)
    c = conn.cursor()
    c.execute("SELECT id, username, phone, email, password_hash FROM users WHERE email = ?", (email,))
    user = c.fetchone()
    conn.close()
    return user




@app.route("/")
def index():
    return render_template("index.html")


@app.route("/signup", methods=["GET", "POST"])
def signup():
    if request.method == "POST":
        username = request.form.get("username").strip()
        phone = request.form.get("phone").strip()
        email = request.form.get("email").strip().lower()
        password = request.form.get("password")

        # Validation
        if not username or not phone or not email or not password:
            flash("All fields are required", "error")
            return redirect(url_for("signup"))

        if not re.fullmatch(r"\d{10}", phone):
            flash("Phone must be 10 digits", "error")
            return redirect(url_for("signup"))

        if not email.endswith("@gmail.com"):
            flash("Email must end with @gmail.com", "error")
            return redirect(url_for("signup"))

        success, msg = add_user(username, phone, email, password)

        if not success:
            flash(msg, "error")
            return redirect(url_for("signup"))

        flash("Signup successful! Please login.", "success")
        return redirect(url_for("signin"))

    return render_template("signup.html")


@app.route("/signin", methods=["GET", "POST"])
def signin():
    if request.method == "POST":
        email = request.form.get("email").strip().lower()
        password = request.form.get("password")

        user = get_user_by_email(email)

        if not user:
            flash("User not found", "error")
            return redirect(url_for("signup"))

        user_id, username, phone, email_db, pw_hash = user

        if not check_password_hash(pw_hash, password):
            flash("Incorrect password", "error")
            return redirect(url_for("signin"))

        session["user_id"] = user_id
        session["username"] = username

        flash("Login successful", "success")
        return redirect(url_for("home"))

    return render_template("signin.html")


@app.route("/logout")
def logout():
    session.clear()
    flash("Logged out successfully", "success")
    return redirect(url_for("index"))


@app.route("/home")
def home():
    if "user_id" not in session:
        return redirect(url_for("signin"))
    return render_template("home.html", username=session["username"])


@app.route("/details")
def details():
    if "user_id" not in session:
        return redirect(url_for("signin"))
    return render_template("details.html")



@app.route("/predict", methods=["GET", "POST"])
def predict_route():
    if "user_id" not in session:
        return redirect(url_for("signin"))

    if request.method == "POST":
        try:
            open_val = float(request.form["Open"])
            high = float(request.form["High"])
            low = float(request.form["Low"])
            volume = float(request.form["Volume"])

            prediction = predict_price(open_val, high, low, volume)
            value = round(prediction[0], 2)

            return render_template(
                "predict.html",
                prediction_text=f"Predicted Stock Price: ${value}"
            )

        except Exception as e:
            return render_template(
                "predict.html",
                prediction_text=f"Error: {str(e)}"
            )

    return render_template("predict.html", prediction_text=None)



if __name__ == "__main__":
    app.run(debug=True)
