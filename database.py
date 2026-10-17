import sqlite3
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
DB_DIR = BASE_DIR / "database"
DB_PATH = DB_DIR / "library.db"


def get_connection():
    DB_DIR.mkdir(exist_ok=True)

    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row

    conn.execute("PRAGMA foreign_keys = ON")

    return conn


# =========================================================
# إنشاء قاعدة البيانات
# =========================================================

def create_tables():
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS stages (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_ar TEXT NOT NULL,
            name_en TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS semesters (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            stage_id INTEGER NOT NULL,
            name_ar TEXT NOT NULL,
            name_en TEXT NOT NULL,

            FOREIGN KEY (stage_id)
                REFERENCES stages(id)
                ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS subjects (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            semester_id INTEGER NOT NULL,
            name_ar TEXT NOT NULL,
            name_en TEXT NOT NULL,

            UNIQUE (
                semester_id,
                name_ar
            ),

            FOREIGN KEY (semester_id)
                REFERENCES semesters(id)
                ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            name_ar TEXT NOT NULL,
            name_en TEXT NOT NULL
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS files (
            id INTEGER PRIMARY KEY AUTOINCREMENT,

            subject_id INTEGER NOT NULL,
            category_id INTEGER NOT NULL,

            title TEXT NOT NULL,

            telegram_file_id TEXT NOT NULL,
            telegram_unique_id TEXT,

            file_name TEXT,
            mime_type TEXT,

            uploaded_by INTEGER,

            created_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP,

            FOREIGN KEY (subject_id)
                REFERENCES subjects(id)
                ON DELETE CASCADE,

            FOREIGN KEY (category_id)
                REFERENCES categories(id)
                ON DELETE CASCADE
        )
    """)

    cursor.execute("""
        CREATE TABLE IF NOT EXISTS users (
            telegram_id INTEGER PRIMARY KEY,
            first_name TEXT,
            username TEXT,

            joined_at TIMESTAMP
                DEFAULT CURRENT_TIMESTAMP
        )
    """)

    conn.commit()
    conn.close()


# =========================================================
# البيانات الأساسية
# =========================================================

def seed_database():
    conn = get_connection()
    cursor = conn.cursor()

    # -------------------------
    # المراحل
    # -------------------------

    cursor.execute(
        "SELECT COUNT(*) FROM stages"
    )

    if cursor.fetchone()[0] == 0:

        stages = [
            ("المرحلة الأولى", "First Stage"),
            ("المرحلة الثانية", "Second Stage"),
            ("المرحلة الثالثة", "Third Stage"),
            ("المرحلة الرابعة", "Fourth Stage"),
        ]

        cursor.executemany(
            """
            INSERT INTO stages (
                name_ar,
                name_en
            )
            VALUES (?, ?)
            """,
            stages
        )

        conn.commit()

    # -------------------------
    # الفصول
    # -------------------------

    cursor.execute(
        "SELECT COUNT(*) FROM semesters"
    )

    if cursor.fetchone()[0] == 0:

        cursor.execute(
            "SELECT id FROM stages ORDER BY id"
        )

        stages = cursor.fetchall()

        for stage in stages:

            cursor.execute(
                """
                INSERT INTO semesters (
                    stage_id,
                    name_ar,
                    name_en
                )
                VALUES (?, ?, ?)
                """,
                (
                    stage["id"],
                    "الفصل الأول",
                    "First Semester"
                )
            )

            cursor.execute(
                """
                INSERT INTO semesters (
                    stage_id,
                    name_ar,
                    name_en
                )
                VALUES (?, ?, ?)
                """,
                (
                    stage["id"],
                    "الفصل الثاني",
                    "Second Semester"
                )
            )

        conn.commit()

    # -------------------------
    # أقسام الملفات
    # -------------------------

    cursor.execute(
        "SELECT COUNT(*) FROM categories"
    )

    if cursor.fetchone()[0] == 0:

        categories = [
            ("المحاضرات", "Lectures"),
            ("ملفات العملي", "Labs"),
            ("الواجبات", "Assignments"),
            ("أسئلة امتحانات", "Previous Questions"),
            ("مصادر خارجية", "Books"),
            ("الملخصات", "Summaries"),
        ]

        cursor.executemany(
            """
            INSERT INTO categories (
                name_ar,
                name_en
            )
            VALUES (?, ?)
            """,
            categories
        )

        conn.commit()

    conn.close()


def initialize_database():
    create_tables()
    seed_database()


# =========================================================
# المستخدمون
# =========================================================

def add_user(
    telegram_id,
    first_name,
    username
):
    conn = get_connection()
    cursor = conn.cursor()

    cursor.execute(
        """
        INSERT INTO users (
            telegram_id,
            first_name,
            username
        )
        VALUES (?, ?, ?)

        ON CONFLICT(telegram_id)
        DO UPDATE SET
            first_name = excluded.first_name,
            username = excluded.username
        """,
        (
            telegram_id,
            first_name,
            username
        )
    )

    conn.commit()
    conn.close()


def get_all_users():
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT telegram_id
        FROM users
        ORDER BY joined_at
        """
    ).fetchall()

    conn.close()

    return rows


# =========================================================
# المراحل
# =========================================================

def get_stages():
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM stages
        ORDER BY id
        """
    ).fetchall()

    conn.close()

    return rows


def get_stage(stage_id):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM stages
        WHERE id = ?
        """,
        (stage_id,)
    ).fetchone()

    conn.close()

    return row


# =========================================================
# الفصول
# =========================================================

def get_semesters(stage_id):
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM semesters
        WHERE stage_id = ?
        ORDER BY id
        """,
        (stage_id,)
    ).fetchall()

    conn.close()

    return rows


def get_semester(semester_id):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM semesters
        WHERE id = ?
        """,
        (semester_id,)
    ).fetchone()

    conn.close()

    return row


# =========================================================
# المواد
# =========================================================

def get_subjects(semester_id):
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM subjects
        WHERE semester_id = ?
        ORDER BY name_ar
        """,
        (semester_id,)
    ).fetchall()

    conn.close()

    return rows


def get_subject(subject_id):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM subjects
        WHERE id = ?
        """,
        (subject_id,)
    ).fetchone()

    conn.close()

    return row


def add_subject(
    semester_id,
    name_ar,
    name_en
):
    conn = get_connection()
    cursor = conn.cursor()

    try:

        cursor.execute(
            """
            INSERT INTO subjects (
                semester_id,
                name_ar,
                name_en
            )
            VALUES (?, ?, ?)
            """,
            (
                semester_id,
                name_ar,
                name_en
            )
        )

        conn.commit()

        result = True

    except sqlite3.IntegrityError:

        result = False

    conn.close()

    return result


def delete_subject(subject_id):
    conn = get_connection()

    conn.execute(
        """
        DELETE FROM subjects
        WHERE id = ?
        """,
        (subject_id,)
    )

    conn.commit()
    conn.close()


# =========================================================
# الأقسام
# =========================================================

def get_categories():
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM categories
        ORDER BY id
        """
    ).fetchall()

    conn.close()

    return rows


def get_category(category_id):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT *
        FROM categories
        WHERE id = ?
        """,
        (category_id,)
    ).fetchone()

    conn.close()

    return row


# =========================================================
# الملفات
# =========================================================

def add_file(
    subject_id,
    category_id,
    title,
    telegram_file_id,
    telegram_unique_id,
    file_name,
    mime_type,
    uploaded_by
):
    conn = get_connection()

    conn.execute(
        """
        INSERT INTO files (
            subject_id,
            category_id,
            title,
            telegram_file_id,
            telegram_unique_id,
            file_name,
            mime_type,
            uploaded_by
        )
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """,
        (
            subject_id,
            category_id,
            title,
            telegram_file_id,
            telegram_unique_id,
            file_name,
            mime_type,
            uploaded_by
        )
    )

    conn.commit()
    conn.close()


def get_files(
    subject_id,
    category_id
):
    conn = get_connection()

    rows = conn.execute(
        """
        SELECT *
        FROM files

        WHERE subject_id = ?
        AND category_id = ?

        ORDER BY created_at DESC
        """,
        (
            subject_id,
            category_id
        )
    ).fetchall()

    conn.close()

    return rows


def get_file_record(file_db_id):
    conn = get_connection()

    row = conn.execute(
        """
        SELECT
            files.*,

            subjects.name_ar AS subject_name,

            categories.name_ar AS category_name

        FROM files

        JOIN subjects
        ON subjects.id = files.subject_id

        JOIN categories
        ON categories.id = files.category_id

        WHERE files.id = ?
        """,
        (file_db_id,)
    ).fetchone()

    conn.close()

    return row


def delete_file(file_db_id):
    conn = get_connection()

    conn.execute(
        """
        DELETE FROM files
        WHERE id = ?
        """,
        (file_db_id,)
    )

    conn.commit()
    conn.close()


def rename_file(
    file_db_id,
    new_title
):
    conn = get_connection()

    conn.execute(
        """
        UPDATE files
        SET title = ?
        WHERE id = ?
        """,
        (
            new_title,
            file_db_id
        )
    )

    conn.commit()
    conn.close()


def search_files(search_text):
    conn = get_connection()

    search = f"%{search_text}%"

    rows = conn.execute(
        """
        SELECT
            files.*,

            subjects.name_ar AS subject_name,

            categories.name_ar AS category_name

        FROM files

        JOIN subjects
        ON subjects.id = files.subject_id

        JOIN categories
        ON categories.id = files.category_id

        WHERE files.title LIKE ?
        OR files.file_name LIKE ?
        OR subjects.name_ar LIKE ?
        OR subjects.name_en LIKE ?

        ORDER BY files.created_at DESC

        LIMIT 25
        """,
        (
            search,
            search,
            search,
            search
        )
    ).fetchall()

    conn.close()

    return rows


# =========================================================
# الإحصائيات
# =========================================================

def get_statistics():
    conn = get_connection()

    users_count = conn.execute(
        "SELECT COUNT(*) FROM users"
    ).fetchone()[0]

    subjects_count = conn.execute(
        "SELECT COUNT(*) FROM subjects"
    ).fetchone()[0]

    files_count = conn.execute(
        "SELECT COUNT(*) FROM files"
    ).fetchone()[0]

    conn.close()

    return {
        "users": users_count,
        "subjects": subjects_count,
        "files": files_count,
    }