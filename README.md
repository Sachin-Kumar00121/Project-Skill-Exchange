# ⚡ SkillX - Local Service Marketplace

SkillX is a professional web application designed to connect local service providers (like mechanics, plumbers, electricians) with users in need of their expertise. It streamlines the process of booking, managing, and reviewing local services.

## 🚀 Key Features

### For Users 👤
* **Browse Skills:** Explore various categories of local services.
* **Instant Booking:** Request a service by selecting a date, time, and adding remarks.
* **Track Status:** Monitor your bookings (Pending, Accepted, or Completed).
* **Rate & Review:** Provide feedback and star ratings after service completion.

### For Service Providers 🛠
* **Profile Management:** List and manage the skills you offer with pricing.
* **Booking Control:** Accept or decline service requests from users.
* **Job Completion:** Mark tasks as finished to build a professional history.

### For Admin 👨‍💻
* **Central Dashboard:** View platform statistics including total users and bookings.
* **Moderation:** Ability to block or delete users and providers violating policies.
* **Content Management:** Oversee all skills, reviews, and transaction history.

## 💻 Tech Stack
* **Frontend:** HTML5, CSS3, JavaScript (Vanilla).
* **Backend:** Python 3, Flask Framework.
* **Database:** MySQL.
* **Security:** Werkzeug password hashing for user protection.

## 🛠️ Local Installation & Setup

1. **Clone the Project:**
   ```bash
   git clone [https://github.com/Sachin-Kumar00121/Project-Skill-Exchange.git](https://github.com/Sachin-Kumar00121/Project-Skill-Exchange.git)
   cd Project-Skill-Exchange


2. **Create & Activate Virtual Environment**
    * **Environment बनाना**
     python -m venv venv

     * **Windows पर चालू करना**
       venv\Scripts\activate

3. **Install Requirements**
     pip install -r requirements.txt

4. **Configure Database (.env)**
  * अपने प्रोजेक्ट फोल्डर में एक नई फाइल बनाएँ जिसका नाम .env रखें और उसमें अपनी MySQL डिटेल्स डालें:

   DB_HOST=localhost
   DB_USER=root
   DB_PASS=your_mysql_password
   DB_NAME=your_database_name
   DB_PORT=your db port

5. **Run the Application**
   * python app.py

  Once running, open your browser and go to: http://127.0.0.1:5000/

  Developed as a 6th Semester CSE Polytechnic Project.