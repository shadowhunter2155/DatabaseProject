from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector

app = Flask(__name__)
app.secret_key = "course_system_secret"


# ======================
# DB
# ======================
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="course_admin",
        password="mypassword",
        database="course_system"
    )


db = get_db()
cursor = db.cursor(dictionary=True)


# ======================
# REGISTER
# ======================
@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user_id = request.form["user_id"]
        password = request.form["password"]
        role = request.form["role"]

        db = get_db()
        cursor = db.cursor(dictionary=True)

        if role == "student":
            cursor.execute("""
                INSERT INTO Student(student_id, password)
                VALUES (%s, %s)
            """, (user_id, password))

        elif role == "teacher":
            cursor.execute("""
                INSERT INTO Instructor(instructor_id, password)
                VALUES (%s, %s)
            """, (user_id, password))

        db.commit()
        db.close()

        return redirect("/login")

    return render_template("register.html")


# ======================
# LOGIN
# ======================
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form.get("role")
        password = request.form.get("password")

        db = get_db()
        cursor = db.cursor(dictionary=True)

        if role == "student":
            student_id = request.form.get("student_id")
            cursor.execute("""
                SELECT * FROM Student
                WHERE student_id=%s AND password=%s
            """, (student_id, password))

            student = cursor.fetchone()

            if student:
                session["student_id"] = student_id
                return redirect(url_for("student_home"))

        elif role == "teacher":
            teacher_id = request.form.get("teacher_id")
            cursor.execute("""
                SELECT * FROM Instructor
                WHERE instructor_id=%s AND password=%s
            """, (teacher_id, password))

            teacher = cursor.fetchone()

            if teacher:
                session["teacher_id"] = teacher_id
                return redirect(url_for("teacher_home"))

        db.close()
        return "帳號或密碼錯誤"

    return render_template("login.html")


# ======================
# HOME
# ======================
@app.route("/")
def index():
    return render_template("index.html")


@app.route("/student_home")
def student_home():
    if "student_id" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM Student
        WHERE student_id=%s
    """, (session["student_id"],))

    student = cursor.fetchone()
    db.close()

    return render_template("student_home.html", student=student)


@app.route("/teacher_home")
def teacher_home():
    if "teacher_id" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM Instructor
        WHERE instructor_id=%s
    """, (session["teacher_id"],))

    teacher = cursor.fetchone()
    db.close()

    return render_template("teacher_home.html", teacher=teacher)


# ======================
# TEACHER BASIC FEATURE
# ======================
@app.route("/teacher/add_course", methods=["GET", "POST"])
def teacher_add_course():
    if "teacher_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        course_id = request.form["course_id"]
        name = request.form["name"]
        credits = request.form["credits"]
        dept_name = request.form["dept_name"]

        db = get_db()
        cursor = db.cursor(dictionary=True)

        cursor.execute("""
            INSERT INTO Course(course_id, name, credits, dept_name)
            VALUES (%s, %s, %s, %s)
        """, (course_id, name, credits, dept_name))

        db.commit()
        db.close()

        return redirect("/all_courses")

    return render_template("teacher_add_course.html")


# ======================
# EXISTING ROUTES (完全不動)
# ======================
@app.route("/all_courses")
def all_courses():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            c.course_id,
            c.name,
            c.credits,
            c.category,
            d.dept_name
        FROM Course c
        LEFT JOIN Department d ON c.dept_name=d.dept_name
    """)

    courses = cursor.fetchall()
    db.close()

    return render_template("all_courses.html", courses=courses)


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


if __name__ == "__main__":
    app.run(debug=True)
