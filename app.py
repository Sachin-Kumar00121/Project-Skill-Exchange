import code
import os
from dotenv import load_dotenv
load_dotenv()
from flask import make_response
from flask import Flask, render_template, request, redirect, session, url_for
from datetime import datetime
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
            return render_template("login.html", error="Invalid Password or User not found")

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

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":

        provider_id = session["user_id"]  

        skill_name = request.form["skill_name"].strip()
        category = request.form["category"]
        description = request.form["description"]
        price = request.form["price"]
        unit = request.form["unit"]
        experience = request.form["experience"]

        # Safe Photo Handling
        photo = request.files.get("photo")

        if photo and photo.filename != "":
            photo_filename = photo.filename
            photo.save("static/uploads/" + photo_filename)
        else:
            photo_filename = None

        # Duplicate check
        cursor.execute(
            "SELECT skill_id FROM skills WHERE provider_id=%s AND LOWER(skill_name)=%s",
            (provider_id, skill_name.lower())
        )

        if cursor.fetchone():
            return render_template("add_skill.html", error="You already added this skill.")

        # Insert
        cursor.execute("""
            INSERT INTO skills (provider_id, skill_name, category, description, price, unit, experience, photo)
            VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
        """, (provider_id, skill_name, category, description, price, unit, experience, photo_filename))

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
    user_id = session.get("user_id")
    role = session.get("role")
    hide_skill = session.pop("hide_skill", None)

    base_query = """
        SELECT s.*, u.name AS provider_name
        FROM skills s
        JOIN users u ON s.provider_id = u.user_id
    """

    conditions = []
    values = []

    if category:
        conditions.append("s.category=%s")
        values.append(category)

    if user_id and role == "user":
        conditions.append("""
            s.skill_id NOT IN (
                SELECT skill_id FROM bookings
                WHERE user_id=%s
                AND status IN ('pending','accepted')
            )
        """)
        values.append(user_id)

    if hide_skill:
        conditions.append("s.skill_id != %s")
        values.append(hide_skill)

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    cursor.execute(base_query, tuple(values))
    skills = cursor.fetchall()

    response = make_response(render_template("all_skills.html", skills=skills))
    response.headers["Cache-Control"] = "no-store"
    return response


# Booking Route
@app.route("/book", methods=["POST"])
def book():

    if "user_id" not in session or session.get("role") != "user":
        return redirect("/login")

    user_id = session["user_id"]

    skill_id = request.form["skill_id"]
    offered_price = request.form["offered_price"]
    unit = request.form["unit"]
    service_date = request.form["service_date"]

    hour = request.form.get("hour")
    minute = request.form.get("minute")
    ampm = request.form.get("ampm")

    # ✅ Convert to 24hr format for DB
    time_string = f"{hour}:{minute} {ampm}"
    time_obj = datetime.strptime(time_string, "%I:%M %p")
    service_time = time_obj.strftime("%H:%M:%S")  

    # ✅ Duplicate Check
    cursor.execute("""
        SELECT * FROM bookings
        WHERE skill_id=%s 
        AND user_id=%s
        AND service_date=%s
        AND status IN ('pending','accepted')
    """, (skill_id, user_id, service_date))

    existing = cursor.fetchone()
    
    if existing:
        return redirect("/all-skills")

    # Get provider id
    cursor.execute("SELECT provider_id FROM skills WHERE skill_id=%s", (skill_id,))
    skill = cursor.fetchone()

    if not skill:
        return redirect("/all-skills")

    provider_id = skill["provider_id"]

    # Insert new booking
    cursor.execute("""
        INSERT INTO bookings
        (skill_id, user_id, provider_id, offered_price, unit, service_date, service_time)
        VALUES (%s,%s,%s,%s,%s,%s,%s)
    """, (skill_id, user_id, provider_id, offered_price, unit, service_date, service_time))

    db.commit()

    session["hide_skill"] = skill_id

    return redirect(url_for("all_skills"))


# Cancel Booking Route
@app.route("/cancel-booking/<int:booking_id>", methods=["POST"])
def cancel_booking(booking_id):

    if "user_id" not in session:
        return redirect("/login")

    cursor.execute("""
        UPDATE bookings 
        SET status='cancelled'
        WHERE booking_id=%s 
        AND user_id=%s 
        AND status IN ('pending','accepted')
    """, (booking_id, session["user_id"]))

    db.commit()

    return redirect("/my-bookings")


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
    for b in bookings:
     if b["service_time"]:
            time_obj = datetime.strptime(str(b["service_time"]), "%H:%M:%S")
            b["display_time"] = time_obj.strftime("%I:%M %p")

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
    
    for b in bookings:
     if b["service_time"]:
        time_obj = datetime.strptime(str(b["service_time"]), "%H:%M:%S")
        b["display_time"] = time_obj.strftime("%I:%M %p")

    return render_template("provider_bookings.html", bookings=bookings)


# Update Booking Status (Accept/Reject) for Providers route
@app.route("/update-booking/<int:booking_id>/<status>", methods=["POST"])
def update_booking(booking_id, status):

    if "user_id" not in session:
        return redirect("/login")

    if status not in ["accepted", "rejected"]:
        return redirect("/provider-bookings")

    cursor.execute("""
        UPDATE bookings
        SET status=%s
        WHERE booking_id=%s AND provider_id=%s
    """, (status, booking_id, session["user_id"]))

    db.commit()

    return redirect("/provider-bookings")


if __name__ == "__main__":
    app.run(debug=True)


