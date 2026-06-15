from flask import Flask, render_template, request, redirect, session, url_for
import mysql.connector

app = Flask(__name__)
app.secret_key = "course_system_secret"

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        user_id = request.form["user_id"]
        password = request.form["password"]
        role = request.form["role"]  # 'student' 或 'teacher'

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

    # GET 時顯示註冊表單
    return render_template("register.html")


def get_course_periods(start_time, end_time):
    """
    輸入開始與結束時間(timedelta或string)，計算它橫跨了哪些節數
    例如：09:10 到 11:10 應該回傳 [2, 3]
    """
    # 將時間統一轉為秒數
    start_sec = start_time.total_seconds() if hasattr(start_time, 'total_seconds') else start_time.seconds
    end_sec = end_time.total_seconds() if hasattr(end_time, 'total_seconds') else end_time.seconds
    # 台大節數對應的「開始時間」與「結束時間」秒數
    # 格式：(節數, 開始秒數, 結束秒數)
    # 08:10 = 8*3600 + 10*60 = 29400 秒
    period_defs = [
        (0,  7*3600 + 10*60,  8*3600),
        (1,  8*3600 + 10*60,  9*3600),
        (2,  9*3600 + 10*60, 10*3600 + 10*60), # 09:10 ~ 10:10 (或 10:00)
        (3, 10*3600 + 20*60, 11*3600 + 20*60), # 10:20 ~ 11:20
        (4, 11*3600 + 20*60, 12*3600 + 20*60),
        (5, 12*3600 + 20*60, 13*3600 + 20*60),
        (6, 13*3600 + 20*60, 14*3600 + 20*60),
        (7, 14*3600 + 20*60, 15*3600 + 20*60),
        (8, 15*3600 + 30*60, 16*3600 + 30*60),
        (9, 16*3600 + 30*60, 17*3600 + 30*60),
        (10, 17*3600 + 30*60, 18*3600 + 30*60),
        (11, 18*3600 + 25*60, 19*3600 + 25*60),
        (12, 19*3600 + 20*60, 20*3600 + 20*60),
        (13, 20*3600 + 15*60, 21*3600 + 15*60),
    ]

    matched_periods = []
    for p, p_start, p_end in period_defs:
        # 只要課程時間與該節數時間有重疊，就加進去
        # 條件：課程開始時間 < 節數結束時間 AND 課程結束時間 > 節數開始時間
        if start_sec < p_end and end_sec > p_start:
            matched_periods.append(p)
            
    return matched_periods
# 在 app.py 中大約第 50 行左右
def get_db():
    return mysql.connector.connect(
        host="localhost",
        user="root",          # 👈 改成你常用的帳號（例如 root）
        password="poray0408",   # 👈 改成你電腦真正的資料庫密碼
        database="course_system2"
    )
db = get_db()
cursor = db.cursor(dictionary=True)



@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        role = request.form.get("role")
        password = request.form.get("password")

        db = get_db()
        cursor = db.cursor(dictionary=True)

        if role == "student":
            student_id = request.form.get("student_id")
            cursor.execute("SELECT * FROM Student WHERE student_id=%s AND password=%s",
                           (student_id, password))
            student = cursor.fetchone()
            if student:
                session["student_id"] = student_id
                return redirect(url_for("student_home"))
            else:
                return "帳號或密碼錯誤"

        elif role == "teacher":
            teacher_id = request.form.get("teacher_id")
            cursor.execute("SELECT * FROM Instructor WHERE instructor_id=%s AND password=%s",
                           (teacher_id, password))
            teacher = cursor.fetchone()
            if teacher:
                session["teacher_id"] = teacher_id
                return redirect(url_for("teacher_home"))
            else:
                return "帳號或密碼錯誤"

        db.close()

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

            i.instructor_id AS instructor,

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

    db = get_db()
    cursor = db.cursor(dictionary=True)
    
    cursor.execute("""
        SELECT * FROM Student WHERE student_id=%s AND password=%s
    """, (student_id, password))
    student = cursor.fetchone()
    
    db.close() # 務必記得關閉連線

    if student:
        session["student_id"] = student_id
        return redirect("/student_home")
    return "帳號或密碼錯誤"

@app.route("/student_home")
def student_home():
    if "student_id" not in session:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT * FROM Student WHERE student_id=%s", (session["student_id"],))
    student = cursor.fetchone()
    db.close()

    return render_template("student_home.html", student=student)

@app.route("/teacher_home")
def teacher_home():

    if "teacher_id" not in session:
        return redirect("/login")

    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM Instructor
        WHERE instructor_id=%s
    """, (session["teacher_id"],))

    teacher = cursor.fetchone()

    return render_template(
        "teacher_home.html",
        teacher=teacher
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
    # 修改後的 Base SQL
    sql = """
    SELECT
        co.offering_id,
        c.course_id,
        c.name,
        c.credits,
        d.dept_name,
        i.name AS instructor,
        cl.building,
        cl.room_number,
        co.current_enroll,
        co.capacity,
        -- ⭐ 關鍵：把不同的星期和時間黏在一起。例如："1:10:20:00-12:10:00,5:12:20:00-14:10:00"
        GROUP_CONCAT(CONCAT(ct.weekday, ':', ct.start_time, '-', ct.end_time) ORDER BY ct.weekday) AS all_times

    FROM Course_Offering co
    JOIN Course c 
        ON co.course_id = c.course_id
    LEFT JOIN Department d 
        ON c.dept_name = d.dept_name
    LEFT JOIN Offering_Time ot 
        ON co.offering_id = ot.offering_id  -- 透過中介表 JOIN
    LEFT JOIN Course_Time ct 
        ON ot.time_id = ct.time_id
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


    sql += " GROUP BY co.offering_id ORDER BY c.course_id"
    cursor.execute(sql, params)

    courses = cursor.fetchall()
    # 在 cursor.fetchall() 後面加上這段轉換邏輯
    
    
    weekday_map = {1: "週一", 2: "週二", 3: "週三", 4: "週四", 5: "週五", 6: "週六", 7: "週日"}
    
    for course in courses:
        if course["all_times"]:
            time_strings = []
            # 依逗號拆開多個時段
            slots = course["all_times"].split(",") 
            for slot in slots:
                # 拆出 星期、開始時間、結束時間
                w_day, time_range = slot.split(":", 1)
                start, end = time_range.split("-")
                
                # 格式化時間 (只取到分，去掉秒，例如 10:20:00 -> 10:20)
                start_hm = ":".join(start.split(":")[:2])
                end_hm = ":".join(end.split(":")[:2])
                
                time_strings.append(f"{weekday_map[int(w_day)]} {start_hm}~{end_hm}")
            
            # 把格式化後的結果用空格或逗號串起來，存回一個新欄位
            course["formatted_time"] = " | ".join(time_strings)
        else:
            course["formatted_time"] = "未排定時間"

    
    # 後續一樣 return render_template(...)
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
    auth_code = request.form.get("auth_code", "").strip()
    
    if not student_id:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    try:
        # 1. 檢查是否重複選課
        cursor.execute("SELECT * FROM Enrollment WHERE student_id=%s AND offering_id=%s", (student_id, offering_id))
        if cursor.fetchone():
            return {"message": "已選過此課"}, 400

        # 2. 獲取課程人數與資訊 (加上 FOR UPDATE 鎖定，防止並發超選)
        cursor.execute("""
            SELECT capacity, current_enroll, course_id 
            FROM Course_Offering 
            WHERE offering_id=%s FOR UPDATE
        """, (offering_id,))
        offering = cursor.fetchone()
        
        if not offering:
            return {"message": "找不到該課程開課紀錄"}, 404

        # 3. 授權碼與人數檢查
        if offering["current_enroll"] >= offering["capacity"]:
            if not auth_code:
                return {"message": "課程已滿，需授權碼"}, 400
            
            # 有給授權碼，驗證其有效性
            cursor.execute("""
                SELECT * FROM Authorization_Code 
                WHERE code=%s AND offering_id=%s AND used=FALSE AND expire_time > NOW()
            """, (auth_code, offering_id))
            if not cursor.fetchone():
                return {"message": "授權碼無效或已過期"}, 400
        elif auth_code:
            # 沒滿但使用者自願填授權碼，仍須驗證
            cursor.execute("""
                SELECT * FROM Authorization_Code 
                WHERE code=%s AND offering_id=%s AND used=FALSE AND expire_time > NOW()
            """, (auth_code, offering_id))
            if not cursor.fetchone():
                return {"message": "授權碼無效或已過期"}, 400

        # 1. 撈出學生目前已選的所有課的所有時段
        cursor.execute("""
            SELECT ct.* FROM Enrollment e
            JOIN Offering_Time ot ON e.offering_id = ot.offering_id
            JOIN Course_Time ct ON ot.time_id = ct.time_id
            WHERE e.student_id=%s
        """, (student_id,))
        my_times = cursor.fetchall()

        # 2. 撈出該加選新課的所有時段
        cursor.execute("""
            SELECT ct.* FROM Offering_Time ot
            JOIN Course_Time ct ON ot.time_id = ct.time_id
            WHERE ot.offering_id=%s
        """, (offering_id,))
        new_times = cursor.fetchall()

        # 3. 進行雙層迴圈交叉比對 (邏輯不變，但資料變精準了！)
        for new_t in new_times:
            for my_t in my_times:
                if new_t["weekday"] == my_t["weekday"]:
                    if not (new_t["end_time"] <= my_t["start_time"] or new_t["start_time"] >= my_t["end_time"]):
                        return {"message": "時間衝堂"}, 400

        # 5. 先修課檢查
        cursor.execute("SELECT prereq_id FROM Course_Prereq WHERE course_id=%s", (offering["course_id"],))
        prereqs = cursor.fetchall()
        for p in prereqs:
            cursor.execute("""
                SELECT * FROM Completed_Course WHERE student_id=%s AND course_id=%s
            """, (student_id, p["prereq_id"]))
            if not cursor.fetchone():
                return {"message": "未滿足先修課條件"}, 400

        # 6. 執行選課動作
        cursor.execute("""
            INSERT INTO Enrollment(student_id, offering_id, status, priority)
            VALUES (%s, %s, 'enrolled', 1)
        """, (student_id, offering_id))

        cursor.execute("""
            UPDATE Course_Offering SET current_enroll = current_enroll + 1 WHERE offering_id=%s
        """, (offering_id,))

        if auth_code:
            cursor.execute("UPDATE Authorization_Code SET used=TRUE WHERE code=%s", (auth_code,))
        
        db.commit()
        return {"message": "選課成功"}
        
    except Exception as e:
        db.rollback()
        return {"message": f"系統錯誤: {str(e)}"}, 500
    finally:
        db.close()

@app.route("/schedule")
def schedule():

    PERIODS = list(range(0, 14))
    WEEKDAYS = [1, 2, 3, 4, 5]

    student_id = session.get("student_id")

    if not student_id:
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)
    # ==================== 【新增：點子 A 統計邏輯】 ====================
    # 運用了 COUNT(), SUM() 聚合函數以及 GROUP BY 分組
    summary_sql = """
    SELECT 
        COUNT(e.offering_id) AS total_courses,
        SUM(c.credits) AS total_credits
    FROM Enrollment e
    JOIN Course_Offering co ON e.offering_id = co.offering_id
    JOIN Course c ON co.course_id = c.course_id
    WHERE e.student_id = %s AND e.status = 'enrolled'
    GROUP BY e.student_id
    """
    cursor.execute(summary_sql, (student_id,))
    summary_result = cursor.fetchone()
    
    # 如果學生一堂課都還沒選，fetch 出來會是 None，給予預設值 0
    if summary_result:
        total_courses = summary_result["total_courses"]
        total_credits = summary_result["total_credits"]
    else:
        total_courses = 0
        total_credits = 0
    # ====================================================================
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
    JOIN Offering_Time ot ON co.offering_id = ot.offering_id  -- 新增這行
    JOIN Course_Time ct ON ot.time_id = ct.time_id            -- 修改這行
    LEFT JOIN Classroom cl ON co.classroom_id = cl.classroom_id
    LEFT JOIN Instructor i ON co.instructor_id = i.instructor_id
    WHERE e.student_id = %s
    """, (student_id,))

    rows = cursor.fetchall()

    # 修改後的新 /schedule 邏輯片段
    timetable = {}
    for row in rows:
        weekday = row["weekday"]
        start = row["start_time"]
        end = row["end_time"]

        # 取得這堂課涵蓋的所有節數，例如 [2, 3]
        periods = get_course_periods(start, end)

        for period in periods:
            if period not in timetable:
                timetable[period] = {}
            # 讓第 2 節和第 3 節的格子都指向這堂課
            timetable[period][weekday] = row

    db.close()

    return render_template(
        "schedule.html",
        timetable=timetable,
        periods=PERIODS,
        weekdays=WEEKDAYS,
        total_courses=total_courses,     # 👈 傳給前端
        total_credits=total_credits       # 👈 傳給前端
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

@app.route("/student_enroll")
def student_enroll_page():
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT offering_id, course_id FROM Course_Offering")
    offerings = cursor.fetchall()
    db.close()
    return render_template("student_enroll.html", offerings=offerings)

@app.route("/student/enroll/<offering_id>", methods=["POST"])
def student_enroll(offering_id):
    student_id = session.get("student_id")
    if not student_id:
        return redirect("/login")

    auth_code = request.form.get("auth_code", "").strip()
    db = get_db()
    cursor = db.cursor(dictionary=True)

    # 檢查課程人數
    cursor.execute("SELECT capacity, current_enroll, course_id FROM Course_Offering WHERE offering_id=%s", (offering_id,))
    offering = cursor.fetchone()
    if offering["current_enroll"] >= offering["capacity"] and not auth_code:
        return {"message": "課程已滿，需授權碼"}, 400

    # 檢查授權碼
    if auth_code:
        cursor.execute("""SELECT * FROM Authorization_Code 
                          WHERE code=%s AND offering_id=%s AND used=FALSE AND expire_time > NOW()""",
                       (auth_code, offering_id))
        if not cursor.fetchone():
            return {"message": "授權碼無效"}, 400

    # 檢查重複選課
    cursor.execute("SELECT * FROM Enrollment WHERE student_id=%s AND offering_id=%s", (student_id, offering_id))
    if cursor.fetchone():
        return {"message": "已選過此課"}, 400

    # 檢查時間衝突
    cursor.execute("""SELECT ct.* FROM Enrollment e 
                      JOIN Course_Offering co ON e.offering_id=co.offering_id 
                      JOIN Course_Time ct ON co.time_id=ct.time_id 
                      WHERE e.student_id=%s""", (student_id,))
    my_times = cursor.fetchall()
    cursor.execute("""SELECT ct.* FROM Course_Offering co 
                      JOIN Course_Time ct ON co.time_id=ct.time_id 
                      WHERE co.offering_id=%s""", (offering_id,))
    new_time = cursor.fetchone()
    for t in my_times:
        if t["weekday"] == new_time["weekday"] and not (new_time["end_time"] <= t["start_time"] or new_time["start_time"] >= t["end_time"]):
            return {"message": "時間衝堂"}, 400

    # 檢查先修課程
    cursor.execute("SELECT prereq_id FROM Course_Prereq WHERE course_id=%s", (offering["course_id"],))
    prereqs = cursor.fetchall()
    for p in prereqs:
        cursor.execute("SELECT * FROM Completed_Course WHERE student_id=%s AND course_id=%s", (student_id, p["prereq_id"]))
        if not cursor.fetchone():
            return {"message": "未滿足先修課"}, 400

    # 新增選課
    cursor.execute("INSERT INTO Enrollment(student_id, offering_id, status, priority) VALUES (%s, %s, 'enrolled', 1)", (student_id, offering_id))
    cursor.execute("UPDATE Course_Offering SET current_enroll=current_enroll+1 WHERE offering_id=%s", (offering_id,))
    if auth_code:
        cursor.execute("UPDATE Authorization_Code SET used=TRUE WHERE code=%s", (auth_code,))
    db.commit()
    db.close()
    return {"message": "選課成功"}

@app.route("/teacher/add_course", methods=["GET", "POST"])
def teacher_add_course():
    if "teacher_id" not in session:
        return redirect("/login")

    if request.method == "POST":
        course_id = request.form["course_id"]
        name = request.form["name"]
        credits = request.form["credits"]
        dept_name = request.form["dept_name"]
        prereqs = request.form.getlist("prereqs")  # 多選先修課程

        db = get_db()
        cursor = db.cursor(dictionary=True)
        cursor.execute("INSERT INTO Course(course_id, name, credits, dept_name) VALUES (%s, %s, %s, %s)",
                       (course_id, name, credits, dept_name))

        # 設定先修課程
        for prereq_id in prereqs:
            cursor.execute("INSERT INTO Course_Prereq(course_id, prereq_id) VALUES (%s, %s)", (course_id, prereq_id))

        db.commit()
        db.close()
        return redirect("/all_courses")

    # GET 顯示表單
    db = get_db()
    cursor = db.cursor(dictionary=True)
    cursor.execute("SELECT course_id, name FROM Course")
    all_courses = cursor.fetchall()
    db.close()
    return render_template("teacher_add_course.html", courses=all_courses)

# =========================
# Teacher Helper
# =========================

def require_teacher():
    return "teacher_id" in session


# =========================
# Teacher Dashboard
# =========================

@app.route("/teacher_dashboard")
def teacher_dashboard():

    if not require_teacher():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM Instructor
        WHERE instructor_id=%s
    """, (session["teacher_id"],))

    teacher = cursor.fetchone()

    db.close()

    return render_template(
        "teacher_dashboard.html",
        teacher=teacher
    )


# =========================
# 修改課程
# =========================

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
        SET name=%s,
            credits=%s
        WHERE course_id=%s
    """, (name, credits, course_id))

    db.commit()
    db.close()

    return "課程修改成功"


# =========================
# 新增開課
# =========================

@app.route("/teacher/offering/add", methods=["POST"])
def teacher_add_offering():

    if not require_teacher():
        return redirect("/login")

    course_id = request.form["course_id"]
    semester_id = request.form["semester_id"]
    classroom_id = request.form["classroom_id"]
    time_id = request.form["time_id"]
    capacity = request.form["capacity"]

    teacher_id = session["teacher_id"]

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM Course_Offering
        WHERE (instructor_id=%s OR classroom_id=%s)
        AND time_id=%s
    """, (teacher_id, classroom_id, time_id))

    if cursor.fetchone():
        db.close()
        return "時間衝突"

    cursor = db.cursor()

    cursor.execute("""
        INSERT INTO Course_Offering
        (
            course_id,
            semester_id,
            instructor_id,
            classroom_id,
            time_id,
            capacity,
            current_enroll
        )
        VALUES
        (
            %s,%s,%s,%s,%s,%s,0
        )
    """, (
        course_id,
        semester_id,
        teacher_id,
        classroom_id,
        time_id,
        capacity
    ))

    db.commit()
    db.close()

    return "開課成功"


# =========================
# 修改開課
# =========================

@app.route("/teacher/offering/edit/<offering_id>", methods=["POST"])
def teacher_edit_offering(offering_id):

    if not require_teacher():
        return redirect("/login")

    classroom_id = request.form["classroom_id"]
    time_id = request.form["time_id"]
    capacity = request.form["capacity"]

    teacher_id = session["teacher_id"]

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT *
        FROM Course_Offering
        WHERE offering_id != %s
        AND (instructor_id=%s OR classroom_id=%s)
        AND time_id=%s
    """, (
        offering_id,
        teacher_id,
        classroom_id,
        time_id
    ))

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
    """, (
        classroom_id,
        time_id,
        capacity,
        offering_id
    ))

    db.commit()
    db.close()

    return "修改成功"


# =========================
# 刪除開課
# =========================

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


# =========================
# 查看老師所有開課
# =========================

@app.route("/teacher/courses")
def teacher_courses():

    if not require_teacher():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            co.offering_id,
            c.course_id,
            c.name,
            co.capacity,
            co.current_enroll
        FROM Course_Offering co
        JOIN Course c
            ON co.course_id=c.course_id
        WHERE co.instructor_id=%s
    """, (session["teacher_id"],))

    courses = cursor.fetchall()

    db.close()

    return render_template(
        "teacher_courses.html",
        courses=courses
    )


# =========================
# 查看老師課表
# =========================

@app.route("/teacher/schedule")
def teacher_schedule():

    if not require_teacher():
        return redirect("/login")

    db = get_db()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            c.name,
            ct.weekday,
            ct.start_time,
            ct.end_time,
            cl.building,
            cl.room_number
        FROM Course_Offering co
        JOIN Course c
            ON co.course_id=c.course_id
        JOIN Course_Time ct
            ON co.time_id=ct.time_id
        LEFT JOIN Classroom cl
            ON co.classroom_id=cl.classroom_id
        WHERE co.instructor_id=%s
    """, (session["teacher_id"],))

    schedule = cursor.fetchall()

    db.close()

    return render_template(
        "teacher_schedule.html",
        schedule=schedule
    )
    
if __name__ == "__main__":
    app.run(debug=True)
