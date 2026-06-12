from flask import Flask, render_template, request, redirect, session
import mysql.connector

app = Flask(__name__)
app.secret_key = "course_system_secret"


def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="poray0408",
        database="course_system"
    )


# =====================
# HOME / LOGIN
# =====================

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/login")
def login():
    return render_template("login.html")


# =====================
# STUDENT (不動)
# =====================

@app.route("/student_home")
def student_home():
    if "student_id" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("SELECT * FROM Student WHERE student_id=%s",
                   (session["student_id"],))

    student = cursor.fetchone()
    db.close()

    return render_template("student_home.html", student=student)


# =====================
# TEACHER AUTH FIX
# =====================

def require_teacher():
    return "instructor_id" in session


@app.route("/teacher_login")
def teacher_login_page():
    return render_template("teacher_login.html")


@app.route("/teacher_login", methods=["POST"])
def teacher_login():

    instructor_id = request.form["instructor_id"]
    password = request.form["password"]

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM Instructor
        WHERE instructor_id=%s AND password=%s
    """, (instructor_id, password))

    teacher = cursor.fetchone()
    db.close()

    if teacher:
        session["instructor_id"] = instructor_id
        return redirect("/teacher_home")

    return "老師帳號或密碼錯誤"


@app.route("/teacher_home")
def teacher_home():

    if not require_teacher():
        return redirect("/teacher_login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM Instructor
        WHERE instructor_id=%s
    """, (session["instructor_id"],))

    teacher = cursor.fetchone()
    db.close()

    return render_template("teacher_home.html", teacher=teacher)


# =====================
# COURSE (FIXED schema)
# =====================

@app.route("/teacher/course/add", methods=["POST"])
def teacher_add_course():

    if not require_teacher():
        return redirect("/login")

    course_id = request.form["course_id"]
    name = request.form["name"]
    credits = request.form["credits"]

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO Course(course_id, name, credits)
        VALUES (%s, %s, %s)
    """, (course_id, name, credits))

    db.commit()
    db.close()

    return "課程新增成功"


@app.route("/teacher/course/edit/<course_id>", methods=["POST"])
def teacher_edit_course(course_id):

    if not require_teacher():
        return redirect("/login")

    name = request.form["name"]
    credits = request.form["credits"]

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        UPDATE Course
        SET name=%s, credits=%s
        WHERE course_id=%s
    """, (name, credits, course_id))

    db.commit()
    db.close()

    return "課程修改成功"


# =====================
# OFFERING
# =====================

@app.route("/teacher/offering/add", methods=["POST"])
def teacher_add_offering():

    if not require_teacher():
        return redirect("/login")

    course_id = request.form["course_id"]
    semester_id = request.form["semester_id"]
    instructor_id = session["instructor_id"]
    classroom_id = request.form["classroom_id"]
    time_id = request.form["time_id"]
    capacity = request.form["capacity"]

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM Course_Offering
        WHERE (instructor_id=%s OR classroom_id=%s)
        AND time_id=%s
    """, (instructor_id, classroom_id, time_id))

    if cursor.fetchone():
        db.close()
        return "時間衝突"

    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO Course_Offering
        (course_id, semester_id, instructor_id, classroom_id, time_id, capacity, current_enroll)
        VALUES (%s,%s,%s,%s,%s,%s,0)
    """, (course_id, semester_id, instructor_id, classroom_id, time_id, capacity))

    db.commit()
    db.close()

    return "開課成功"


@app.route("/teacher/offering/edit/<offering_id>", methods=["POST"])
def teacher_edit_offering(offering_id):

    if not require_teacher():
        return redirect("/login")

    classroom_id = request.form["classroom_id"]
    time_id = request.form["time_id"]
    capacity = request.form["capacity"]
    instructor_id = session["instructor_id"]

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM Course_Offering
        WHERE offering_id != %s
        AND (instructor_id=%s OR classroom_id=%s)
        AND time_id=%s
    """, (offering_id, instructor_id, classroom_id, time_id))

    if cursor.fetchone():
        db.close()
        return "時間衝突"

    cursor = db.cursor()

    cursor.execute("""
        UPDATE Course_Offering
        SET classroom_id=%s,
            time_id=%s,
            capacity=%s
        WHERE offering_id=%s
    """, (classroom_id, time_id, capacity, offering_id))

    db.commit()
    db.close()

    return "修改成功"


@app.route("/teacher/offering/delete/<offering_id>")
def teacher_delete_offering(offering_id):

    if not require_teacher():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor()

    cursor.execute("""
        DELETE FROM Course_Offering
        WHERE offering_id=%s
    """, (offering_id,))

    db.commit()
    db.close()

    return "刪除成功"


# =====================
# TEACHER VIEW (改成 HTML 方便 debug)
# =====================

@app.route("/teacher/schedule")
def teacher_schedule():

    if not require_teacher():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM Course_Offering
    """)

    data = cursor.fetchall()
    db.close()

    return render_template("debug.html", data=data)


@app.route("/teacher/courses")
def teacher_courses():

    if not require_teacher():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM Course_Offering
    """)

    data = cursor.fetchall()
    db.close()

    return render_template("debug.html", data=data)


# =====================
# DASHBOARD
# =====================

@app.route("/teacher_dashboard")
def teacher_dashboard():

    if not require_teacher():
        return redirect("/teacher_login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT * FROM Instructor
        WHERE instructor_id=%s
    """, (session["instructor_id"],))

    teacher = cursor.fetchone()
    db.close()

    return render_template("teacher_dashboard.html", teacher=teacher)


if __name__ == "__main__":
    app.run(debug=True)
