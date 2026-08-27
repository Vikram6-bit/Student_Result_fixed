from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    flash,
    Response
)

import csv
import io

import mysql.connector
from mysql.connector import Error

from werkzeug.security import (
    generate_password_hash,
    check_password_hash
)

from functools import wraps


# =========================================================
# FLASK APP
# =========================================================

app = Flask(__name__)

app.secret_key = "student_result_secret_key_123"


# =========================================================
# MYSQL CONNECTION
# =========================================================

def get_db_connection():
    return mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="student_result"
    )


# =========================================================
# CREATE / RESET ADMIN ACCOUNT
# =========================================================

def create_admin_if_needed():

    db = None
    cursor = None

    try:

        db = get_db_connection()
        cursor = db.cursor(dictionary=True)

        password_hash = generate_password_hash("admin123")

        # Check admin
        cursor.execute(
            """
            SELECT id
            FROM users
            WHERE username = %s
            LIMIT 1
            """,
            ("admin",)
        )

        admin = cursor.fetchone()

        if admin:

            cursor.execute(
                """
                UPDATE users
                SET password = %s,
                    role = 'admin'
                WHERE username = %s
                """,
                (
                    password_hash,
                    "admin"
                )
            )

        else:

            cursor.execute(
                """
                INSERT INTO users
                (
                    username,
                    password,
                    role,
                    student_id
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    NULL
                )
                """,
                (
                    "admin",
                    password_hash,
                    "admin"
                )
            )

        db.commit()

        print("---------------------------------------")
        print("Admin account ready")
        print("Username: admin")
        print("Password: admin123")
        print("---------------------------------------")

    except Error as e:

        if db:
            db.rollback()

        print("Admin setup error:", e)

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# ADMIN REQUIRED
# =========================================================

def admin_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if session.get("role") != "admin":

            flash(
                "Admin access required.",
                "error"
            )

            return redirect(
                url_for("admin_login")
            )

        return f(*args, **kwargs)

    return decorated_function


# =========================================================
# STUDENT REQUIRED
# =========================================================

def student_required(f):

    @wraps(f)
    def decorated_function(*args, **kwargs):

        if not session.get("student_id"):

            flash(
                "Please login as a student.",
                "error"
            )

            return redirect(
                url_for("student_login")
            )

        return f(*args, **kwargs)

    return decorated_function


# =========================================================
# HOME
# =========================================================

@app.route("/")
def home():

    if session.get("role") == "admin":

        return redirect(
            url_for("admin_dashboard")
        )

    if session.get("role") == "student":

        return redirect(
            url_for("student_dashboard")
        )

    return render_template(
        "home.html"
    )


# =========================================================
# ADMIN LOGIN
# =========================================================

@app.route(
    "/admin_login",
    methods=["GET", "POST"]
)
def admin_login():

    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()

        password = request.form.get(
            "password",
            ""
        )

        if not username or not password:

            flash(
                "Enter username and password.",
                "error"
            )

            return render_template(
                "admin_login.html"
            )

        db = None
        cursor = None

        try:

            db = get_db_connection()

            cursor = db.cursor(
                dictionary=True
            )

            cursor.execute(
                """
                SELECT
                    id,
                    username,
                    password,
                    role
                FROM users
                WHERE username = %s
                AND role = 'admin'
                LIMIT 1
                """,
                (username,)
            )

            user = cursor.fetchone()

            if user and check_password_hash(
                user["password"],
                password
            ):

                session.clear()

                session["user_id"] = user["id"]
                session["username"] = user["username"]
                session["role"] = "admin"

                flash(
                    "Admin login successful.",
                    "success"
                )

                return redirect(
                    url_for("admin_dashboard")
                )

            else:

                flash(
                    "Invalid admin username or password.",
                    "error"
                )

        except Error as e:

            flash(
                "Database error: " + str(e),
                "error"
            )

        finally:

            if cursor:
                cursor.close()

            if db:
                db.close()

    return render_template(
        "admin_login.html"
    )


# =========================================================
# ADMIN DASHBOARD
# =========================================================

@app.route("/admin_dashboard")
@app.route("/admin-dashboard")
def admin_dashboard():

    if session.get("role") != "admin":
        return redirect(url_for("admin_login"))

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("SELECT AVG(python), AVG(sql_marks), AVG(html) FROM results")
    row = cursor.fetchone()

    cursor.close()
    db.close()

    avg_python = round(row[0], 2) if row[0] else 0
    avg_sql = round(row[1], 2) if row[1] else 0
    avg_html = round(row[2], 2) if row[2] else 0

    return render_template(
        "admin_dashboard.html",
        avg_python=avg_python,
        avg_sql=avg_sql,
        avg_html=avg_html
    )

# =========================================================
# STUDENT LOGIN
# =========================================================

@app.route(
    "/student-login",
    methods=["GET", "POST"]
)
@app.route(
    "/student_login",
    methods=["GET", "POST"]
)
def student_login():

    if request.method == "POST":

        roll_no = request.form.get(
            "roll_no",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        if not roll_no or not email:

            flash(
                "Enter Roll Number and Email.",
                "error"
            )

            return render_template(
                "student_login.html"
            )

        db = None
        cursor = None

        try:

            db = get_db_connection()

            cursor = db.cursor(
                dictionary=True
            )

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    roll_no,
                    email
                FROM students
                WHERE roll_no = %s
                AND LOWER(email) = LOWER(%s)
                LIMIT 1
                """,
                (
                    roll_no,
                    email
                )
            )

            student = cursor.fetchone()

            if student:

                session.clear()

                session["student_id"] = student["id"]
                session["student_name"] = student["name"]
                session["student_roll_no"] = student["roll_no"]
                session["role"] = "student"

                flash(
                    "Student login successful!",
                    "success"
                )

                return redirect(
                    url_for("student_dashboard")
                )

            else:

                flash(
                    "Invalid Roll Number or Email.",
                    "error"
                )

        except Error as e:

            flash(
                "Database error: " + str(e),
                "error"
            )

        finally:

            if cursor:
                cursor.close()

            if db:
                db.close()

    return render_template(
        "student_login.html"
    )


# =========================================================
# STUDENT DASHBOARD
# =========================================================

@app.route("/student-dashboard")
@app.route("/student_dashboard")
@student_required
def student_dashboard():

    student_id = session.get(
        "student_id"
    )

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        # Get student
        cursor.execute(
            """
            SELECT
                id,
                name,
                roll_no,
                email
            FROM students
            WHERE id = %s
            LIMIT 1
            """,
            (student_id,)
        )

        student = cursor.fetchone()

        if not student:

            session.clear()

            flash(
                "Student record not found.",
                "error"
            )

            return redirect(
                url_for("student_login")
            )

        # Get result
        cursor.execute(
            """
            SELECT
                id,
                python,
                sql_marks,
                html
            FROM results
            WHERE student_id = %s
            ORDER BY id DESC
            """,
            (student_id,)
        )

        rows = cursor.fetchall()

        results_list = []

        for row in rows:

            python_marks = int(
                row["python"] or 0
            )

            sql_marks = int(
                row["sql_marks"] or 0
            )

            html_marks = int(
                row["html"] or 0
            )

            total = (
                python_marks
                + sql_marks
                + html_marks
            )

            percentage = (
                total / 300
            ) * 100

            if percentage >= 80:
                grade = "A"

            elif percentage >= 70:
                grade = "B"

            elif percentage >= 60:
                grade = "C"

            elif percentage >= 50:
                grade = "D"

            else:
                grade = "F"

            results_list.append(
                {
                    "id": row["id"],
                    "python": python_marks,
                    "sql": sql_marks,
                    "html": html_marks,
                    "total": total,
                    "percentage": round(
                        percentage,
                        2
                    ),
                    "grade": grade
                }
            )

        return render_template(
            "student_dashboard.html",
            student=student,
            results=results_list
        )

    except Error as e:

        return render_template(
            "error.html",
            message="Database error: " + str(e)
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# VIEW STUDENTS
#
# IMPORTANT:
# Two endpoint names are provided:
#
# students
# view_students
#
# Therefore BOTH work:
#
# url_for("students")
# url_for("view_students")
# =========================================================

@app.route(
    "/students",
    endpoint="students"
)
@app.route(
    "/students",
    endpoint="view_students"
)
@app.route(
    "/view_students",
    endpoint="view_students_page"
)
@admin_required
def students():

    db = None
    cursor = None

    try:

        db = get_db_connection()

        # Dictionary cursor because students.html
        # reads student.name, student.roll_no, etc.
        cursor = db.cursor(dictionary=True)

        cursor.execute(
            """
            SELECT
                id,
                name,
                roll_no,
                email,
                class_name
            FROM students
            ORDER BY id
            """
        )

        student_rows = cursor.fetchall()

        return render_template(
            "students.html",
            students=student_rows
        )

    except Error as e:

        return render_template(
            "error.html",
            message="Database error: " + str(e)
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# ADD STUDENT
# =========================================================

@app.route(
    "/add_student",
    methods=["GET", "POST"]
)
@admin_required
def add_student():

    if request.method == "POST":

        name = request.form.get(
            "name",
            ""
        ).strip()

        roll_no = request.form.get(
            "roll_no",
            ""
        ).strip()

        email = request.form.get(
            "email",
            ""
        ).strip()

        class_name = request.form.get(
            "class_name",
            ""
        ).strip()

        if not name or not roll_no:

            flash(
                "Name and Roll Number are required.",
                "error"
            )

            return render_template(
                "add_student.html"
            )

        db = None
        cursor = None

        try:

            db = get_db_connection()

            cursor = db.cursor(
                dictionary=True
            )

            # Check roll number
            cursor.execute(
                """
                SELECT id
                FROM students
                WHERE roll_no = %s
                LIMIT 1
                """,
                (roll_no,)
            )

            if cursor.fetchone():

                flash(
                    "Roll number already exists.",
                    "error"
                )

                return render_template(
                    "add_student.html"
                )

            # Check email
            if email:

                cursor.execute(
                    """
                    SELECT id
                    FROM students
                    WHERE LOWER(email) = LOWER(%s)
                    LIMIT 1
                    """,
                    (email,)
                )

                if cursor.fetchone():

                    flash(
                        "Email already exists.",
                        "error"
                    )

                    return render_template(
                        "add_student.html"
                    )

            # Insert
            cursor.execute(
                """
                INSERT INTO students
                (
                    name,
                    roll_no,
                    email,
                    class_name
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    name,
                    roll_no,
                    email,
                    class_name
                )
            )

            db.commit()

            flash(
                "Student added successfully!",
                "success"
            )

            return redirect(
                url_for("students")
            )

        except Error as e:

            if db:
                db.rollback()

            flash(
                "Database error: " + str(e),
                "error"
            )

        finally:

            if cursor:
                cursor.close()

            if db:
                db.close()

    return render_template(
        "add_student.html"
    )


# =========================================================
# EDIT STUDENT
# =========================================================

@app.route(
    "/edit_student/<int:student_id>",
    methods=["GET", "POST"]
)
@admin_required
def edit_student(student_id):

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        if request.method == "POST":

            name = request.form.get(
                "name",
                ""
            ).strip()

            roll_no = request.form.get(
                "roll_no",
                ""
            ).strip()

            email = request.form.get(
                "email",
                ""
            ).strip()

            class_name = request.form.get(
                "class_name",
                ""
            ).strip()

            if not name or not roll_no:

                flash(
                    "Name and Roll Number are required.",
                    "error"
                )

                return redirect(
                    url_for(
                        "edit_student",
                        student_id=student_id
                    )
                )

            # Duplicate roll number
            cursor.execute(
                """
                SELECT id
                FROM students
                WHERE roll_no = %s
                AND id != %s
                LIMIT 1
                """,
                (
                    roll_no,
                    student_id
                )
            )

            if cursor.fetchone():

                flash(
                    "Roll number already exists.",
                    "error"
                )

                return redirect(
                    url_for(
                        "edit_student",
                        student_id=student_id
                    )
                )

            # Duplicate email
            if email:

                cursor.execute(
                    """
                    SELECT id
                    FROM students
                    WHERE LOWER(email) = LOWER(%s)
                    AND id != %s
                    LIMIT 1
                    """,
                    (
                        email,
                        student_id
                    )
                )

                if cursor.fetchone():

                    flash(
                        "Email already exists.",
                        "error"
                    )

                    return redirect(
                        url_for(
                            "edit_student",
                            student_id=student_id
                        )
                    )

            cursor.execute(
                """
                UPDATE students
                SET
                    name = %s,
                    roll_no = %s,
                    email = %s,
                    class_name = %s
                WHERE id = %s
                """,
                (
                    name,
                    roll_no,
                    email,
                    class_name,
                    student_id
                )
            )

            db.commit()

            flash(
                "Student updated successfully.",
                "success"
            )

            return redirect(
                url_for("students")
            )

        # GET
        cursor.execute(
            """
            SELECT
                id,
                name,
                roll_no,
                email,
                class_name
            FROM students
            WHERE id = %s
            LIMIT 1
            """,
            (student_id,)
        )

        student = cursor.fetchone()

        if not student:

            return render_template(
                "error.html",
                message="Student not found."
            )

        return render_template(
            "edit_student.html",
            student=student
        )

    except Error as e:

        if db:
            db.rollback()

        return render_template(
            "error.html",
            message="Database error: " + str(e)
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# DELETE STUDENT
# =========================================================

@app.route(
    "/delete_student/<int:student_id>"
)
@admin_required
def delete_student(student_id):

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        # Delete results first
        cursor.execute(
            """
            DELETE FROM results
            WHERE student_id = %s
            """,
            (student_id,)
        )

        # Delete student
        cursor.execute(
            """
            DELETE FROM students
            WHERE id = %s
            """,
            (student_id,)
        )

        db.commit()

        flash(
            "Student deleted successfully.",
            "success"
        )

        return redirect(
            url_for("students")
        )

    except Error as e:

        if db:
            db.rollback()

        return render_template(
            "error.html",
            message="Database error: " + str(e)
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# SEARCH STUDENT
# =========================================================

@app.route(
    "/search_student",
    methods=["GET", "POST"]
)
@admin_required
def search_student():

    search = ""
    results = []

    if request.method == "POST":

        search = request.form.get(
            "search",
            ""
        ).strip()

    else:

        search = request.args.get(
            "search",
            ""
        ).strip()

    if search:

        db = None
        cursor = None

        try:

            db = get_db_connection()

            cursor = db.cursor(dictionary=True)

            value = "%" + search + "%"

            cursor.execute(
                """
                SELECT
                    id,
                    name,
                    roll_no,
                    email,
                    class_name
                FROM students
                WHERE name LIKE %s
                   OR roll_no LIKE %s
                   OR email LIKE %s
                   OR class_name LIKE %s
                ORDER BY id
                """,
                (
                    value,
                    value,
                    value,
                    value
                )
            )

            results = cursor.fetchall()

        except Error as e:

            flash(
                "Database error: " + str(e),
                "error"
            )

        finally:

            if cursor:
                cursor.close()

            if db:
                db.close()

    return render_template(
        "search_student.html",
        results=results,
        search=search
    )


# =========================================================
# ADD RESULT
# =========================================================

@app.route(
    "/add_result",
    methods=["GET", "POST"]
)
@admin_required
def add_result():

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        if request.method == "POST":

            student_id = request.form.get(
                "student_id",
                ""
            ).strip()

            python_marks = request.form.get(
                "python",
                ""
            ).strip()

            sql_marks = request.form.get(
                "sql_marks",
                ""
            ).strip()

            html_marks = request.form.get(
                "html",
                ""
            ).strip()

            if not student_id:

                flash(
                    "Please select a student.",
                    "error"
                )

                return redirect(
                    url_for("add_result")
                )

            try:

                python_marks = int(
                    python_marks
                )

                sql_marks = int(
                    sql_marks
                )

                html_marks = int(
                    html_marks
                )

            except ValueError:

                flash(
                    "Marks must be numbers.",
                    "error"
                )

                return redirect(
                    url_for("add_result")
                )

            if (
                python_marks < 0
                or python_marks > 100
                or sql_marks < 0
                or sql_marks > 100
                or html_marks < 0
                or html_marks > 100
            ):

                flash(
                    "Marks must be between 0 and 100.",
                    "error"
                )

                return redirect(
                    url_for("add_result")
                )

            # Check student
            cursor.execute(
                """
                SELECT id
                FROM students
                WHERE id = %s
                LIMIT 1
                """,
                (student_id,)
            )

            if not cursor.fetchone():

                flash(
                    "Student does not exist.",
                    "error"
                )

                return redirect(
                    url_for("add_result")
                )

            # Check existing result
            cursor.execute(
                """
                SELECT id
                FROM results
                WHERE student_id = %s
                LIMIT 1
                """,
                (student_id,)
            )

            if cursor.fetchone():

                flash(
                    "Result already exists for this student.",
                    "error"
                )

                return redirect(
                    url_for("add_result")
                )

            # Insert
            cursor.execute(
                """
                INSERT INTO results
                (
                    student_id,
                    python,
                    sql_marks,
                    html
                )
                VALUES
                (
                    %s,
                    %s,
                    %s,
                    %s
                )
                """,
                (
                    student_id,
                    python_marks,
                    sql_marks,
                    html_marks
                )
            )

            db.commit()

            flash(
                "Result added successfully.",
                "success"
            )

            return redirect(
                url_for("results")
            )

        # Student dropdown
        cursor.execute(
            """
            SELECT
                id,
                name,
                roll_no
            FROM students
            ORDER BY name
            """
        )

        students_list = cursor.fetchall()

        return render_template(
            "add_result.html",
            students=students_list
        )

    except Error as e:

        if db:
            db.rollback()

        flash(
            "Database error: " + str(e),
            "error"
        )

        return redirect(
            url_for("add_result")
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# VIEW RESULTS
#
# BOTH endpoint names work:
#
# results
# view_results
# =========================================================

@app.route(
    "/results",
    endpoint="results"
)
@app.route(
    "/results",
    endpoint="view_results"
)
@app.route(
    "/view_results",
    endpoint="view_results_page"
)
@admin_required
def results():

    db = None
    cursor = None

    try:

        db = get_db_connection()

        # Normal cursor because
        # results.html may use result[0],
        # result[1], etc.
        cursor = db.cursor()

        cursor.execute(
            """
            SELECT
                results.id,
                students.name,
                students.roll_no,
                results.python,
                results.sql_marks,
                results.html
            FROM results
            INNER JOIN students
                ON results.student_id = students.id
            ORDER BY results.id
            """
        )

        rows = cursor.fetchall()

        result_list = []

        for row in rows:

            python_marks = int(
                row[3] or 0
            )

            sql_marks = int(
                row[4] or 0
            )

            html_marks = int(
                row[5] or 0
            )

            total = (
                python_marks
                + sql_marks
                + html_marks
            )

            percentage = (
                total / 300
            ) * 100

            if percentage >= 80:
                grade = "A"

            elif percentage >= 70:
                grade = "B"

            elif percentage >= 60:
                grade = "C"

            elif percentage >= 50:
                grade = "D"

            else:
                grade = "F"

            result_list.append(
                {
                    "id": row[0],
                    "name": row[1],
                    "roll_no": row[2],
                    "python": python_marks,
                    "sql": sql_marks,
                    "html": html_marks,
                    "total": total,
                    "percentage": round(percentage, 2),
                    "grade": grade
                }
            )

        return render_template(
            "results.html",
            results=result_list
        )

    except Error as e:

        return render_template(
            "error.html",
            message="Database error: " + str(e)
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# EDIT RESULT
# =========================================================

@app.route(
    "/edit_result/<int:result_id>",
    methods=["GET", "POST"]
)
@admin_required
def edit_result(result_id):

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor(
            dictionary=True
        )

        if request.method == "POST":

            python_marks = request.form.get(
                "python",
                "0"
            )

            sql_marks = request.form.get(
                "sql",
                "0"
            )

            html_marks = request.form.get(
                "html",
                "0"
            )

            try:

                python_marks = int(
                    python_marks
                )

                sql_marks = int(
                    sql_marks
                )

                html_marks = int(
                    html_marks
                )

            except ValueError:

                flash(
                    "Marks must be numbers.",
                    "error"
                )

                return redirect(
                    url_for(
                        "edit_result",
                        result_id=result_id
                    )
                )

            if (
                python_marks < 0
                or python_marks > 100
                or sql_marks < 0
                or sql_marks > 100
                or html_marks < 0
                or html_marks > 100
            ):

                flash(
                    "Marks must be between 0 and 100.",
                    "error"
                )

                return redirect(
                    url_for(
                        "edit_result",
                        result_id=result_id
                    )
                )

            cursor.execute(
                """
                UPDATE results
                SET
                    python = %s,
                    sql_marks = %s,
                    html = %s
                WHERE id = %s
                """,
                (
                    python_marks,
                    sql_marks,
                    html_marks,
                    result_id
                )
            )

            db.commit()

            flash(
                "Result updated successfully.",
                "success"
            )

            return redirect(
                url_for("results")
            )

        cursor.execute(
            """
            SELECT
                id,
                student_id,
                python,
                sql_marks,
                html
            FROM results
            WHERE id = %s
            LIMIT 1
            """,
            (result_id,)
        )

        result = cursor.fetchone()

        if not result:

            return render_template(
                "error.html",
                message="Result not found."
            )

        return render_template(
            "edit_result.html",
            result=result
        )

    except Error as e:

        if db:
            db.rollback()

        return render_template(
            "error.html",
            message="Database error: " + str(e)
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# DELETE RESULT
# =========================================================

@app.route(
    "/delete_result/<int:result_id>"
)
@admin_required
def delete_result(result_id):

    db = None
    cursor = None

    try:

        db = get_db_connection()

        cursor = db.cursor()

        cursor.execute(
            """
            DELETE FROM results
            WHERE id = %s
            """,
            (result_id,)
        )

        db.commit()

        flash(
            "Result deleted successfully.",
            "success"
        )

        return redirect(
            url_for("results")
        )

    except Error as e:

        if db:
            db.rollback()

        return render_template(
            "error.html",
            message="Database error: " + str(e)
        )

    finally:

        if cursor:
            cursor.close()

        if db:
            db.close()


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    flash(
        "You have been logged out.",
        "success"
    )

    return redirect(
        url_for("home")
    )


# =========================================================
# 404 ERROR
# =========================================================

@app.errorhandler(404)
def page_not_found(error):

    return render_template(
        "error.html",
        message="Page not found."
    ), 404


# =========================================================
# 500 ERROR
# =========================================================

@app.errorhandler(500)
def internal_error(error):

    return render_template(
        "error.html",
        message="Internal server error."
    ), 500


@app.route("/download_results")
@admin_required
def download_results():

    db = get_db_connection()
    cursor = db.cursor()

    cursor.execute("""
        SELECT students.name, students.roll_no, results.python, results.sql_marks, results.html
        FROM results
        INNER JOIN students ON results.student_id = students.id
    """)

    rows = cursor.fetchall()

    cursor.close()
    db.close()

    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Name", "Roll No", "Python", "SQL", "HTML"])
    writer.writerows(rows)

    return Response(
        output.getvalue(),
        mimetype="text/csv",
        headers={"Content-Disposition": "attachment;filename=results.csv"}
    )

@app.route("/top_scorers")
@admin_required
def top_scorers():

    db = get_db_connection()
    cursor = db.cursor(dictionary=True)

    cursor.execute("""
        SELECT
            students.name,
            students.roll_no,
            (results.python + results.sql_marks + results.html) AS total
        FROM results
        INNER JOIN students ON results.student_id = students.id
        ORDER BY total DESC
        LIMIT 5
    """)

    top_students = cursor.fetchall()

    cursor.close()
    db.close()

    return render_template("top_scorers.html", top_students=top_students)


# =========================================================
# START APPLICATION
# =========================================================

if __name__ == "__main__":

    create_admin_if_needed()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )