from flask import Flask, render_template, request, redirect, session
import mysql.connector

app = Flask(__name__)
app.secret_key = "course_system_secret"

def time_to_period(t):
    seconds = t.total_seconds()

    # 台大常見對應（你可微調）
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
        if idx == int(seconds // 3600 - 7):  # 簡化映射
            return idx

    return None
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="poray0408",
        database="course_system"
    )
db = get_db()
cursor = db.cursor(dictionary=True)

@app.route("/login")
def login():
    return render_template("login.html")

# main homepage
@app.route("/")
def index():
    return render_template("index.html")

# view all current courses
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

        JOIN Course c
            ON co.course_id=c.course_id

        JOIN Semester s
            ON co.semester_id=s.semester_id

        LEFT JOIN Instructor i
            ON co.instructor_id=i.instructor_id

        LEFT JOIN Classroom cl
            ON co.classroom_id=cl.classroom_id

        ORDER BY c.course_id
    """)

    courses = cursor.fetchall()
    db.close()
    return render_template(
        "current_courses.html",
        courses=courses
    )

@app.route("/all_courses")
def all_courses():
    db=get_db()
    cursor=db.cursor(dictionary=True)
    cursor.execute("""
        SELECT
            c.course_id,
            c.name,
            c.credits,
            c.category,
            d.dept_name

        FROM Course c

        LEFT JOIN Department d
        ON c.dept_name=d.dept_name

        ORDER BY c.course_id
    """)

    courses=cursor.fetchall()
    db.close()
    return render_template(
        "all_courses.html",
        courses=courses
    )


@app.route("/student_login", methods=["POST"])
def student_login():

    student_id = request.form["student_id"]
    password = request.form["password"]

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM Student
        WHERE student_id=%s
        AND password=%s
    """,(student_id,password))

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
    """,(session["student_id"],))

    student = cursor.fetchone()

    return render_template(
        "student_home.html",
        student=student
    )

@app.route("/logout")
def logout():
    session.clear()
    return redirect("/login")

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

    JOIN Course c
        ON co.course_id = c.course_id

    LEFT JOIN Department d
        ON c.dept_name = d.dept_name

    LEFT JOIN Course_Time ct
        ON co.time_id = ct.time_id

    LEFT JOIN Instructor i
        ON co.instructor_id = i.instructor_id

    LEFT JOIN Classroom cl
        ON co.classroom_id = cl.classroom_id

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

            conditions.append(
                "(ct.start_time < %s AND ct.end_time > %s)"
            )

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

@app.route("/enroll/<offering_id>", methods=["POST"])
def enroll(offering_id):

    student_id = session.get("student_id")
    auth_code = request.form.get(
        "auth_code",
        ""
    ).strip()
    if not student_id:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    if auth_code:

        cursor.execute("""
            SELECT *
            FROM Authorization_Code
            WHERE code=%s
            AND offering_id=%s
            AND used=FALSE
            AND expire_time > NOW()
        """, (auth_code, offering_id))

        code = cursor.fetchone()

        if not code:
            return {"message": "授權碼無效"}, 400
    # 人數
    cursor.execute("""
        SELECT capacity, current_enroll, course_id
        FROM Course_Offering
        WHERE offering_id=%s
    """, (offering_id,))
    offering = cursor.fetchone()

    if offering["current_enroll"] >= offering["capacity"]:

        if not auth_code:
            return {"message": "課程已滿，需授權碼"}, 400

        cursor.execute("""
            SELECT *
            FROM Authorization_Code
            WHERE code=%s
            AND offering_id=%s
            AND used=FALSE
            AND expire_time > NOW()
        """,(auth_code, offering_id))

        if not cursor.fetchone():
            return {"message": "授權碼無效"}, 400

    # 重複選課
    cursor.execute("""
        SELECT *
        FROM Enrollment
        WHERE student_id=%s AND offering_id=%s
    """, (student_id, offering_id))

    if cursor.fetchone():
        return {"message": "已選過此課"}, 400

    # 衝堂
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

    # 先修
    cursor.execute("""
        SELECT prereq_id
        FROM Course_Prereq
        WHERE course_id=%s
    """, (offering["course_id"],))

    prereqs = cursor.fetchall()

    for p in prereqs:
        cursor.execute("""
            SELECT *
            FROM Completed_Course
            WHERE student_id=%s AND course_id=%s
        """, (student_id, p["prereq_id"]))

        if not cursor.fetchone():
            return {"message": "未滿足先修課"}, 400

    # 選課
    cursor.execute("""
        INSERT INTO Enrollment(student_id, offering_id, status, priority)
        VALUES (%s, %s, 'enrolled', 1)
    """, (student_id, offering_id))

    # 更新人數
    cursor.execute("""
        UPDATE Course_Offering
        SET current_enroll = current_enroll + 1
        WHERE offering_id=%s
    """, (offering_id,))

    if auth_code:

        cursor.execute("""
            UPDATE Authorization_Code
            SET used=TRUE
            WHERE code=%s
        """,(auth_code,))
    db.commit()
    db.close()

    return {"message": "選課成功"}

@app.route("/schedule")
def schedule():

    PERIODS = list(range(0, 14))
    WEEKDAYS = [1, 2, 3, 4, 5]

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

        weekday = row["weekday"]
        start = row["start_time"]

        period = time_to_period(start)

        if period is None:
            continue

        if period not in timetable:
            timetable[period] = {}

        timetable[period][weekday] = row

    db.close()

    return render_template(
        "schedule.html",
        timetable=timetable,
        periods=PERIODS,
        weekdays=WEEKDAYS
    )

@app.route("/drop/<offering_id>")
def drop(offering_id):

    student_id = session.get("student_id")

    if not student_id:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # 檢查是否有選課
    cursor.execute("""
        SELECT *
        FROM Enrollment
        WHERE student_id=%s AND offering_id=%s
    """, (student_id, offering_id))

    enroll = cursor.fetchone()

    if not enroll:
        return {"message": "你沒有選這門課"}, 400

    # 刪除選課
    cursor.execute("""
        DELETE FROM Enrollment
        WHERE student_id=%s AND offering_id=%s
    """, (student_id, offering_id))

    # 更新人數
    cursor.execute("""
        UPDATE Course_Offering
        SET current_enroll = current_enroll - 1
        WHERE offering_id=%s AND current_enroll > 0
    """, (offering_id,))

    db.commit()
    db.close()

    return redirect("/schedule")

if __name__ == "__main__":
    app.run(debug=True)