
from flask import Flask, render_template, request, redirect, session
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "skill_exchange_secret"

# ✅ MySQL Connection (apna password yahan set karo)
db = mysql.connector.connect(
    host="localhost",
    user="root",
    password="Sachin@#8057",   # <-- yahan apna MySQL password
    database="skill_exchange"
)
cursor = db.cursor(dictionary=True)


# ✅ Home Page
@app.route("/")
def home():
    return render_template("index.html")


# ✅ Register (Email OR Phone + Confirm Password)
@app.route("/register/user", methods=["GET", "POST"])
def register_user():
    return register_common("user")


@app.route("/register/provider", methods=["GET", "POST"])
def register_provider():
    return register_common("provider")

def register_common(role):
    if request.method == "GET":
        return render_template("register.html", role=role)

    name = request.form["name"].strip()
    identifier = request.form["identifier"].strip().lower()
    password = request.form["password"]
    confirm_password = request.form["confirm_password"]

    # Confirm password check
    if password != confirm_password:
        return "Password and Confirm Password do not match"

    # Detect email/phone
    is_email = "@" in identifier
    is_phone = identifier.isdigit() and len(identifier) == 10  # 10 digit

    if not (is_email or is_phone):
        return "Please enter a valid Email or 10-digit Phone number"

    # Duplicate check
    if is_email:
        cursor.execute("SELECT user_id FROM users WHERE email=%s", (identifier,))
    else:
        cursor.execute("SELECT user_id FROM users WHERE phone=%s", (identifier,))
    if cursor.fetchone():
        return "Already registered. Please login."

    hashed_password = generate_password_hash(password)

    # Insert with role
    if is_email:
        cursor.execute(
            "INSERT INTO users (name, email, phone, password, id_type, role) VALUES (%s,%s,%s,%s,%s,%s)",
            (name, identifier, None, hashed_password, "email", role)
        )
    else:
        cursor.execute(
            "INSERT INTO users (name, email, phone, password, id_type, role) VALUES (%s,%s,%s,%s,%s,%s)",
            (name, None, identifier, hashed_password, "phone", role)
        )

    db.commit()
    return redirect("/login")


# ✅ Login (Email OR Phone)
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        identifier = request.form["identifier"]
        password = request.form["password"]

        # email ya phone se user nikaalo
        if "@" in identifier:
            cursor.execute("SELECT * FROM users WHERE email=%s", (identifier,))
        else:
            cursor.execute("SELECT * FROM users WHERE phone=%s", (identifier,))

        user = cursor.fetchone()

        # ✅ YAHI WO JAGAH HAI
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]   # 👈 यही line tum pooch rahe the

            return redirect("/dashboard")

        else:
            return "Invalid login credentials"

    return render_template("login.html")



# ✅ Dashboard (protected)
@app.route("/dashboard")
def dashboard():
    if "user_id" not in session:
        return redirect("/login")
    return render_template("dashboard.html")


# ✅ Logout
@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
