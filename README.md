# 系統功能實作規劃:
## 檢視課程
- 選擇檢視該學期開的課程，或是所有課程
- 課程查詢
    - 依課程名稱、時段、系所檢索
    - 顯示課程資訊：修課人數、教授、教室、先修課程
## 登入/註冊
- 登入：帳號密碼驗證
- 註冊：姓名(ID)、系所
### 學生端功能
- 新增選課：
    - 檢查時間衝突
    - 檢查先修課程是否完成
    - 檢查修課人數是否已滿
    - 支援授權碼選課
- 查詢已選課程： 
    - 以日程表方式呈現
    - 顯示年級、總學分數、本學期學分數
- 刪除已選課程
### 老師端功能
- 新增課程：
    - 設定課程名稱、開課系所、學分數、先修課程
- 修改課程：
    - 修改課程名稱、開課系所、學分數、先修課程
- 新增本學期開課：
    - 檢查時間衝突
    - 設定修課人數上限、教授、教室位置
    - 設定授權碼人數
- 查詢已開課程：
    - 以日程表方式呈現
    - 查詢教授所在系的所有課堂列表
- 修改已開課程：
    - 調整時段、教室、授課老師
- 刪除已開課程


# system execute
1. python 
```python
python app.py
```
  or flask
```flask
flask run
```
2. link
```
http://127.0.0.1:5000/
```


# MSQL:
## 用戶
```sql
CREATE USER 'course_admin'@'localhost' IDENTIFIED BY 'mypassword';
GRANT ALL PRIVILEGES ON course_system.* TO 'course_admin'@'localhost';
FLUSH PRIVILEGES;
```

## 原DATABASE
```sql
CREATE DATABASE course_system;
USE course_system;
-- 學生表
CREATE TABLE Student (
    student_id VARCHAR(20) PRIMARY KEY,
    password VARCHAR(100) NOT NULL
);

-- 老師表
CREATE TABLE Instructor (
    instructor_id VARCHAR(20) PRIMARY KEY,
    password VARCHAR(100) NOT NULL
);

-- 系所
CREATE TABLE Department (
    dept_name VARCHAR(50) PRIMARY KEY,
);

-- 課程
CREATE TABLE Course (
    course_id VARCHAR(20) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    credits INT NOT NULL,
    dept_name VARCHAR(50),
    FOREIGN KEY (dept_name) REFERENCES Department(dept_name)
);

-- 課程時間表
CREATE TABLE Course_Time (
    time_id INT AUTO_INCREMENT PRIMARY KEY,
    weekday VARCHAR(10) NOT NULL,   -- e.g. 'Mon', 'Tue'
    start_time TIME NOT NULL,
    end_time TIME NOT NULL
);

-- 教室
CREATE TABLE Classroom (
    classroom_id VARCHAR(20) PRIMARY KEY,
    building VARCHAR(50),
    room_number VARCHAR(20),
    capacity INT
);

-- 開課資訊表
CREATE TABLE Course_Offering (
    offering_id INT AUTO_INCREMENT PRIMARY KEY,
    classroom_id VARCHAR(50),
    course_id VARCHAR(20) NOT NULL,
    semester VARCHAR(20) NOT NULL,
    instructor_id VARCHAR(20),
    capacity INT NOT NULL,
    current_enroll INT DEFAULT 0,
    time_id INT,
    FOREIGN KEY (classroom_id) REFERENCES Classroom(classroom_id),
    FOREIGN KEY (course_id) REFERENCES Course(course_id),
    FOREIGN KEY (instructor_id) REFERENCES Instructor(instructor_id),
    FOREIGN KEY (time_id) REFERENCES Course_Time(time_id)
);

-- 選課紀錄表
CREATE TABLE Enrollment (
    enroll_id INT AUTO_INCREMENT PRIMARY KEY,
    student_id VARCHAR(20) NOT NULL,
    offering_id INT NOT NULL,
    status VARCHAR(20) DEFAULT 'enrolled',
    priority INT DEFAULT 1,
    FOREIGN KEY (student_id) REFERENCES Student(student_id),
    FOREIGN KEY (offering_id) REFERENCES Course_Offering(offering_id)
);

-- 授權碼表
CREATE TABLE Authorization_Code (
    code_id INT AUTO_INCREMENT PRIMARY KEY,
    offering_id INT NOT NULL,
    code VARCHAR(50) NOT NULL,
    expire_time DATETIME,
    used BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (offering_id) REFERENCES Course_Offering(offering_id)
);

-- 先修課程表
CREATE TABLE Course_Prereq (
    course_id VARCHAR(20) NOT NULL,
    prereq_id VARCHAR(20) NOT NULL,
    PRIMARY KEY (course_id, prereq_id),
    FOREIGN KEY (course_id) REFERENCES Course(course_id),
    FOREIGN KEY (prereq_id) REFERENCES Course(course_id)
);

-- 已修課程表
CREATE TABLE Completed_Course (
    student_id VARCHAR(20) NOT NULL,
    course_id VARCHAR(20) NOT NULL,
    grade VARCHAR(5),
    PRIMARY KEY (student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES Student(student_id),
    FOREIGN KEY (course_id) REFERENCES Course(course_id)
);

```
## 新DATABASE
```sql
CREATE TABLE Department (
    dept_name VARCHAR(100) PRIMARY KEY,
    building VARCHAR(100) NOT NULL
);

CREATE TABLE Instructor (
    instructor_id VARCHAR(20) PRIMARY KEY,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    dept_name VARCHAR(100),
    FOREIGN KEY (dept_name) REFERENCES Department(dept_name) ON DELETE SET NULL
);

CREATE TABLE Student (
    student_id VARCHAR(20) PRIMARY KEY,
    password VARCHAR(255) NOT NULL,
    name VARCHAR(100) NOT NULL,
    dept_name VARCHAR(100),
    grade INT,
    tot_credits INT DEFAULT 0,
    advisor_id VARCHAR(50),
    FOREIGN KEY (dept_name) REFERENCES Department(dept_name) ON DELETE SET NULL,
    FOREIGN KEY (advisor_id) REFERENCES Instructor(instructor_id) ON DELETE SET NULL
);

CREATE TABLE Semester (
    semester_id VARCHAR(50) PRIMARY KEY,
    year INT NOT NULL,
    term VARCHAR(20) NOT NULL
);

CREATE TABLE Classroom (
    classroom_id VARCHAR(50) PRIMARY KEY,
    building VARCHAR(100) NOT NULL,
    room_number VARCHAR(20) NOT NULL,
    capacity INT NOT NULL
);

CREATE TABLE Course_Time (
    time_id VARCHAR(20) PRIMARY KEY,
    weekday INT NOT NULL,
    start_time TIME NOT NULL,
    end_time TIME NOT NULL
);

CREATE TABLE Course (
    course_id VARCHAR(50) PRIMARY KEY,
    name VARCHAR(100) NOT NULL,
    credits INT NOT NULL,
    category ENUM('required', 'elective') NOT NULL,
    dept_name VARCHAR(100),
    FOREIGN KEY (dept_name) REFERENCES Department(dept_name) ON DELETE SET NULL
);

CREATE TABLE Course_Prereq (
    course_id VARCHAR(50),
    prereq_id VARCHAR(50),
    PRIMARY KEY (course_id, prereq_id),
    FOREIGN KEY (course_id) REFERENCES Course(course_id) ON DELETE CASCADE,
    FOREIGN KEY (prereq_id) REFERENCES Course(course_id) ON DELETE CASCADE
);

-- ⭐ 修改後的 Course_Offering：移除了原本的 time_id 欄位與其外鍵約束
CREATE TABLE Course_Offering (
    offering_id VARCHAR(50) PRIMARY KEY,
    course_id VARCHAR(50) NOT NULL,
    semester_id VARCHAR(50) NOT NULL,
    instructor_id VARCHAR(20),
    classroom_id VARCHAR(50),
    capacity INT NOT NULL,
    current_enroll INT DEFAULT 0,

    FOREIGN KEY (course_id) REFERENCES Course(course_id) ON DELETE CASCADE,
    FOREIGN KEY (semester_id) REFERENCES Semester(semester_id) ON DELETE CASCADE,
    FOREIGN KEY (instructor_id) REFERENCES Instructor(instructor_id) ON DELETE SET NULL,
    FOREIGN KEY (classroom_id) REFERENCES Classroom(classroom_id) ON DELETE SET NULL
);

-- ⭐ 新增的多對多中介資料表：用來存放一門開課的多個時間段
CREATE TABLE Offering_Time (
    offering_id VARCHAR(50),
    time_id VARCHAR(20),
    PRIMARY KEY (offering_id, time_id),
    FOREIGN KEY (offering_id) REFERENCES Course_Offering(offering_id) ON DELETE CASCADE,
    FOREIGN KEY (time_id) REFERENCES Course_Time(time_id) ON DELETE CASCADE
);

CREATE TABLE Authorization_Code (
    code VARCHAR(20) PRIMARY KEY,
    offering_id VARCHAR(50),
    expire_time TIMESTAMP,
    used BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (offering_id) REFERENCES Course_Offering(offering_id) ON DELETE CASCADE
);

CREATE TABLE Enrollment (
    student_id VARCHAR(20),
    offering_id VARCHAR(50),
    status ENUM('enrolled', 'waitlist', 'dropped') DEFAULT 'waitlist',
    priority INT,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (student_id, offering_id),
    FOREIGN KEY (student_id) REFERENCES Student(student_id) ON DELETE CASCADE,
    FOREIGN KEY (offering_id) REFERENCES Course_Offering(offering_id) ON DELETE CASCADE
);

CREATE TABLE Completed_Course (
    student_id VARCHAR(20),
    course_id VARCHAR(50),
    grade VARCHAR(2),
    PRIMARY KEY (student_id, course_id),
    FOREIGN KEY (student_id) REFERENCES Student(student_id) ON DELETE CASCADE,
    FOREIGN KEY (course_id) REFERENCES Course(course_id) ON DELETE CASCADE
);
```
