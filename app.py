import code
import os
from dotenv import load_dotenv
load_dotenv()
from flask import jsonify, make_response
from flask import Flask, render_template, request, redirect, session, url_for
from datetime import datetime, time, date
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

def admin_required():
    if session.get("role") != "admin":
        return False
    return True


# Admin login route
@app.route("/admin-login", methods=["GET","POST"])
def admin_login():

    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        cursor.execute("SELECT * FROM users WHERE email=%s AND role='admin'", (email,))
        admin = cursor.fetchone()

        if admin and check_password_hash(admin["password"], password):
            session.clear()
            session["user_id"] = admin["user_id"]
            session["role"] = "admin"
            return redirect("/admin-dashboard")
        else:
            return render_template("admin/admin_login.html", error="Invalid Login Credentials....")

    return render_template("admin/admin_login.html")

# Admin logout route
@app.route("/admin/logout")
def admin_logout():
    session.pop("admin", None)
    return redirect(url_for("admin_login"))

#Admin Passwoerd Change Route
@app.route("/admin-change-password", methods=["GET","POST"])
def admin_change_password():

    if session.get("role") != "admin":
        return redirect("/login")

    if request.method == "POST":
        old_password = request.form["old_password"]
        new_password = request.form["new_password"]

        cursor.execute("SELECT * FROM users WHERE user_id=%s", (session["user_id"],))
        admin = cursor.fetchone()

        if not check_password_hash(admin["password"], old_password):
            return render_template("admin/admin_change_password.html", error="Old password incorrect")

        new_hash = generate_password_hash(new_password)

        cursor.execute("UPDATE users SET password=%s WHERE user_id=%s",
                       (new_hash, session["user_id"]))
        db.commit()

        return render_template("admin/admin_change_password.html",
                               message="Password Updated Successfully")

    return render_template("admin/admin_change_password.html")


#Admin dashboard route
@app.route("/admin-dashboard")
def admin_dashboard():

    if not admin_required():
        return redirect("/login")

    cursor.execute("SELECT COUNT(*) as total FROM users WHERE role='user'")
    total_users = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM users WHERE role='provider'")
    total_providers = cursor.fetchone()["total"]

    cursor.execute("SELECT COUNT(*) as total FROM bookings")
    total_bookings = cursor.fetchone()["total"]

    cursor.execute("SELECT SUM(offered_price) as revenue FROM bookings WHERE status='completed'")
    revenue = cursor.fetchone()["revenue"] or 0

    return render_template(
        "admin/admin_dashboard.html",
        total_users=total_users,
        total_providers=total_providers,
        total_bookings=total_bookings,
        total_revenue=revenue
    )


#Admin Manage users route
@app.route("/admin-users")
def admin_users():

    search = request.args.get("search")

    page = request.args.get("page",1,type=int)
    per_page = 5
    offset = (page-1)*per_page

    query = "SELECT * FROM users WHERE role='user'"
    values = []

    if search:
        query += " AND (name LIKE %s OR email LIKE %s)"
        values.append(f"%{search}%")
        values.append(f"%{search}%")

    # total count
    count_query = query
    cursor.execute(count_query, tuple(values))
    total = len(cursor.fetchall())

    # pagination
    query += " LIMIT %s OFFSET %s"
    values.append(per_page)
    values.append(offset)

    cursor.execute(query, tuple(values))
    users = cursor.fetchall()

    total_pages = (total + per_page -1)//per_page

    return render_template(
        "admin/admin_users.html",
        users=users,
        page=page,
        total_pages=total_pages
    )


# Admin Toggle User Block/Unblock Route
@app.route("/admin-toggle-user/<int:user_id>")
def admin_toggle_user(user_id):

    if session.get("role") != "admin":
        return redirect("/login")

    reason = request.args.get("reason", "Policy Violation")

    cursor.execute("SELECT status FROM users WHERE user_id=%s", (user_id,))
    user = cursor.fetchone()

    if user["status"] == "active":
        cursor.execute("""
            UPDATE users
            SET status='blocked',
                block_reason=%s,
                blocked_at=%s
            WHERE user_id=%s
        """, (reason, datetime.now(), user_id))
    else:
        cursor.execute("""
            UPDATE users
            SET status='active',
                block_reason=NULL,
                blocked_at=NULL
            WHERE user_id=%s
        """, (user_id,))

    db.commit()
    return redirect(request.referrer)


#Admin Delete User Route
@app.route("/admin-delete-user/<int:user_id>")
def admin_delete_user(user_id):

    #  Delete bookings first
    cursor.execute("DELETE FROM bookings WHERE user_id=%s", (user_id,))

    #  Delete feedback if exists
    cursor.execute("DELETE FROM feedback WHERE user_id=%s", (user_id,))

    #  Delete skills if provider
    cursor.execute("DELETE FROM skills WHERE provider_id=%s", (user_id,))

    #  Now delete user
    cursor.execute("DELETE FROM users WHERE user_id=%s", (user_id,))

    db.commit()

    return redirect("/admin-users")


# Admin Manage Providers Route with Search
@app.route("/admin-providers")
def admin_providers():

    search = request.args.get("search")

    page = request.args.get("page",1,type=int)
    per_page = 5
    offset = (page-1)*per_page

    query = "SELECT * FROM users WHERE role='provider'"
    values = []

    if search:
        query += " AND (name LIKE %s OR email LIKE %s)"
        values.append(f"%{search}%")
        values.append(f"%{search}%")

    count_query = query
    cursor.execute(count_query, tuple(values))
    total = len(cursor.fetchall())

    query += " LIMIT %s OFFSET %s"
    values.append(per_page)
    values.append(offset)

    cursor.execute(query, tuple(values))
    providers = cursor.fetchall()

    total_pages = (total + per_page -1)//per_page

    return render_template(
        "admin/admin_providers.html",
        providers=providers,
        page=page,
        total_pages=total_pages
    )


# Admin Manage Bookings Route
@app.route("/admin-bookings")
def admin_bookings():

    user = request.args.get("user")
    provider = request.args.get("provider")
    skill = request.args.get("skill")
    status = request.args.get("status")

    page = request.args.get("page",1,type=int)
    per_page = 5
    offset = (page-1)*per_page

    query = """
    SELECT b.*, 
           u.name as user_name,
           p.name as provider_name,
           s.skill_name
    FROM bookings b
    JOIN users u ON b.user_id = u.user_id
    JOIN users p ON b.provider_id = p.user_id
    JOIN skills s ON b.skill_id = s.skill_id
    WHERE 1=1
    """

    values = []

    if user:
        query += " AND u.name LIKE %s"
        values.append(f"%{user}%")

    if provider:
        query += " AND p.name LIKE %s"
        values.append(f"%{provider}%")

    if skill:
        query += " AND s.skill_name LIKE %s"
        values.append(f"%{skill}%")

    if status:
        query += " AND b.status=%s"
        values.append(status)

    count_query = query
    cursor.execute(count_query, tuple(values))
    total = len(cursor.fetchall())

    query += " LIMIT %s OFFSET %s"
    values.append(per_page)
    values.append(offset)

    cursor.execute(query, tuple(values))
    bookings = cursor.fetchall()

    total_pages = (total + per_page -1)//per_page

    return render_template(
        "admin/admin_bookings.html",
        bookings=bookings,
        page=page,
        total_pages=total_pages
    )

# Admin Manage Skills Route
@app.route("/admin-skills")
def admin_skills():

    category = request.args.get("category")
    skill = request.args.get("skill")
    provider = request.args.get("provider")
    price = request.args.get("price")

    page = request.args.get("page",1,type=int)
    per_page = 5
    offset = (page-1)*per_page

    query = """
    SELECT s.*, u.name as provider_name
    FROM skills s
    JOIN users u ON s.provider_id = u.user_id
    WHERE 1=1
    """

    values = []

    if category:
        query += " AND s.category LIKE %s"
        values.append(f"%{category}%")

    if skill:
        query += " AND s.skill_name LIKE %s"
        values.append(f"%{skill}%")

    if provider:
        query += " AND u.name LIKE %s"
        values.append(f"%{provider}%")

    if price:
        try:
            search_price = float(price)
            query += " AND s.price = %s"
            values.append(search_price)
        except ValueError:
            pass

    count_query = query
    cursor.execute(count_query, tuple(values))
    total = len(cursor.fetchall())

    query += " LIMIT %s OFFSET %s"
    values.append(per_page)
    values.append(offset)

    cursor.execute(query, tuple(values))
    skills = cursor.fetchall()

    total_pages = (total + per_page -1)//per_page

    return render_template(
        "admin/admin_skills.html",
        skills=skills,
        page=page,
        total_pages=total_pages
    )


# Admin Manage Reviews Route
@app.route("/admin-reviews")
def admin_reviews():

    user = request.args.get("user")
    skill = request.args.get("skill")
    provider = request.args.get("provider")
    rating = request.args.get("rating")
    comment = request.args.get("comment")

    page = request.args.get("page",1,type=int)
    per_page = 5
    offset = (page-1)*per_page

    query = """
    SELECT r.*, u.name as user_name, s.skill_name, p.name as provider_name
    FROM feedback r
    JOIN users u ON r.user_id = u.user_id
    JOIN skills s ON r.skill_id = s.skill_id
    JOIN users p ON s.provider_id = p.user_id
    WHERE 1=1
    """

    values = []

    if user:
        query += " AND u.name LIKE %s"
        values.append(f"%{user}%")

    if skill:
        query += " AND s.skill_name LIKE %s"
        values.append(f"%{skill}%")

    if provider:
        query += " AND p.name LIKE %s"
        values.append(f"%{provider}%")

    if rating:
        query += " AND r.rating = %s"
        values.append(rating)

    if comment:
        query += " AND r.comment LIKE %s"
        values.append(f"%{comment}%")

    count_query = query
    cursor.execute(count_query, tuple(values))
    total = len(cursor.fetchall())

    query += " LIMIT %s OFFSET %s"
    values.append(per_page)
    values.append(offset)

    cursor.execute(query, tuple(values))
    reviews = cursor.fetchall()

    total_pages = (total + per_page -1)//per_page

    return render_template(
        "admin/admin_reviews.html",
        reviews=reviews,
        page=page,
        total_pages=total_pages
    )

# 🔍 SEARCH SUGGEST
@app.route("/search-suggest")
def search_suggest():
    q = request.args.get("q")

    cursor.execute("""
    SELECT skill_name 
    FROM skills 
    WHERE skill_name LIKE %s 
    LIMIT 5
    """, (f"%{q}%",))

    results = cursor.fetchall()
    return jsonify([r['skill_name'] for r in results])


# 🏠 HOME PAGE
@app.route("/")
def home():

    # ✅ STATS
    cursor.execute("SELECT COUNT(*) as total FROM users WHERE role='user'")
    total_users = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as total FROM users WHERE role='provider'")
    total_providers = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as total FROM bookings")
    total_bookings = cursor.fetchone()['total']


    # ✅ TOP CATEGORIES
    cursor.execute("""
    SELECT category, COUNT(*) as total
    FROM skills
    GROUP BY category
    ORDER BY total DESC
    LIMIT 4
    """)
    top_categories = cursor.fetchall()


    # ✅ POPULAR SERVICES 
    cursor.execute("""
    SELECT s.*, u.name as provider_name,

    ROUND(AVG(f.rating),1) as avg_rating,
    COUNT(DISTINCT f.feedback_id) as total_reviews,
    COUNT(DISTINCT b.booking_id) as total_bookings

    FROM skills s
    JOIN users u ON s.provider_id = u.user_id
    LEFT JOIN feedback f ON s.skill_id = f.skill_id
    LEFT JOIN bookings b ON s.skill_id = b.skill_id

    GROUP BY s.skill_id
    ORDER BY total_bookings DESC, avg_rating DESC
    LIMIT 3
    """)
    skills = cursor.fetchall()


    #  TRENDING
    cursor.execute("""
    SELECT s.*, u.name as provider_name,
    COUNT(b.booking_id) as bookings

    FROM skills s
    JOIN users u ON s.provider_id = u.user_id
    JOIN bookings b ON s.skill_id = b.skill_id

    GROUP BY s.skill_id
    ORDER BY bookings DESC
    LIMIT 3
    """)
    trending_skills = cursor.fetchall()


    # 📂 CATEGORY BASED
    cursor.execute("SELECT DISTINCT category FROM skills LIMIT 3")
    categories = cursor.fetchall()

    category_skills = []

    for cat in categories:
        cursor.execute("""
        SELECT * FROM skills 
        WHERE category=%s 
        LIMIT 4
        """, (cat['category'],))

        category_skills.append({
            "category": cat['category'],
            "skills": cursor.fetchall()
        })


    return render_template("index.html",
        total_users=total_users,
        total_providers=total_providers,
        total_bookings=total_bookings,
        top_categories=top_categories,
        skills=skills,
        trending_skills=trending_skills,
        category_skills=category_skills
    )

# ✅ SINGLE REGISTER ROUTE (FINAL)
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("auth.html") 

    role = request.form.get("role")  

    if not role:
        return render_template("auth.html", error="Please select User or Provider")

    name = request.form["name"].strip()
    identifier = request.form["identifier"].strip().lower()
    password = request.form["password"]
    confirm_password = request.form["confirm_password"]

    # ✅ Confirm password check
    if password != confirm_password:
        return render_template("auth.html", error="Password and Confirm Password do not match")

    # ✅ Strong password validation
    pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$'
    if not re.match(pattern, password):
        return render_template("auth.html",
                               error="Password must be at least 8 characters long and include uppercase, lowercase, number and special character.")

    # ✅ Detect email / phone
    is_email = "@" in identifier
    is_phone = identifier.isdigit() and len(identifier) == 10

    if not (is_email or is_phone):
        return render_template("auth.html",
                               error="Enter valid Email or 10-digit Phone")

    # ✅ Duplicate check
    if is_email:
        cursor.execute("SELECT user_id FROM users WHERE email=%s", (identifier,))
    else:
        cursor.execute("SELECT user_id FROM users WHERE phone=%s", (identifier,))

    if cursor.fetchone():
        return render_template("auth.html", error="Already registered. Please login.")

    hashed_password = generate_password_hash(password)

    # ✅ Insert user
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

        # Email or Phone check
        if "@" in identifier:
            cursor.execute("SELECT * FROM users WHERE email=%s", (identifier,))
        else:
            cursor.execute("SELECT * FROM users WHERE phone=%s", (identifier,))

        user = cursor.fetchone()

        if user and check_password_hash(user["password"], password):

        
            if user["role"] == "admin":
                return render_template("auth.html",
                                       error="Admin must login from Admin Panel")


            if user.get("status") == "blocked":
                return render_template("auth.html",
                                      error=f"Your account is blocked. Reason: {user.get('block_reason','Contact Admin')}")

        
            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]

            return redirect("/dashboard")

        else:
            return render_template("auth.html",
                                   error="Invalid Password or User not found")

    return render_template("auth.html")

#✅ Change Password Route
@app.route("/change-password", methods=["GET", "POST"])
def change_password():

    user_id = session.get("user_id")  

    if request.method == "POST":

        new_password = request.form["new_password"]
        confirm_password = request.form["confirm_password"]

        # =========================
        # 🔹 CASE 1: NOT LOGGED IN (Forgot Password)
        # =========================
        if not user_id:
            identifier = request.form.get("identifier")

            if not identifier:
                return render_template("change_password.html",
                                       error="Enter Email or Phone")

            if new_password != confirm_password:
                return render_template("change_password.html",
                                       error="Passwords do not match")

            new_hash = generate_password_hash(new_password)

            if "@" in identifier:
                cursor.execute("UPDATE users SET password=%s WHERE email=%s",
                               (new_hash, identifier))
            else:
                cursor.execute("UPDATE users SET password=%s WHERE phone=%s",
                               (new_hash, identifier))

            db.commit()

            return render_template("change_password.html",
                                   success="Password reset successful")

        # =========================
        # 🔹 CASE 2: LOGGED IN
        # =========================
        old_password = request.form["old_password"]

        cursor.execute("SELECT password FROM users WHERE user_id=%s", (user_id,))
        user = cursor.fetchone()

        if not check_password_hash(user["password"], old_password):
            return render_template("change_password.html",
                                   error="Old password incorrect")

        if new_password != confirm_password:
            return render_template("change_password.html",
                                   error="Passwords do not match")

        new_hash = generate_password_hash(new_password)

        cursor.execute("UPDATE users SET password=%s WHERE user_id=%s",
                       (new_hash, user_id))

        db.commit()

        return render_template("change_password.html",
                               success="Password updated successfully")

    return render_template("change_password.html")


# ✅ Dashboard 
@app.route("/dashboard")
def dashboard():

    if "user_id" not in session:
        return redirect("/login")

    cursor.execute("SELECT status, block_reason FROM users WHERE user_id=%s",
                   (session["user_id"],))
    user = cursor.fetchone()

    if user["status"] == "blocked":
        session.clear()
        return render_template("login.html",
                               error=f"Your account is blocked. Reason: {user.get('block_reason','Contact Admin')}")

    return render_template("dashboard.html",
                           user_status=user["status"])



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


# View All Skills 
@app.route("/all-skills")
def all_skills():

    category = request.args.get("category")
    search = request.args.get("search")   

    user_id = session.get("user_id")
    role = session.get("role")
    hide_skill = session.pop("hide_skill", None)

    base_query = """
    SELECT s.*, 
           u.name AS provider_name,
           (SELECT AVG(rating) 
            FROM feedback 
            WHERE provider_id = s.provider_id) AS avg_rating
    FROM skills s
    JOIN users u ON s.provider_id = u.user_id
    """

    conditions = []
    values = []

    # Category filter
    if category:
        conditions.append("s.category=%s")
        values.append(category)

    # 🔎 Search filter 
    if search:
        conditions.append("(s.skill_name LIKE %s OR u.name LIKE %s)")
        values.append(f"%{search}%")
        values.append(f"%{search}%")

    # Hide already booked skills
    if user_id and role == "user":
        conditions.append("""
            s.skill_id NOT IN (
                SELECT skill_id FROM bookings
                WHERE user_id=%s
                AND status IN ('pending','accepted')
            )
        """)
        values.append(user_id)

    # Hide skill after booking
    if hide_skill:
        conditions.append("s.skill_id != %s")
        values.append(hide_skill)

    if conditions:
        base_query += " WHERE " + " AND ".join(conditions)

    cursor.execute(base_query, tuple(values))
    skills = cursor.fetchall()

    response = make_response(
        render_template("all_skills.html", skills=skills)
    )
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
        (skill_id, user_id, provider_id, offered_price, unit, service_date, service_time, remark)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s)
    """, (skill_id, user_id, provider_id, offered_price, unit, service_date, service_time, request.form.get("remark")))

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
        SELECT b.*, 
               s.skill_name,
               u.name as provider_name
        FROM bookings b
        JOIN skills s ON b.skill_id = s.skill_id
        JOIN users u ON b.provider_id = u.user_id
        WHERE b.user_id=%s
        ORDER BY b.booking_id DESC
    """, (user_id,))

    bookings = cursor.fetchall()

    # Date & Time Convert
    for b in bookings:

        # -------- DATE --------
        if b.get("service_date"):
            if isinstance(b["service_date"], date):
                b["display_date"] = b["service_date"].strftime("%d %b %Y")
            else:
                dt_obj = datetime.strptime(str(b["service_date"]), "%Y-%m-%d")
                b["display_date"] = dt_obj.strftime("%d %b %Y")

        # -------- TIME --------
        if b.get("service_time"):
            if isinstance(b["service_time"], time):
                b["display_time"] = b["service_time"].strftime("%I:%M %p")
            else:
                time_obj = datetime.strptime(str(b["service_time"]), "%H:%M:%S")
                b["display_time"] = time_obj.strftime("%I:%M %p")
        else:
            b["display_time"] = "Not Set"

        # -------- FEEDBACK CHECK --------
        cursor.execute(
            "SELECT feedback_id FROM feedback WHERE booking_id=%s",
            (b["booking_id"],)
        )
        feedback = cursor.fetchone()

        b["feedback_given"] = True if feedback else False

    return render_template("my_bookings.html", bookings=bookings)

# View Bookings for Providers route
@app.route("/provider-bookings")
def provider_bookings():

    if 'user_id' not in session:
        return redirect("/login")

    provider_id = session['user_id']

    # Booking fetch
    cursor.execute("""
        SELECT b.*, s.skill_name, u.name as user_name
        FROM bookings b
        JOIN skills s ON b.skill_id = s.skill_id
        JOIN users u ON b.user_id = u.user_id
        WHERE b.provider_id=%s
    """, (provider_id,))

    bookings = cursor.fetchall()

    # ✅ Date & Time Convert (FIXED INDENTATION)
    for b in bookings:

        # Date Convert
        if b.get("service_date"):
            if isinstance(b["service_date"], date):
                b["display_date"] = b["service_date"].strftime("%d %b %Y")
            else:
                dt_obj = datetime.strptime(str(b["service_date"]), "%Y-%m-%d")
                b["display_date"] = dt_obj.strftime("%d %b %Y")

        # Time Convert
        if b.get("service_time"):
            if isinstance(b["service_time"], time):
                b["display_time"] = b["service_time"].strftime("%I:%M %p")
            else:
                time_obj = datetime.strptime(str(b["service_time"]), "%H:%M:%S")
                b["display_time"] = time_obj.strftime("%I:%M %p")

    # ⭐ Average Rating
    cursor.execute("""
        SELECT AVG(rating) as avg_rating, COUNT(*) as total_reviews
        FROM feedback
        WHERE provider_id=%s
    """, (provider_id,))
    rating_data = cursor.fetchone()

    # ⭐ All Reviews
    cursor.execute("""
        SELECT f.*, 
               u.name as user_name,
               s.skill_name,
               b.service_date,
               b.service_time
        FROM feedback f
        JOIN users u ON f.user_id = u.user_id
        JOIN bookings b ON f.booking_id = b.booking_id
        JOIN skills s ON f.skill_id = s.skill_id
        WHERE f.provider_id=%s
        ORDER BY f.created_at DESC
    """, (provider_id,))

    reviews = cursor.fetchall()

    # ✅ Reviews Date & Time Convert (FIXED)
    for r in reviews:

        # Booking Date
        if r.get("service_date"):
            if isinstance(r["service_date"], date):
                r["display_date"] = r["service_date"].strftime("%d %b %Y")
            else:
                dt_obj = datetime.strptime(str(r["service_date"]), "%Y-%m-%d")
                r["display_date"] = dt_obj.strftime("%d %b %Y")

        # Booking Time
        if r.get("service_time"):
            if isinstance(r["service_time"], time):
                r["display_time"] = r["service_time"].strftime("%I:%M %p")
            else:
                time_obj = datetime.strptime(str(r["service_time"]), "%H:%M:%S")
                r["display_time"] = time_obj.strftime("%I:%M %p")

        # Feedback Created Time
        if r.get("created_at"):
            dt_obj = r["created_at"]
            if isinstance(dt_obj, datetime):
                r["display_created_at"] = dt_obj.strftime("%d %b %Y • %I:%M %p").lstrip("0")
            else:
                dt_obj = datetime.strptime(str(dt_obj), "%Y-%m-%d %H:%M:%S")
                r["display_created_at"] = dt_obj.strftime("%d %b %Y • %I:%M %p").lstrip("0")

    return render_template(
        "provider_bookings.html",
        bookings=bookings,
        rating_data=rating_data,
        reviews=reviews
    )

# Update Booking Status (Accept/Reject) for Providers route
@app.route("/update-booking/<int:booking_id>/<status>", methods=["POST"])
def update_booking(booking_id, status):

    if "user_id" not in session:
        return redirect("/login")


    if status not in ["accepted", "rejected", "completed"]:
        return redirect("/provider-bookings")

    cursor.execute("""
        UPDATE bookings
        SET status=%s
        WHERE booking_id=%s AND provider_id=%s
    """, (status, booking_id, session["user_id"]))

    db.commit()

    return redirect("/provider-bookings")

# Mark Completed Route for Providers
@app.route("/mark-completed/<int:booking_id>", methods=["POST"])
def mark_completed(booking_id):

    if "user_id" not in session:
        return redirect("/login")

    cursor.execute("""
        UPDATE bookings 
        SET status='completed'
        WHERE booking_id=%s AND provider_id=%s
    """, (booking_id, session["user_id"]))

    db.commit()

    return redirect("/provider-bookings")

# Give Feedback Route
@app.route("/give-feedback/<int:booking_id>", methods=["GET", "POST"])
def give_feedback(booking_id):

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    # booking verify (completed only)
    cursor.execute("""
        SELECT * FROM bookings
        WHERE booking_id=%s 
        AND user_id=%s 
        AND status='completed'
    """, (booking_id, user_id))

    booking = cursor.fetchone()

    if not booking:
        return redirect("/my-bookings")

    # Already submitted check
    cursor.execute(
        "SELECT feedback_id FROM feedback WHERE booking_id=%s",
        (booking_id,)
    )
    existing = cursor.fetchone()

    if existing:
        return redirect("/my-bookings")

    if request.method == "POST":
        rating = request.form["rating"]
        comment = request.form["comment"]

        cursor.execute("""
            INSERT INTO feedback
            (booking_id, skill_id, user_id, provider_id, rating, comment)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (
            booking_id,
            booking["skill_id"],
            user_id,
            booking["provider_id"],
            rating,
            comment
        ))

        # mark feedback given
        cursor.execute("""
            UPDATE bookings
            SET feedback_given = 1
            WHERE booking_id=%s
        """, (booking_id,))

        db.commit()

        return redirect("/my-bookings")

    return render_template("give_feedback.html", booking=booking)

#my feedback route
@app.route("/my-feedbacks")
def my_feedbacks():

    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    sort = request.args.get("sort")
    rating_filter = request.args.get("rating")

    query = """
        SELECT f.*, s.skill_name, u.name as provider_name
        FROM feedback f
        JOIN skills s ON f.skill_id = s.skill_id
        JOIN users u ON f.provider_id = u.user_id
        WHERE f.user_id = %s
    """

    values = [user_id]

    if rating_filter:
        query += " AND f.rating = %s"
        values.append(rating_filter)

    if sort == "rating_high":
        query += " ORDER BY f.rating DESC"
    elif sort == "rating_low":
        query += " ORDER BY f.rating ASC"
    elif sort == "latest":
        query += " ORDER BY f.created_at DESC"
    elif sort == "oldest":
        query += " ORDER BY f.created_at ASC"

    cursor.execute(query, tuple(values))
    feedbacks = cursor.fetchall()

    # Time convert for user feedback list
    for f in feedbacks:
     if f.get("created_at"):

        dt_obj = f["created_at"]

        if isinstance(dt_obj, datetime):
            f["display_date"] = dt_obj.strftime("%d %b %Y")
            f["display_time"] = dt_obj.strftime("%I:%M %p").lstrip("0")
        else:
            dt_obj = datetime.strptime(str(dt_obj), "%Y-%m-%d %H:%M:%S")
            f["display_date"] = dt_obj.strftime("%d %b %Y")
            f["display_time"] = dt_obj.strftime("%I:%M %p").lstrip("0")

    return render_template("my_feedbacks.html", feedbacks=feedbacks)

# Delete Feedback route
@app.route("/delete-feedback/<int:feedback_id>", methods=["POST"])
def delete_feedback(feedback_id):

    if "user_id" not in session:
        return redirect("/login")

    cursor.execute("""
        DELETE FROM feedback
        WHERE feedback_id=%s AND user_id=%s
    """, (feedback_id, session["user_id"]))

    db.commit()

    return redirect("/my-feedbacks")

#Edit Feedback route
@app.route("/edit-feedback/<int:feedback_id>", methods=["GET","POST"])
def edit_feedback(feedback_id):

    if "user_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        rating = request.form["rating"]
        comment = request.form["comment"]

        cursor.execute("""
            UPDATE feedback
            SET rating=%s, comment=%s
            WHERE feedback_id=%s AND user_id=%s
        """, (rating, comment, feedback_id, session["user_id"]))

        db.commit()
        return redirect("/my-feedbacks")

    cursor.execute("""
        SELECT * FROM feedback
        WHERE feedback_id=%s AND user_id=%s
    """, (feedback_id, session["user_id"]))

    feedback = cursor.fetchone()

    return render_template("edit_feedback.html", feedback=feedback)

if __name__ == "__main__":
    app.run(debug=True)


