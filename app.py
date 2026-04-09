import code
import os
import random
from flask import jsonify
from werkzeug.utils import secure_filename
from dotenv import load_dotenv
load_dotenv()
from flask import jsonify, make_response
from flask import Flask, render_template, request, redirect, session, url_for
from datetime import datetime, time, date
import re
import mysql.connector
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import timedelta
from flask import flash
mysql.connector.Error

app = Flask(__name__)
app.secret_key = "skill_exchange_secret"

#  Session Timeout Settings
app.config['SESSION_PERMANENT'] = False
app.config['PERMANENT_SESSION_LIFETIME'] = timedelta(minutes=30)

#  MySQL Connection
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


# Admin Toggle Provider Block/Unblock Route
@app.route("/admin-toggle-provider/<int:provider_id>")
def admin_toggle_provider(provider_id):
    if session.get("role") != "admin":
        return redirect("/login")

    reason = request.args.get("reason", "Policy Violation")

    cursor.execute("SELECT status FROM users WHERE user_id=%s", (provider_id,))
    user = cursor.fetchone()

    if user["status"] == "active":
        cursor.execute("""
            UPDATE users
            SET status='blocked',
                block_reason=%s,
                blocked_at=%s
            WHERE user_id=%s
        """, (reason, datetime.now(), provider_id))
    else:
        cursor.execute("""
            UPDATE users
            SET status='active',
                block_reason=NULL,
                blocked_at=NULL
            WHERE user_id=%s
        """, (provider_id,))

    db.commit()
    return redirect(request.referrer)

# Admin Delete Provider Route 
@app.route("/admin-delete-provider/<int:provider_id>")
def admin_delete_provider(provider_id):
    if session.get("role") != "admin":
        return redirect("/login")

    # 1. Delete provider bookings
    cursor.execute("DELETE FROM bookings WHERE provider_id=%s", (provider_id,))
    # 2. Delete provider reviews
    cursor.execute("DELETE FROM feedback WHERE provider_id=%s", (provider_id,))
    # 3. Delete Provider skills
    cursor.execute("DELETE FROM skills WHERE provider_id=%s", (provider_id,))
    # 4. Now delete Provider
    cursor.execute("DELETE FROM users WHERE user_id=%s", (provider_id,))

    db.commit()
    return redirect("/admin-providers")


# Admin Manage Providers Route 
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

# SEARCH SUGGEST
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


#  HOME PAGE
@app.route("/")
def home():

    # STATS
    cursor.execute("SELECT COUNT(*) as total FROM users WHERE role='user'")
    total_users = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as total FROM users WHERE role='provider'")
    total_providers = cursor.fetchone()['total']

    cursor.execute("SELECT COUNT(*) as total FROM bookings")
    total_bookings = cursor.fetchone()['total']

    #  TOP CATEGORIES
    cursor.execute("""
    SELECT category, COUNT(*) as total
    FROM skills
    GROUP BY category
    ORDER BY total DESC
    LIMIT 4
    """)
    top_categories = cursor.fetchall()

    #  POPULAR SERVICES 
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
 
    # CATEGORY BASED (FIXED: Added Provider Name)
  
    cursor.execute("SELECT DISTINCT category FROM skills LIMIT 3")
    categories = cursor.fetchall()

    category_skills = []

    for cat in categories:
        # JOIN users table 
        cursor.execute("""
        SELECT s.*, u.name as provider_name 
        FROM skills s
        JOIN users u ON s.provider_id = u.user_id
        WHERE s.category=%s 
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

#  SINGLE REGISTER ROUTE
@app.route("/register", methods=["GET", "POST"])
def register():

    if request.method == "GET":
        return render_template("auth.html") 

    role = request.form.get("role")  

    if not role:
        return render_template("auth.html", error="Please select User or Provider", show_signup=True)

    name = request.form["name"].strip()
    identifier = request.form["identifier"].strip().lower()
    password = request.form["password"]
    
    #  Strong password validation
    pattern = r'^(?=.*[a-z])(?=.*[A-Z])(?=.*\d)(?=.*[@$!%*?&]).{8,}$'
    if not re.match(pattern, password):
        return render_template("auth.html",
                               error="Password must be at least 8 characters long and include uppercase, lowercase, number and special character.", show_signup=True)

    #  Detect email / phone
    is_email = "@" in identifier
    is_phone = identifier.isdigit() and len(identifier) == 10

    if not (is_email or is_phone):
        return render_template("auth.html",
                               error="Enter valid Email or 10-digit Phone", show_signup=True)

    # Duplicate check
    if is_email:
        cursor.execute("SELECT user_id FROM users WHERE email=%s", (identifier,))
    else:
        cursor.execute("SELECT user_id FROM users WHERE phone=%s", (identifier,))

    if cursor.fetchone():
        return render_template("auth.html", error="Already registered. Please login.", show_signup=True)

    hashed_password = generate_password_hash(password)

    #  Insert user
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
    
    # ---  Success message with delay instead of instant redirect ---
    return render_template("auth.html", 
                           success_msg="Registration Successful! Redirecting to login...", 
                           redirect_to="/login", 
                           show_signup=True)

#  Login (Email OR Phone)
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

            session.clear()
            
            # for new session 
            session["user_id"] = user["user_id"]
            session["user_name"] = user["name"]
            session["role"] = user["role"]

            session.permanent = False

            # --- Success message with delay instead of instant redirect ---
            return render_template("auth.html", 
                                   success_msg="Login Successful! Welcome back...", 
                                   redirect_to="/dashboard", 
                                   show_signup=False)

        else:
            return render_template("auth.html",
                                   error="Invalid Password or User not found")

    return render_template("auth.html")


#  Change password route
@app.route("/change-password", methods=["GET", "POST"])
def change_password():
    
    if request.args.get("action") == "forgot":
        session.clear()
        return redirect("/change-password")

    user_id = session.get("user_id")  

    if request.method == "POST":
        new_password = request.form.get("new_password")
        confirm_password = request.form.get("confirm_password")

        if not new_password or not confirm_password:
            return render_template("change_password.html", error="Please fill new password fields")

        if new_password != confirm_password:
            return render_template("change_password.html", error="Passwords do not match")

        new_hash = generate_password_hash(new_password)

        #  CASE 1: NOT LOGGED IN (Forgot Password)
        if not user_id:
            identifier = request.form.get("identifier")
            if not identifier:
                return render_template("change_password.html", error="Enter Email or Phone number")

            if "@" in identifier:
                cursor.execute("SELECT * FROM users WHERE email=%s", (identifier,))
            else:
                cursor.execute("SELECT * FROM users WHERE phone=%s", (identifier,))
            
            user = cursor.fetchone()
            if not user:
                return render_template("change_password.html", error="User not found")

            if "@" in identifier:
                cursor.execute("UPDATE users SET password=%s WHERE email=%s", (new_hash, identifier))
            else:
                cursor.execute("UPDATE users SET password=%s WHERE phone=%s", (new_hash, identifier))

            db.commit()
            return render_template("change_password.html", success="Password reset successful! You can now login.")

        #  CASE 2: LOGGED IN (Change Password)
        else:
            old_password = request.form.get("old_password")
            if not old_password:
                return render_template("change_password.html", error="Enter your old password")

            cursor.execute("SELECT password FROM users WHERE user_id=%s", (user_id,))
            user = cursor.fetchone()

            if not check_password_hash(user["password"], old_password):
                return render_template("change_password.html", error="Old password incorrect")

            cursor.execute("UPDATE users SET password=%s WHERE user_id=%s", (new_hash, user_id))
            db.commit()

            return render_template("change_password.html", success="Password updated successfully!")

    return render_template("change_password.html")


#  Dashboard 
@app.route("/dashboard")
def dashboard():

    # 1. Login Check
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]
  
    # 2. USER STATUS CHECK
    cursor.execute("SELECT status, block_reason FROM users WHERE user_id=%s", (user_id,))
    user = cursor.fetchone()

    if user["status"] == "blocked":
        session.clear()
        return render_template("auth.html",
                               error=f"Your account is blocked. Reason: {user.get('block_reason','Contact Admin')}")

    # 3. STATS CALCULATION
    
    # Total bookings
    cursor.execute("""
        SELECT COUNT(*) as total 
        FROM bookings 
        WHERE user_id=%s OR provider_id=%s
    """, (user_id, user_id))
    total_bookings = cursor.fetchone()["total"]

    # Pending
    cursor.execute("""
        SELECT COUNT(*) as total 
        FROM bookings 
        WHERE (user_id=%s OR provider_id=%s) AND status='pending'
    """, (user_id, user_id))
    pending_bookings = cursor.fetchone()["total"]

    # Completed
    cursor.execute("""
        SELECT COUNT(*) as total 
        FROM bookings 
        WHERE (user_id=%s OR provider_id=%s) AND status='completed'
    """, (user_id, user_id))
    completed_bookings = cursor.fetchone()["total"]

    # Total skills 
    cursor.execute("SELECT COUNT(*) as total FROM skills WHERE provider_id=%s", (user_id,))
    total_skills = cursor.fetchone()["total"]

    # Total feedback
    cursor.execute("SELECT COUNT(*) as total FROM feedback WHERE user_id=%s", (user_id,))
    total_feedbacks = cursor.fetchone()["total"]


    # 4.  SMART RECENT ACTIVITY 
    raw_activities = []

    # Fetch Latest Skills 
    unique_skills = set()
    cursor.execute("""
        SELECT skill_name, skill_id as item_id 
        FROM skills 
        WHERE provider_id=%s 
        ORDER BY skill_id DESC LIMIT 5
    """, (user_id,))
    for row in cursor.fetchall():
        if row['skill_name'] not in unique_skills:
            unique_skills.add(row['skill_name'])
            raw_activities.append({
                "msg": f"Added skill: {row['skill_name']}",
                "id": row['item_id']
            })

    # Fetch Latest Bookings 
    unique_bookings = set()
    cursor.execute("""
        SELECT s.skill_name, b.booking_id as item_id 
        FROM bookings b
        JOIN skills s ON b.skill_id = s.skill_id
        WHERE b.user_id=%s OR b.provider_id=%s
        ORDER BY b.booking_id DESC LIMIT 5
    """, (user_id, user_id))
    for row in cursor.fetchall():
        if row['skill_name'] not in unique_bookings:
            unique_bookings.add(row['skill_name'])
            raw_activities.append({
                "msg": f"Booked: {row['skill_name']}", 
                "id": row['item_id']
            })

    # Fetch Latest Feedbacks
    cursor.execute("""
        SELECT u.name as receiver_name, f.feedback_id as item_id 
        FROM feedback f
        JOIN users u ON f.provider_id = u.user_id
        WHERE f.user_id=%s 
        ORDER BY f.feedback_id DESC LIMIT 5
    """, (user_id,))

    for row in cursor.fetchall():
        raw_activities.append({
            "msg": f"Given feedback to: {row['receiver_name']}",
            "id": row['item_id']
        })

    # Sort mixed activities by ID 
    raw_activities.sort(key=lambda x: x["id"], reverse=True)
    
    # Extract only the messages and limit strictly to top 5
    recent_data = [item["msg"] for item in raw_activities[:5]]

    # 5. FINAL RENDER
    return render_template("dashboard.html",
                           user_status=user["status"],
                           total_skills=total_skills,
                           total_feedbacks=total_feedbacks,
                           total_bookings=total_bookings,
                           pending_bookings=pending_bookings,
                           completed_bookings=completed_bookings,
                           recent_data=recent_data)

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
           
            upload_dir = os.path.join('static', 'uploads', 'skill_pics')
            
            if not os.path.exists(upload_dir):
                os.makedirs(upload_dir)
            photo_filename = photo.filename
            photo.save(os.path.join(upload_dir, photo_filename))
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

    provider_id = session["user_id"]

    
    cursor.execute("SELECT photo FROM skills WHERE skill_id=%s AND provider_id=%s", (skill_id, provider_id))
    skill_to_delete = cursor.fetchone()

    # delete skill from db
    cursor.execute(
        "DELETE FROM skills WHERE skill_id=%s AND provider_id=%s",
        (skill_id, provider_id)
    )
    db.commit()

    # delete skill images from uploads folder
    if skill_to_delete and skill_to_delete['photo']:
        photo_path = os.path.join('static', 'uploads', 'skill_pics', skill_to_delete['photo'])
        if os.path.exists(photo_path):
            try:
                os.remove(photo_path)
            except Exception as e:
                pass

    return redirect("/my-skills")

# Edit Skill Route
@app.route("/edit-skill/<int:skill_id>", methods=["GET", "POST"])
def edit_skill(skill_id):
    if "user_id" not in session:
        return redirect("/login")

    provider_id = session["user_id"]

    if request.method == "GET":
        cursor.execute(
            "SELECT * FROM skills WHERE skill_id=%s AND provider_id=%s",
            (skill_id, provider_id)
        )
        skill = cursor.fetchone()
        if not skill:
            return redirect("/my-skills")
        return render_template("edit_skill.html", skill=skill)

    skill_name = request.form["skill_name"].strip()
    category = request.form["category"]
    price = request.form["price"]
    unit = request.form["unit"]
    experience = request.form["experience"]
    description = request.form["description"]

    photo = request.files.get("photo")
    if photo and photo.filename != "":
        upload_dir = os.path.join('static', 'uploads', 'skill_pics')
        if not os.path.exists(upload_dir):
            os.makedirs(upload_dir)
            
        cursor.execute("SELECT photo FROM skills WHERE skill_id=%s AND provider_id=%s", (skill_id, provider_id))
        old_skill_data = cursor.fetchone()
            
        photo_filename = photo.filename
        photo.save(os.path.join(upload_dir, photo_filename))
        
        if old_skill_data and old_skill_data['photo']:
            old_photo_path = os.path.join(upload_dir, old_skill_data['photo'])
            if os.path.exists(old_photo_path):
                try:
                    os.remove(old_photo_path)
                except Exception as e:
                    pass
        
        cursor.execute("""
            UPDATE skills 
            SET skill_name=%s, category=%s, price=%s, unit=%s, experience=%s, description=%s, photo=%s 
            WHERE skill_id=%s AND provider_id=%s
        """, (skill_name, category, price, unit, experience, description, photo_filename, skill_id, provider_id))
    else:
        cursor.execute("""
            UPDATE skills 
            SET skill_name=%s, category=%s, price=%s, unit=%s, experience=%s, description=%s 
            WHERE skill_id=%s AND provider_id=%s
        """, (skill_name, category, price, unit, experience, description, skill_id, provider_id))

    db.commit()
    
    # ---  JSON Response for AJAX ---
    return jsonify({"success": True, "message": "Service updated successfully!"})


# 🟢 Toggle Skill Status (Active/Inactive) Route
@app.route("/toggle-skill-status/<int:skill_id>", methods=["POST"])
def toggle_skill_status(skill_id):
    if "user_id" not in session or session.get("role") != "provider":
        return redirect("/login")
    
    # चेक करें कि अभी स्टेटस क्या है
    cursor.execute("SELECT status FROM skills WHERE skill_id=%s AND provider_id=%s", (skill_id, session["user_id"]))
    skill = cursor.fetchone()
    
    if skill:
        # अगर active है तो inactive करें, और inactive है तो active करें
        new_status = 'inactive' if skill['status'] == 'active' else 'active'
        cursor.execute("UPDATE skills SET status=%s WHERE skill_id=%s", (new_status, skill_id))
        db.commit()
        
    return redirect(request.referrer)

# View All Skills 
@app.route("/all-skills")
def all_skills():

    category = request.args.get("category")
    search = request.args.get("search")   

    user_id = session.get("user_id")
    role = session.get("role")
    hide_skill = session.pop("hide_skill", None)
    
    user_name = session.get("user_name", "Guest")

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

    # Search filter 
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
        render_template("all_skills.html", skills=skills, user_name=user_name)
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

    # Convert to 24hr format for DB
    time_string = f"{hour}:{minute} {ampm}"
    time_obj = datetime.strptime(time_string, "%I:%M %p")
    service_time = time_obj.strftime("%H:%M:%S")  

    # Duplicate Check
    cursor.execute("""
        SELECT * FROM bookings
        WHERE skill_id=%s AND user_id=%s AND service_date=%s AND status IN ('pending','accepted')
    """, (skill_id, user_id, service_date))

    existing = cursor.fetchone()
    if existing:
        return redirect("/all-skills")

    # Get provider id and skill name 
    cursor.execute("SELECT provider_id, skill_name FROM skills WHERE skill_id=%s", (skill_id,))
    skill = cursor.fetchone()

    if not skill:
        return redirect("/all-skills")

    provider_id = skill["provider_id"]
    skill_name = skill["skill_name"]

    #  New Data & OTP Logic 
    address = request.form.get("address")
    contact_phone = request.form.get("contact_phone")
    remark = request.form.get("remark")
    
    # Generate a random 4-digit OTP
    otp_code = str(random.randint(1000, 9999))
    # -------------------------------------

    # Insert new booking with address, phone, and otp
    cursor.execute("""
        INSERT INTO bookings 
        (skill_id, user_id, provider_id, offered_price, unit, service_date, service_time, remark, address, contact_phone, otp_code, status)
        VALUES (%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,%s,'pending')
    """, (skill_id, user_id, provider_id, offered_price, unit, service_date, service_time, remark, address, contact_phone, otp_code))

    # Send Notification to Provider
    notif_msg = f"New booking request for '{skill_name}' from {session['user_name']}."
    cursor.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)", (provider_id, notif_msg))

    db.commit()
    session["hide_skill"] = skill_id

    return redirect(url_for("all_skills"))


# Cancel Booking Route
@app.route("/cancel-booking/<int:booking_id>", methods=["POST"])
def cancel_booking(booking_id):
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    #  Get details for notification before updating
    cursor.execute("""
        SELECT b.provider_id, s.skill_name 
        FROM bookings b JOIN skills s ON b.skill_id = s.skill_id 
        WHERE b.booking_id=%s AND b.user_id=%s
    """, (booking_id, user_id))
    b_data = cursor.fetchone()

    # Cancel the booking
    cursor.execute("""
        UPDATE bookings SET status='cancelled'
        WHERE booking_id=%s AND user_id=%s AND status IN ('pending','accepted')
    """, (booking_id, user_id))

    #  Send Notification to Provider
    if b_data:
        notif_msg = f"Booking for '{b_data['skill_name']}' was cancelled by the user."
        cursor.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)", (b_data['provider_id'], notif_msg))

    db.commit()
    return redirect("/my-bookings")

# View My Bookings for user route
@app.route("/my-bookings")
def my_bookings():

    if 'user_id' not in session:
        return redirect("/login")

    user_id = session['user_id']

    #  SQL Query 
    cursor.execute("""
        SELECT b.*, 
               s.skill_name,
               u.name as provider_name,
               u.phone as provider_phone 
        FROM bookings b
        JOIN skills s ON b.skill_id = s.skill_id
        JOIN users u ON b.provider_id = u.user_id
        WHERE b.user_id=%s
        ORDER BY b.booking_id DESC
    """, (user_id,))

    bookings = cursor.fetchall()

    # Date & Time Convert 
    for b in bookings:

        #  DATE 
        if b.get("service_date"):
            if isinstance(b["service_date"], date):
                b["display_date"] = b["service_date"].strftime("%d %b %Y")
            else:
                dt_obj = datetime.strptime(str(b["service_date"]), "%Y-%m-%d")
                b["display_date"] = dt_obj.strftime("%d %b %Y")

        #  TIME 
        if b.get("service_time"):
            if isinstance(b["service_time"], time):
                b["display_time"] = b["service_time"].strftime("%I:%M %p")
            else:
                time_obj = datetime.strptime(str(b["service_time"]), "%H:%M:%S")
                b["display_time"] = time_obj.strftime("%I:%M %p")
        else:
            b["display_time"] = "Not Set"

        # FEEDBACK CHECK 
        cursor.execute(
            "SELECT feedback_id FROM feedback WHERE booking_id=%s",
            (b["booking_id"],)
        )
        feedback = cursor.fetchone()

        b["feedback_given"] = True if feedback else False

    return render_template("my_bookings.html", bookings=bookings)


#  VIEW BOOKINGS FOR PROVIDERS 
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
        ORDER BY b.booking_id DESC
    """, (provider_id,))

    bookings = cursor.fetchall()

    #  Date & Time Convert 
    for b in bookings:
        if b.get("service_date"):
            if isinstance(b["service_date"], date):
                b["display_date"] = b["service_date"].strftime("%d %b %Y")
            else:
                dt_obj = datetime.strptime(str(b["service_date"]), "%Y-%m-%d")
                b["display_date"] = dt_obj.strftime("%d %b %Y")

        if b.get("service_time"):
            if isinstance(b["service_time"], time):
                b["display_time"] = b["service_time"].strftime("%I:%M %p")
            else:
                time_obj = datetime.strptime(str(b["service_time"]), "%H:%M:%S")
                b["display_time"] = time_obj.strftime("%I:%M %p")

    return render_template("provider_bookings.html", bookings=bookings)


# VIEW REVIEWS FOR PROVIDERS 
@app.route("/provider-reviews")
def provider_reviews():
    if 'user_id' not in session:
        return redirect("/login")

    provider_id = session['user_id']

    #  Average Rating
    cursor.execute("""
        SELECT AVG(rating) as avg_rating, COUNT(*) as total_reviews
        FROM feedback
        WHERE provider_id=%s
    """, (provider_id,))
    rating_data = cursor.fetchone()

    #  All Reviews
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

    # Reviews Date & Time Convert 
    for r in reviews:
        if r.get("service_date"):
            if isinstance(r["service_date"], date):
                r["display_date"] = r["service_date"].strftime("%d %b %Y")
            else:
                dt_obj = datetime.strptime(str(r["service_date"]), "%Y-%m-%d")
                r["display_date"] = dt_obj.strftime("%d %b %Y")

        if r.get("service_time"):
            if isinstance(r["service_time"], time):
                r["display_time"] = r["service_time"].strftime("%I:%M %p")
            else:
                time_obj = datetime.strptime(str(r["service_time"]), "%H:%M:%S")
                r["display_time"] = time_obj.strftime("%I:%M %p")

        if r.get("created_at"):
            dt_obj = r["created_at"]
            if isinstance(dt_obj, datetime):
                r["display_created_at"] = dt_obj.strftime("%d %b %Y • %I:%M %p").lstrip("0")
            else:
                dt_obj = datetime.strptime(str(dt_obj), "%Y-%m-%d %H:%M:%S")
                r["display_created_at"] = dt_obj.strftime("%d %b %Y • %I:%M %p").lstrip("0")

    return render_template("provider_reviews.html", rating_data=rating_data, reviews=reviews)

# Update Booking Status (Accept/Reject) for Providers route
@app.route("/update-booking/<int:booking_id>/<status>", methods=["POST"])
def update_booking(booking_id, status):
    if "user_id" not in session:
        return redirect("/login")

    if status not in ["accepted", "rejected", "completed"]:
        return redirect("/provider-bookings")

    provider_id = session["user_id"]

    # --- Profile Completion Check (Phone Number) ---
    if status == "accepted":
        cursor.execute("SELECT phone FROM users WHERE user_id=%s", (provider_id,))
        provider_data = cursor.fetchone()
        
        # Check if phone is None, empty string, or 'Not provided'
        phone = provider_data['phone'] if type(provider_data) is dict else provider_data[0]
        
        if not phone or str(phone).strip() == "" or str(phone).lower() == "not provided":
            flash("Action Required: Please update your phone number in your Profile before accepting bookings.", "warning")
            return redirect("/profile")
    # --------------------------------------------------------

    # Update status
    cursor.execute("""
        UPDATE bookings SET status=%s WHERE booking_id=%s AND provider_id=%s
    """, (status, booking_id, provider_id))

    # Get details and Send Notification to User
    cursor.execute("""
        SELECT b.user_id, s.skill_name 
        FROM bookings b JOIN skills s ON b.skill_id = s.skill_id 
        WHERE b.booking_id=%s
    """, (booking_id,))
    b_data = cursor.fetchone()

    if b_data:
        notif_msg = f"Your booking for '{b_data['skill_name']}' has been {status}."
        # Using dict access if dictionary=True, else tuple access
        user_to_notify = b_data['user_id'] if type(b_data) is dict else b_data[0]
        cursor.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)", (user_to_notify, notif_msg))

    db.commit()
    return redirect("/provider-bookings")


# Mark Completed Route for Providers 
@app.route("/mark-completed/<int:booking_id>", methods=["POST"])
def mark_completed(booking_id):
    if "user_id" not in session:
        return jsonify({"success": False, "message": "Please login first."})

    provider_id = session["user_id"]
    entered_otp = request.form.get("otp_code")

    # 1. डेटाबेस से सही OTP निकालें
    cursor.execute("""
        SELECT otp_code FROM bookings 
        WHERE booking_id=%s AND provider_id=%s
    """, (booking_id, provider_id))
    booking = cursor.fetchone()

    if booking:
        actual_otp = booking["otp_code"] if type(booking) is dict else booking[0]

        # 2. OTP मैच करें
        if str(actual_otp) == str(entered_otp):
            # अगर OTP सही है, तो आपका पुराना स्टेटस अपडेट और नोटिफिकेशन लॉजिक चलेगा
            cursor.execute("""
                UPDATE bookings SET status='completed' WHERE booking_id=%s AND provider_id=%s
            """, (booking_id, provider_id))

            # Send Notification to User 
            cursor.execute("""
                SELECT b.user_id, s.skill_name 
                FROM bookings b JOIN skills s ON b.skill_id = s.skill_id 
                WHERE b.booking_id=%s
            """, (booking_id,))
            b_data = cursor.fetchone()

            if b_data:
                u_id = b_data['user_id'] if type(b_data) is dict else b_data[0]
                s_name = b_data['skill_name'] if type(b_data) is dict else b_data[1]
                
                notif_msg = f"Your booking for '{s_name}' is marked as completed. Please leave a feedback!"
                cursor.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)", (u_id, notif_msg))

            db.commit()
            # सही होने पर JSON Response
            return jsonify({"success": True, "message": "OTP Verified! Service marked as completed."})
        else:
            # गलत होने पर JSON Response
            return jsonify({"success": False, "message": "Invalid OTP! Please ask the client for correct otp."})

    return jsonify({"success": False, "message": "Booking not found."})


# Give Feedback Route
@app.route("/give-feedback/<int:booking_id>", methods=["GET", "POST"])
def give_feedback(booking_id):
    if "user_id" not in session:
        return redirect("/login")

    user_id = session["user_id"]

    cursor.execute("""
        SELECT * FROM bookings WHERE booking_id=%s AND user_id=%s AND status='completed'
    """, (booking_id, user_id))
    booking = cursor.fetchone()

    if not booking:
        return redirect("/my-bookings")

    cursor.execute("SELECT feedback_id FROM feedback WHERE booking_id=%s", (booking_id,))
    existing = cursor.fetchone()

    if existing:
        return redirect("/my-bookings")

    if request.method == "POST":
        rating = float(request.form["rating"])
        comment = request.form["comment"]

        # Insert Feedback
        cursor.execute("""
            INSERT INTO feedback (booking_id, skill_id, user_id, provider_id, rating, comment)
            VALUES (%s,%s,%s,%s,%s,%s)
        """, (booking_id, booking["skill_id"], user_id, booking["provider_id"], rating, comment))

        # mark feedback given
        cursor.execute("""
            UPDATE bookings SET feedback_given = 1 WHERE booking_id=%s
        """, (booking_id,))

        #  Send Notification to Provider
        cursor.execute("SELECT skill_name FROM skills WHERE skill_id=%s", (booking["skill_id"],))
        skill = cursor.fetchone()
        if skill:
            notif_msg = f"You received a {rating}-star feedback for '{skill['skill_name']}'."
            cursor.execute("INSERT INTO notifications (user_id, message) VALUES (%s, %s)", (booking["provider_id"], notif_msg))

        db.commit()
        
        # --- JSON Response for AJAX ---
        return jsonify({"success": True, "message": "Feedback submitted successfully!"})

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
        rating = float(request.form["rating"])
        comment = request.form["comment"]

        cursor.execute("""
            UPDATE feedback
            SET rating=%s, comment=%s
            WHERE feedback_id=%s AND user_id=%s
        """, (rating, comment, feedback_id, session["user_id"]))

        db.commit()
        
        # --- JSON Response for AJAX ---
        return jsonify({"success": True, "message": "Feedback updated successfully!"})

    cursor.execute("""
        SELECT * FROM feedback
        WHERE feedback_id=%s AND user_id=%s
    """, (feedback_id, session["user_id"]))

    feedback = cursor.fetchone()

    return render_template("edit_feedback.html", feedback=feedback)


# File Upload Configuration 
UPLOAD_FOLDER = 'static/uploads/profile_pics'
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

if not os.path.exists(UPLOAD_FOLDER):
    os.makedirs(UPLOAD_FOLDER)

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


#  APP FEATURES: NOTIFICATIONS, PROFILE & PUBLIC VIEW

# 1. Global Context Processor 
@app.context_processor
def inject_global_data():
    if 'user_id' in session:
        # Get notifications
        cursor.execute("SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC LIMIT 5", (session['user_id'],))
        notifs = cursor.fetchall()
        
        # Get unread count
        cursor.execute("SELECT COUNT(*) as unread FROM notifications WHERE user_id=%s AND is_read=0", (session['user_id'],))
        unread_count = cursor.fetchone()['unread']
        
        # Ensure profile pic is in session
        cursor.execute("SELECT profile_pic FROM users WHERE user_id=%s", (session['user_id'],))
        user_data = cursor.fetchone()
        if user_data:
            session['profile_pic'] = user_data.get('profile_pic')
            
        return dict(notifications=notifs, unread_count=unread_count)
    return dict(notifications=[], unread_count=0)

# 2. Notification Routes

@app.route("/read-notification/<int:notify_id>")
def read_notification(notify_id):
    if "user_id" in session:
        cursor.execute("UPDATE notifications SET is_read=1 WHERE notify_id=%s AND user_id=%s", (notify_id, session["user_id"]))
        db.commit()
    return redirect(request.referrer or "/dashboard")

@app.route("/notifications")
def notifications_page():
    if "user_id" not in session:
        return redirect("/login")
    
    # Fetch strictly LIMIT 10 as requested
    cursor.execute("SELECT * FROM notifications WHERE user_id=%s ORDER BY created_at DESC LIMIT 10", (session['user_id'],))
    all_notifs = cursor.fetchall()
    
    cursor.execute("UPDATE notifications SET is_read=1 WHERE user_id=%s", (session["user_id"],))
    db.commit()
    
    return render_template("notifications.html", all_notifications=all_notifs)

#  Delete Notification
@app.route("/delete-notification/<int:notify_id>", methods=["POST"])
def delete_notification(notify_id):
    if "user_id" not in session:
        return redirect("/login")
    
    cursor.execute("DELETE FROM notifications WHERE notify_id=%s AND user_id=%s", (notify_id, session["user_id"]))
    db.commit()
    
    return redirect("/notifications")

# 3. My Profile Route
@app.route("/profile", methods=["GET", "POST"])
def profile():
    if "user_id" not in session:
        return redirect("/login")
    
    cursor.execute("SELECT * FROM users WHERE user_id=%s", (session["user_id"],))
    user_info = cursor.fetchone()
    
    error_message = None

    if request.method == "POST":
        name = request.form.get("name")
        email = request.form.get("email")
        phone = request.form.get("phone")
        bio = request.form.get("bio")
        profile_pic = user_info['profile_pic']

        # --- अगर फील्ड खाली है, तो उसे None (NULL) बना दो ---
        if not email or email.strip() == "":
            email = None
        if not phone or phone.strip() == "":
            phone = None
        # -------------------------------------------------------------

        # प्रोफाइल पिक्चर हैंडल करना
        file = request.files.get('profile_pic')
        if file and file.filename != '':
            filename = f"user_{session['user_id']}_{file.filename}"
            file.save(os.path.join(app.config['UPLOAD_FOLDER'], filename))
            # पुरानी फोटो डिलीट करना
            if profile_pic and os.path.exists(os.path.join(app.config['UPLOAD_FOLDER'], profile_pic)):
                try:
                    os.remove(os.path.join(app.config['UPLOAD_FOLDER'], profile_pic))
                except:
                    pass
            profile_pic = filename
            session['profile_pic'] = profile_pic

        # Database Error को पकड़ने के लिए try block
        try:
            # अब यह हमेशा ईमेल और फोन को अपडेट करेगा, चाहे वो भरे हों या खाली (NULL)
            cursor.execute("""
                UPDATE users 
                SET name=%s, email=%s, phone=%s, bio=%s, profile_pic=%s 
                WHERE user_id=%s
            """, (name, email, phone, bio, profile_pic, session["user_id"]))
                
            db.commit()
            
            session['user_name'] = name 
            
            # ---  JSON Response for AJAX ---
            return jsonify({"success": True, "message": "Profile updated successfully!"})

        except mysql.connector.Error as err:
            #  Duplicate Entry (Error Code: 1062) 
            if err.errno == 1062:
                return jsonify({"success": False, "message": "This email or phone is already in use by someone else."})
            else:
                return jsonify({"success": False, "message": "Error In Database, Please Try Again."})
    
    return render_template("profile.html", user=user_info)

# 4. Public Profile Route 
@app.route("/user/<int:user_id>")
def public_profile(user_id):
    cursor.execute("SELECT user_id, name, role, email, phone, bio, profile_pic FROM users WHERE user_id=%s", (user_id,))
    target_user = cursor.fetchone()
    
    if not target_user:
        return "User not found", 404
        
    user_skills = []
    if target_user['role'] == 'provider':
        cursor.execute("SELECT * FROM skills WHERE provider_id=%s", (user_id,))
        user_skills = cursor.fetchall()
        
    return render_template("public_profile.html", user=target_user, skills=user_skills)

#  Search Profiles
@app.route("/search-profiles")
def search_profiles():
    if "user_id" not in session:
        return redirect("/login")
    
    query = request.args.get("q", "").strip()
    results = []

    if query:
        # Search for BOTH users and providers
        cursor.execute("""
            SELECT user_id, name, role, profile_pic, bio 
            FROM users 
            WHERE role IN ('user', 'provider') AND name LIKE %s
            LIMIT 20
        """, (f"%{query}%",))
        results = cursor.fetchall()
        
    return render_template("search_profiles.html", results=results, query=query)

if __name__ == "__main__":
    app.run(debug=True)
