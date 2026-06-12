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

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT 
            co.offering_id,
            c.name,
            c.credits,
            i.name AS instructor,
            cl.building,
            cl.room_number,
            co.current_enroll,
            co.capacity
        FROM Course_Offering co
        JOIN Course c ON co.course_id = c.course_id
        LEFT JOIN Instructor i ON co.instructor_id = i.instructor_id
        LEFT JOIN Classroom cl ON co.classroom_id = cl.classroom_id
    """)

    courses = cursor.fetchall()

    return render_template("course_search.html", courses=courses)

@app.route("/enroll/<offering_id>")
def enroll(offering_id):

    student_id = session.get("student_id")
    if not student_id:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    # 人數
    cursor.execute("""
        SELECT capacity, current_enroll, course_id
        FROM Course_Offering
        WHERE offering_id=%s
    """, (offering_id,))
    offering = cursor.fetchone()

    if offering["current_enroll"] >= offering["capacity"]:
        return "課程已滿"

    # 重複選課
    cursor.execute("""
        SELECT *
        FROM Enrollment
        WHERE student_id=%s AND offering_id=%s
    """, (student_id, offering_id))

    if cursor.fetchone():
        return "已選過此課"

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
                return "時間衝堂"

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
            return "未滿足先修課"

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

    db.commit()
    db.close()

    return "選課成功"

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
    schedule_data = cursor.fetchall()

    db.close()

    return render_template("schedule.html", schedule=schedule_data)

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
        return "你沒有選這門課"

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