import os
from dotenv import load_dotenv
load_dotenv()
from flask import Flask, render_template, request, redirect, session

import re

import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.secret_key = "skill_exchange_secret"

# ✅ MySQL Connection
db = mysql.connector.connect(
    host=os.getenv("DB_HOST", ""),
    user=os.getenv("DB_USER", ""),
    password=os.getenv("DB_PASS", ""),   
    database=os.getenv("DB_NAME", ""),
    port=int(os.getenv("DB_PORT", ""))

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
    

    # Strong password validation
    pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$'
    if not re.match(pattern, password):
        return render_template("register.html", role=role, error="Password must be at least 8 characters long and include uppercase, lowercase, number and special character.")



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

        # email 
        if "@" in identifier:
            cursor.execute("SELECT * FROM users WHERE email=%s", (identifier,))
        else:
            cursor.execute("SELECT * FROM users WHERE phone=%s", (identifier,))

        user = cursor.fetchone()

        
        if user and check_password_hash(user["password"], password):
            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]   

            return redirect("/dashboard")

        else:
            return render_template("login.html", error="Invalid login credentials")

    return render_template("login.html")



# ✅ Dashboard 
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

# Add Skill Route
@app.route("/add-skill", methods=["GET", "POST"])
def add_skill():
    if 'user_id' not in session:
        return redirect("/login")

    if request.method == "POST":
        provider_id = session['user_id']
        skill_name = request.form['skill_name'].strip()
        category = request.form['category']
        description = request.form['description']

        # Duplicate check
        cursor.execute(
            "SELECT skill_id FROM skills WHERE provider_id=%s AND LOWER(skill_name)=%s",
            (provider_id, skill_name.lower())
        )

        if cursor.fetchone():
            return render_template("add_skill.html", error="You already added this skill.")

        cursor.execute(
            "INSERT INTO skills (provider_id, skill_name, category, description) VALUES (%s,%s,%s,%s)",
            (provider_id, skill_name, category, description)
        )
        db.commit()

        return render_template("add_skill.html", success="Skill Added Successfully")

    return render_template("add_skill.html")


# View My Skills Route
@app.route("/my-skills")
def my_skills():
    if "user_id" not in session:
        return redirect("/login")

    if session.get("role") != "provider":
        return "Access Denied"

    cursor.execute(
        "SELECT * FROM skills WHERE provider_id=%s ORDER BY skill_id DESC",
        (session["user_id"],)
    )

    skills = cursor.fetchall()
    return render_template("my_skills.html", skills=skills)

# Delete Skill Route
@app.route("/delete-skill/<int:skill_id>")
def delete_skill(skill_id):
    if "user_id" not in session:
        return redirect("/login")

    cursor.execute(
        "DELETE FROM skills WHERE skill_id=%s AND provider_id=%s",
        (skill_id, session["user_id"])
    )
    db.commit()

    return redirect("/my-skills")

# Edit Skill Route
@app.route("/edit-skill/<int:skill_id>", methods=["GET", "POST"])
def edit_skill(skill_id):
    if "user_id" not in session:
        return redirect("/login")

    if request.method == "GET":
        cursor.execute(
            "SELECT * FROM skills WHERE skill_id=%s AND provider_id=%s",
            (skill_id, session["user_id"])
        )
        skill = cursor.fetchone()
        return render_template("edit_skill.html", skill=skill)

    skill_name = request.form["skill_name"]
    category = request.form["category"]
    description = request.form["description"]

    cursor.execute(
        "UPDATE skills SET skill_name=%s, category=%s, description=%s WHERE skill_id=%s AND provider_id=%s",
        (skill_name, category, description, skill_id, session["user_id"])
    )
    db.commit()

    return redirect("/my-skills")

# View All Skills (with optional category filter)
@app.route("/all-skills")
def all_skills():
    category = request.args.get("category")

    if category:
        cursor.execute("""
            SELECT s.*, u.name as provider_name
            FROM skills s
            JOIN users u ON s.provider_id = u.user_id
            WHERE s.category=%s
        """, (category,))
    else:
        cursor.execute("""
            SELECT s.*, u.name as provider_name
            FROM skills s
            JOIN users u ON s.provider_id = u.user_id
        """)

    skills = cursor.fetchall()

    booked_skills = []

    if "user_id" in session and session["role"] == "user":
        cursor.execute("""
            SELECT skill_id FROM bookings 
            WHERE user_id=%s AND status IN ('pending','accepted')
        """, (session["user_id"],))
        booked = cursor.fetchall()
        booked_skills = [b["skill_id"] for b in booked]

    return render_template("all_skills.html",
                           skills=skills,
                           booked_skills=booked_skills)



# Booking Route
@app.route("/book/<int:skill_id>", methods=["POST"])
def book(skill_id):

    if "user_id" not in session or session.get("role") != "user":
        return redirect("/login")

    user_id = session["user_id"]

    # Check duplicate booking
    cursor.execute("""
        SELECT * FROM bookings
        WHERE skill_id=%s AND user_id=%s 
        AND status IN ('pending','accepted')
    """, (skill_id, user_id))

    existing = cursor.fetchone()

    if existing:
        return redirect("/all-skills")

    # Get provider id
    cursor.execute("SELECT provider_id FROM skills WHERE skill_id=%s", (skill_id,))
    skill = cursor.fetchone()

    if not skill:
        return redirect("/all-skills")

    provider_id = skill["provider_id"]

    cursor.execute("""
        INSERT INTO bookings (skill_id, user_id, provider_id)
        VALUES (%s,%s,%s)
    """, (skill_id, user_id, provider_id))

    db.commit()

    return redirect("/all-skills")



# View My Bookings  for user route
@app.route("/my-bookings")
def my_bookings():
    if 'user_id' not in session:
        return redirect("/login")

    user_id = session['user_id']

    cursor.execute("""
        SELECT b.*, s.skill_name, u.name as provider_name
        FROM bookings b
        JOIN skills s ON b.skill_id = s.skill_id
        JOIN users u ON b.provider_id = u.user_id
        WHERE b.user_id=%s
    """, (user_id,))

    bookings = cursor.fetchall()

    return render_template("my_bookings.html", bookings=bookings)


# View Bookings for Providers route
@app.route("/provider-bookings")
def provider_bookings():
    if 'user_id' not in session:
        return redirect("/login")

    provider_id = session['user_id']

    cursor.execute("""
        SELECT b.*, s.skill_name, u.name as user_name
        FROM bookings b
        JOIN skills s ON b.skill_id = s.skill_id
        JOIN users u ON b.user_id = u.user_id
        WHERE b.provider_id=%s
    """, (provider_id,))

    bookings = cursor.fetchall()

    return render_template("provider_bookings.html", bookings=bookings)

# Update Booking Status (Accept/Reject) for Providers route
@app.route("/update-booking/<int:booking_id>/<status>")
def update_booking(booking_id, status):
    cursor.execute(
        "UPDATE bookings SET status=%s WHERE booking_id=%s",
        (status, booking_id)
    )
    db.commit()
    return redirect("/provider-bookings")



if __name__ == "__main__":
    app.run(debug=True)


