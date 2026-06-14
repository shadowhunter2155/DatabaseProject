from flask import Flask, render_template, request, redirect, session
import mysql.connector

app = Flask(__name__)
app.secret_key = "course_system_secret"


# =========================
# DB
# =========================
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="poray0408",
        database="course_system"
    )


# =========================
# TIME UTILS
# =========================
def time_to_period(t):
    seconds = t.total_seconds()

    mapping = [
        (0,  "07:10"),
        (1,  "08:10"),
        (2,  "09:10"),
        (3,  "10:20"),
        (4,  "11:20"),
        (5,  "12:20"),
        (6,  "13:20"),
        (7,  "14:20"),
        (8,  "15:30"),
        (9,  "16:30"),
        (10, "17:30"),
        (11, "18:25"),
        (12, "19:20"),
        (13, "20:15"),
    ]

    for idx, _ in mapping:
        if idx == int(seconds // 3600 - 7):
            return idx

    return None


# =========================
# GLOBAL DB (你原本的寫法保留)
# =========================
db = get_db()
cursor = db.cursor(dictionary=True)


# =========================
# AUTH
# =========================
@app.route("/login")
def login():
    return render_template("login.html")


@app.route("/")
def index():
    return render_template("index.html")


@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")


# =========================
# COURSES
# =========================
@app.route("/current_courses")
def current_courses():
    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            co.offering_id,
            c.course_id,
            c.name,
            c.credits,
            i.name AS instructor,
            cl.building,
            cl.room_number,
            co.current_enroll,
            co.capacity,
            s.year,
            s.term
        FROM Course_Offering co
        JOIN Course c ON co.course_id=c.course_id
        JOIN Semester s ON co.semester_id=s.semester_id
        LEFT JOIN Instructor i ON co.instructor_id=i.instructor_id
        LEFT JOIN Classroom cl ON co.classroom_id=cl.classroom_id
        ORDER BY c.course_id
    """)

    courses = cursor.fetchall()
    db.close()

    return render_template("current_courses.html", courses=courses)


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
        ORDER BY c.course_id
    """)

    courses = cursor.fetchall()
    db.close()

    return render_template("all_courses.html", courses=courses)


# =========================
# STUDENT AUTH
# =========================
@app.route("/student_login", methods=["POST"])
def student_login():
    student_id = request.form["student_id"]
    password = request.form["password"]

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM Student
        WHERE student_id=%s AND password=%s
    """, (student_id, password))

    student = cursor.fetchone()

    if student:
        session["student_id"] = student_id
        return redirect("/student_home")

    return "帳號或密碼錯誤"


@app.route("/student_home")
def student_home():
    if "student_id" not in session:
        return redirect("/login")

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM Student
        WHERE student_id=%s
    """, (session["student_id"],))

    student = cursor.fetchone()

    return render_template("student_home.html", student=student)


# =========================
# COURSE SEARCH
# =========================
@app.route("/course_search")
def course_search():
    course_id = request.args.get("course_id", "")
    course_name = request.args.get("course_name", "")
    dept_name = request.args.get("dept_name", "")
    weekday = request.args.get("weekday", "")
    instructor = request.args.get("instructor", "")
    periods = request.args.getlist("period")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT DISTINCT dept_name
        FROM Department
        WHERE dept_name IS NOT NULL
    """)

    departments = cursor.fetchall()

    sql = """
    SELECT
        co.offering_id,
        c.course_id,
        c.name,
        c.credits,
        d.dept_name,
        ct.weekday,
        ct.start_time,
        ct.end_time,
        i.name AS instructor,
        cl.building,
        cl.room_number,
        co.current_enroll,
        co.capacity
    FROM Course_Offering co
    JOIN Course c ON co.course_id = c.course_id
    LEFT JOIN Department d ON c.dept_name = d.dept_name
    LEFT JOIN Course_Time ct ON co.time_id = ct.time_id
    LEFT JOIN Instructor i ON co.instructor_id = i.instructor_id
    LEFT JOIN Classroom cl ON co.classroom_id = cl.classroom_id
    WHERE 1=1
    """

    params = []

    if course_id:
        sql += " AND c.course_id = %s"
        params.append(course_id)

    if course_name:
        sql += " AND c.name LIKE %s"
        params.append(f"%{course_name}%")

    if dept_name:
        sql += " AND d.dept_name = %s"
        params.append(dept_name)

    if weekday:
        sql += " AND ct.weekday = %s"
        params.append(weekday)

    if periods:
        period_map = {
            "0": ("07:10:00", "08:00:00"),
            "1": ("08:10:00", "09:00:00"),
            "2": ("09:10:00", "10:00:00"),
            "3": ("10:20:00", "11:10:00"),
            "4": ("11:20:00", "12:10:00"),
            "5": ("12:20:00", "13:10:00"),
            "6": ("13:20:00", "14:10:00"),
            "7": ("14:20:00", "15:10:00"),
            "8": ("15:30:00", "16:20:00"),
            "9": ("16:30:00", "17:20:00"),
            "10": ("17:30:00", "18:20:00"),
            "11": ("18:25:00", "19:15:00"),
            "12": ("19:20:00", "20:10:00"),
            "13": ("20:15:00", "21:05:00")
        }

        conditions = []

        for p in periods:
            start_time, end_time = period_map[p]
            conditions.append("(ct.start_time < %s AND ct.end_time > %s)")
            params.append(end_time)
            params.append(start_time)

        sql += " AND (" + " OR ".join(conditions) + ")"

    if instructor:
        sql += " AND i.name LIKE %s"
        params.append(f"%{instructor}%")

    cursor.execute(sql, params)
    courses = cursor.fetchall()
    db.close()

    return render_template(
        "course_search.html",
        courses=courses,
        departments=departments,
        course_id=course_id,
        course_name=course_name,
        dept_name=dept_name,
        weekday=weekday,
        instructor=instructor,
        periods=periods
    )


# =========================
# ENROLL / DROP / SCHEDULE
# =========================
@app.route("/enroll/<offering_id>", methods=["POST"])
def enroll(offering_id):
    student_id = session.get("student_id")
    auth_code = request.form.get("auth_code", "").strip()

    if not student_id:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # =====（原本邏輯完全保留）=====
    if auth_code:
        cursor.execute("""
            SELECT *
            FROM Authorization_Code
            WHERE code=%s
            AND offering_id=%s
            AND used=FALSE
            AND expire_time > NOW()
        """, (auth_code, offering_id))

        if not cursor.fetchone():
            return {"message": "授權碼無效"}, 400

    cursor.execute("""
        SELECT capacity, current_enroll, course_id
        FROM Course_Offering
        WHERE offering_id=%s
    """, (offering_id,))

    offering = cursor.fetchone()

    if offering["current_enroll"] >= offering["capacity"] and not auth_code:
        return {"message": "課程已滿，需授權碼"}, 400

    cursor.execute("""
        SELECT *
        FROM Enrollment
        WHERE student_id=%s AND offering_id=%s
    """, (student_id, offering_id))

    if cursor.fetchone():
        return {"message": "已選過此課"}, 400

    # ===== 衝堂 =====
    cursor.execute("""
        SELECT ct.*
        FROM Enrollment e
        JOIN Course_Offering co ON e.offering_id = co.offering_id
        JOIN Course_Time ct ON co.time_id = ct.time_id
        WHERE e.student_id=%s
    """, (student_id,))

    my_times = cursor.fetchall()

    cursor.execute("""
        SELECT ct.*
        FROM Course_Offering co
        JOIN Course_Time ct ON co.time_id = ct.time_id
        WHERE co.offering_id=%s
    """, (offering_id,))

    new_time = cursor.fetchone()

    for t in my_times:
        if t["weekday"] == new_time["weekday"]:
            if not (new_time["end_time"] <= t["start_time"] or new_time["start_time"] >= t["end_time"]):
                return {"message": "時間衝堂"}, 400

    # ===== 選課 =====
    cursor.execute("""
        INSERT INTO Enrollment(student_id, offering_id, status, priority)
        VALUES (%s, %s, 'enrolled', 1)
    """, (student_id, offering_id))

    cursor.execute("""
        UPDATE Course_Offering
        SET current_enroll = current_enroll + 1
        WHERE offering_id=%s
    """, (offering_id,))

    db.commit()
    db.close()

    return {"message": "選課成功"}


@app.route("/drop/<offering_id>")
def drop(offering_id):
    student_id = session.get("student_id")

    if not student_id:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        DELETE FROM Enrollment
        WHERE student_id=%s AND offering_id=%s
    """, (student_id, offering_id))

    cursor.execute("""
        UPDATE Course_Offering
        SET current_enroll = current_enroll - 1
        WHERE offering_id=%s AND current_enroll > 0
    """, (offering_id,))

    db.commit()
    db.close()

    return redirect("/schedule")


@app.route("/schedule")
def schedule():
    student_id = session.get("student_id")

    if not student_id:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
    SELECT 
        co.offering_id,
        c.name AS course_name,
        ct.weekday,
        ct.start_time,
        ct.end_time,
        cl.building,
        cl.room_number,
        i.name AS instructor_name
    FROM Enrollment e
    JOIN Course_Offering co ON e.offering_id = co.offering_id
    JOIN Course c ON co.course_id = c.course_id
    JOIN Course_Time ct ON co.time_id = ct.time_id
    LEFT JOIN Classroom cl ON co.classroom_id = cl.classroom_id
    LEFT JOIN Instructor i ON co.instructor_id = i.instructor_id
    WHERE e.student_id = %s
    """, (student_id,))

    rows = cursor.fetchall()

    timetable = {}

    for row in rows:
        period = time_to_period(row["start_time"])
        if period is None:
            continue

        timetable.setdefault(period, {})
        timetable[period][row["weekday"]] = row

    db.close()

    return render_template(
        "schedule.html",
        timetable=timetable,
        periods=list(range(14)),
        weekdays=[1,2,3,4,5]
    )


# =========================
# =========================
# TEACHER FEATURE (新增在最底下)
# =========================
# =========================

@app.route("/teacher_login", methods=["GET", "POST"])
def teacher_login():
    if request.method == "GET":
        return render_template("teacher_login.html")

    teacher_id = request.form["teacher_id"]
    password = request.form["password"]

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM Instructor
        WHERE instructor_id=%s AND password=%s
    """, (teacher_id, password))

    teacher = cursor.fetchone()
    db.close()

    if teacher:
        session["teacher_id"] = teacher_id
        return redirect("/teacher_home")

    return "登入失敗"


@app.route("/teacher_home")
def teacher_home():
    if "teacher_id" not in session:
        return redirect("/teacher_login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM Instructor
        WHERE instructor_id=%s
    """, (session["teacher_id"],))

    teacher = cursor.fetchone()
    db.close()

    return render_template("teacher_home.html", teacher=teacher)


@app.route("/teacher_courses")
def teacher_courses():
    if "teacher_id" not in session:
        return redirect("/teacher_login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            co.offering_id,
            c.name,
            co.current_enroll,
            co.capacity,
            ct.weekday,
            ct.start_time,
            ct.end_time
        FROM Course_Offering co
        JOIN Course c ON co.course_id=c.course_id
        JOIN Course_Time ct ON co.time_id=ct.time_id
        WHERE co.instructor_id=%s
    """, (session["teacher_id"],))

    courses = cursor.fetchall()
    db.close()

    return render_template("teacher_courses.html", courses=courses)


# =========================
if __name__ == "__main__":
    app.run(debug=True)
