import sqlite3
import os
import shutil
from datetime import datetime, timedelta
from werkzeug.security import generate_password_hash

# Handle Vercel serverless read-only filesystem by copying to /tmp if deployed on Vercel
if os.environ.get('VERCEL'):
    TMP_DB_PATH = '/tmp/attendance.db'
    SRC_DB_PATH = os.path.join(os.path.dirname(__file__), 'attendance.db')
    if not os.path.exists(TMP_DB_PATH):
        if os.path.exists(SRC_DB_PATH):
            shutil.copy2(SRC_DB_PATH, TMP_DB_PATH)
    DB_PATH = TMP_DB_PATH
else:
    DB_PATH = os.path.join(os.path.dirname(__file__), 'attendance.db')

def get_db_connection():
    conn = sqlite3.connect(DB_PATH, timeout=30.0, check_same_thread=False)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA journal_mode = WAL;")
        conn.execute("PRAGMA busy_timeout = 30000;")
    except Exception:
        pass
    return conn

def init_db():
    conn = get_db_connection()
    cursor = conn.cursor()

    # Enable foreign keys
    cursor.execute("PRAGMA foreign_keys = ON;")

    # 1. Faculty Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS faculty (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        name TEXT NOT NULL,
        email TEXT UNIQUE NOT NULL,
        phone TEXT,
        assigned_year TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 2. Users Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS users (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        username TEXT UNIQUE NOT NULL,
        password_hash TEXT NOT NULL,
        role TEXT NOT NULL CHECK(role IN ('admin', 'faculty')),
        faculty_id INTEGER,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE CASCADE
    );
    """)

    # 3. Students Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS students (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        roll_no TEXT NOT NULL,
        name TEXT NOT NULL,
        enrollment_no TEXT,
        year TEXT NOT NULL,
        status TEXT NOT NULL DEFAULT 'active' CHECK(status IN ('active', 'inactive')),
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        UNIQUE(roll_no, year)
    );
    """)

    # 4. Holidays Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS holidays (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        date TEXT UNIQUE NOT NULL,
        reason TEXT NOT NULL,
        created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
    );
    """)

    # 5. Attendance Master Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        year TEXT NOT NULL,
        date TEXT NOT NULL,
        faculty_id INTEGER,
        submitted_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
        status TEXT DEFAULT 'submitted',
        UNIQUE(year, date),
        FOREIGN KEY (faculty_id) REFERENCES faculty(id) ON DELETE SET NULL
    );
    """)

    # 6. Attendance Records Table
    cursor.execute("""
    CREATE TABLE IF NOT EXISTS attendance_records (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        attendance_id INTEGER NOT NULL,
        student_id INTEGER NOT NULL,
        status TEXT NOT NULL CHECK(status IN ('Present', 'Absent')),
        FOREIGN KEY (attendance_id) REFERENCES attendance(id) ON DELETE CASCADE,
        FOREIGN KEY (student_id) REFERENCES students(id) ON DELETE CASCADE,
        UNIQUE(attendance_id, student_id)
    );
    """)

    conn.commit()
    seed_initial_data(conn)
    conn.close()

def seed_initial_data(conn):
    cursor = conn.cursor()

    # Check if admin user exists
    cursor.execute("SELECT id FROM users WHERE role = 'admin'")
    if not cursor.fetchone():
        # Seed Admin
        admin_pass = generate_password_hash('admin123')
        cursor.execute("INSERT INTO users (username, password_hash, role) VALUES (?, ?, ?)",
                       ('admin', admin_pass, 'admin'))

    # Seed 3 Faculty if none exist
    cursor.execute("SELECT COUNT(*) as count FROM faculty")
    count = cursor.fetchone()['count']
    if count == 0:
        faculties = [
            ("Prof. Ravi Kumar Mohane", "ravi.mohane@college.edu", "9876543210", "2nd Year", "prof.ravi", "ravi123"),
            ("Prof. Khushbu", "khushbu@college.edu", "9876543211", "3rd Year", "prof.khushbu", "khushbu123"),
            ("Prof. Jitendra Barmase", "jitendra.barmase@college.edu", "9876543212", "4th Year", "prof.jitendra", "jitendra123"),
        ]
        for name, email, phone, year, username, password in faculties:
            cursor.execute("INSERT INTO faculty (name, email, phone, assigned_year) VALUES (?, ?, ?, ?)",
                           (name, email, phone, year))
            faculty_id = cursor.lastrowid
            pass_hash = generate_password_hash(password)
            cursor.execute("INSERT INTO users (username, password_hash, role, faculty_id) VALUES (?, ?, ?, ?)",
                           (username, pass_hash, 'faculty', faculty_id))

    # Seed realistic students across 2nd, 3rd, and 4th Years
    cursor.execute("SELECT COUNT(*) as count FROM students")
    if cursor.fetchone()['count'] == 0:
        students_data = [
            # 2nd Year (3rd Sem CSE - 74 Students)
            ("01", "ABHISHEK SAHU", "0545CS251001", "2nd Year (CSE)", "active"),
            ("02", "ADITYA PARIHAR", "0545CS251002", "2nd Year (CSE)", "active"),
            ("03", "AKSHITA MALVIYA", "0545CS251003", "2nd Year (CSE)", "active"),
            ("04", "AMBIKA KHADE", "0545CS251004", "2nd Year (CSE)", "active"),
            ("05", "AMRATA KHADIYA", "0545CS251005", "2nd Year (CSE)", "active"),
            ("06", "ASHVINI BUWADE", "0545CS251007", "2nd Year (CSE)", "active"),
            ("07", "BHAVESH PAL", "0545CS251008", "2nd Year (CSE)", "active"),
            ("08", "BHAVIKA SOMANI", "0545CS251009", "2nd Year (CSE)", "active"),
            ("09", "CHANDAN GANGARE", "0545CS251010", "2nd Year (CSE)", "active"),
            ("10", "CHINMAY SOMANI", "0545CS251011", "2nd Year (CSE)", "active"),
            ("11", "DAKSH RATHORE", "0545CS251012", "2nd Year (CSE)", "active"),
            ("12", "DEEP PAWAR", "0545CS251013", "2nd Year (CSE)", "active"),
            ("13", "DEVIKA", "0545CS251014", "2nd Year (CSE)", "active"),
            ("14", "DIKSHA PATNE", "0545CS251015", "2nd Year (CSE)", "active"),
            ("15", "DIVYA KALE", "0545CS251016", "2nd Year (CSE)", "active"),
            ("16", "DURLABH UIKE", "0545CS251017", "2nd Year (CSE)", "active"),
            ("17", "GAURAV KALE", "0545CS251018", "2nd Year (CSE)", "active"),
            ("18", "HARDIK PALERIYA", "0545CS251019", "2nd Year (CSE)", "active"),
            ("19", "HARSH SINGH GAUTAM", "0545CS251020", "2nd Year (CSE)", "active"),
            ("20", "HASMITA PATHEKAR", "0545CS251021", "2nd Year (CSE)", "active"),
            ("21", "HIMANSHI RATHORE", "0545CS251022", "2nd Year (CSE)", "active"),
            ("22", "HIMANSHI SONPURE", "0545CS251023", "2nd Year (CSE)", "active"),
            ("23", "HINA KIRODE", "0545CS251025", "2nd Year (CSE)", "active"),
            ("24", "JATIN SONI", "0545CS251026", "2nd Year (CSE)", "active"),
            ("25", "JAY BOKDE", "0545CS251027", "2nd Year (CSE)", "active"),
            ("26", "JAY DHOTE", "0545CS251028", "2nd Year (CSE)", "active"),
            ("27", "KANIKA PAWAR", "0545CS251029", "2nd Year (CSE)", "active"),
            ("28", "KANISHKA VERMA", "0545CS251030", "2nd Year (CSE)", "active"),
            ("29", "KANISHTHA PAWAR", "0545CS251031", "2nd Year (CSE)", "active"),
            ("30", "KHUSHHAL SURYAVANSHI", "0545CS251032", "2nd Year (CSE)", "active"),
            ("31", "KHUSHI BODKHE", "0545CS251033", "2nd Year (CSE)", "active"),
            ("32", "KRATIKA PAL", "0545CS251034", "2nd Year (CSE)", "active"),
            ("33", "KUMKUM DAHARE", "0545CS251035", "2nd Year (CSE)", "active"),
            ("34", "LAKSHITA THAKRE", "0545CS251036", "2nd Year (CSE)", "active"),
            ("35", "LAVISH SONI", "0545CS251037", "2nd Year (CSE)", "active"),
            ("36", "LEESHA BATHRI", "0545CS251038", "2nd Year (CSE)", "active"),
            ("37", "LEKHANI PAWAR", "0545CS251039", "2nd Year (CSE)", "active"),
            ("38", "LOKESH VISHWAKARMA", "0545CS251040", "2nd Year (CSE)", "active"),
            ("39", "MANISHA", "0545CS251041", "2nd Year (CSE)", "active"),
            ("40", "MAYANK SAHU", "0545CS251042", "2nd Year (CSE)", "active"),
            ("41", "MOHIT LAHARPURE", "0545CS251043", "2nd Year (CSE)", "active"),
            ("42", "MONALI DHOTE", "0545CS251044", "2nd Year (CSE)", "active"),
            ("43", "NIKITA RATHORE", "0545CS251045", "2nd Year (CSE)", "active"),
            ("44", "PALAK DARWAI", "0545CS251047", "2nd Year (CSE)", "active"),
            ("45", "PARTH DESHMUKH", "0545CS251048", "2nd Year (CSE)", "active"),
            ("46", "PRAGATI SAVANE", "0545CS251049", "2nd Year (CSE)", "active"),
            ("47", "PRATYUSH RATHORE", "0545CS251050", "2nd Year (CSE)", "active"),
            ("48", "PRAVEEN MALVIYA", "0545CS251051", "2nd Year (CSE)", "active"),
            ("49", "PUNEET VADUKALE", "0545CS251052", "2nd Year (CSE)", "active"),
            ("50", "RAUNAK KAPSE", "0545CS251053", "2nd Year (CSE)", "active"),
            ("51", "RENU PAWAR", "0545CS251054", "2nd Year (CSE)", "active"),
            ("52", "RUCHIKA PANSE", "0545CS251055", "2nd Year (CSE)", "active"),
            ("53", "SACHIN PRAJAPATI", "0545CS251056", "2nd Year (CSE)", "active"),
            ("54", "SAKSHI BHARADE", "0545CS251057", "2nd Year (CSE)", "active"),
            ("55", "SAVITA KALE", "0545CS251058", "2nd Year (CSE)", "active"),
            ("56", "SHUBHAM BOBADE", "0545CS251060", "2nd Year (CSE)", "active"),
            ("57", "SNEHA KHOBRE", "0545CS251061", "2nd Year (CSE)", "active"),
            ("58", "SUJAL WANJARE", "0545CS251062", "2nd Year (CSE)", "active"),
            ("59", "TEJAS TEKAM", "0545CS251063", "2nd Year (CSE)", "active"),
            ("60", "TULIKA BARASKAR", "0545CS251064", "2nd Year (CSE)", "active"),
            ("61", "VAIBHAVI TOMAR", "0545CS251065", "2nd Year (CSE)", "active"),
            ("62", "VAISHNAVI LIKHITKAR", "0545CS251066", "2nd Year (CSE)", "active"),
            ("63", "VEDANT RATHORE", "0545CS251067", "2nd Year (CSE)", "active"),
            ("64", "VIDHAN BASANTPURE", "0545CS251068", "2nd Year (CSE)", "active"),
            ("65", "VIKAS NARRE", "0545CS251069", "2nd Year (CSE)", "active"),
            ("66", "VISHAKHA PAWAR", "0545CS251070", "2nd Year (CSE)", "active"),
            ("67", "YASH KURAVLE", "0545CS251071", "2nd Year (CSE)", "active"),
            ("68", "YOGITA HIWARKHEDE", "0545CS251072", "2nd Year (CSE)", "active"),
            ("69", "HIMANSHU LOHARE", "0545EX251001", "2nd Year (CSE)", "active"),
            ("70", "KHUSHANK", "0545EX251002", "2nd Year (CSE)", "active"),
            ("71", "RAHUL MAKODE", "0545EX251003", "2nd Year (CSE)", "active"),
            ("72", "RISHABH DENGE", "0545EX251004", "2nd Year (CSE)", "active"),
            ("73", "SHEIKH REHAN", "0545EX251005", "2nd Year (CSE)", "active"),
            ("74", "TARAN YADAV", "0545EX251006", "2nd Year (CSE)", "active"),

            # 3rd Year (5th Sem CSE - 68 Students)
            ("01", "AARTI RANE", "0545CS241002", "3rd Year", "active"),
            ("02", "AASTHA SANDE", "0545CS241003", "3rd Year", "active"),
            ("03", "AAYUSH KASARE", "0545CS241004", "3rd Year", "active"),
            ("04", "ABHISHEK HAJARE", "0545CS241005", "3rd Year", "active"),
            ("05", "AMAN SHIVHARE", "0545CS241007", "3rd Year", "active"),
            ("06", "ANURAG SURYAWANSHI", "0545CS241008", "3rd Year", "active"),
            ("07", "APURVA PARIHAR", "0545CS241009", "3rd Year", "active"),
            ("08", "ARMAAN QURESHI", "0545CS241010", "3rd Year", "active"),
            ("09", "ASMIT PARTE", "0545CS241011", "3rd Year", "active"),
            ("10", "AYUSH YADAV", "0545CS241012", "3rd Year", "active"),
            ("11", "CHAITANYA SAHU", "0545CS241014", "3rd Year", "active"),
            ("12", "CHETANA DHOTE", "0545CS241015", "3rd Year", "active"),
            ("13", "CHHAVI MAKODE", "0545CS241016", "3rd Year", "active"),
            ("14", "DISHA DESHMUKH", "0545CS241017", "3rd Year", "active"),
            ("15", "DIVYANSHU TARUDKAR", "0545CS241018", "3rd Year", "active"),
            ("16", "EKTA DHOTE", "0545CS241019", "3rd Year", "active"),
            ("17", "GAURANG DAHARE", "0545CS241020", "3rd Year", "active"),
            ("18", "GAURAV DAHARE", "0545CS241021", "3rd Year", "active"),
            ("19", "GOUTAM HARSULE", "0545CS241022", "3rd Year", "active"),
            ("20", "HANSIKA NALLOL", "0545CS241023", "3rd Year", "active"),
            ("21", "HARSH YADAV", "0545CS241024", "3rd Year", "active"),
            ("22", "HEMANT MAHALE", "0545CS241025", "3rd Year", "active"),
            ("23", "HIMANSHI UKANDE", "0545CS241026", "3rd Year", "active"),
            ("24", "JIGYASA GAYAKWAD", "0545CS241027", "3rd Year", "active"),
            ("25", "KALAMBE ROHIT PRAMODRAO", "0545CS241028", "3rd Year", "active"),
            ("26", "KAPILKANT LILHORE", "0545CS241029", "3rd Year", "active"),
            ("27", "KRISHNA MALVIYA", "0545CS241030", "3rd Year", "active"),
            ("28", "KUSHAGRA AGRAWAL", "0545CS241031", "3rd Year", "active"),
            ("29", "MAHAK BARASKAR", "0545CS241032", "3rd Year", "active"),
            ("30", "MAHEK RATHORE", "0545CS241033", "3rd Year", "active"),
            ("31", "MAYUR CHODITKAR", "0545CS241034", "3rd Year", "active"),
            ("32", "MITALI SURYAWANSHI", "0545CS241035", "3rd Year", "active"),
            ("33", "MONIKA GAYDHANE", "0545CS241036", "3rd Year", "active"),
            ("34", "MUSKAN HARPODE", "0545CS241037", "3rd Year", "active"),
            ("35", "NEMIT SONI", "0545CS241038", "3rd Year", "active"),
            ("36", "PALAK CHOUHAN", "0545CS241039", "3rd Year", "active"),
            ("37", "PARTE RAJKUMAR SADAN", "0545CS241040", "3rd Year", "active"),
            ("38", "PIYUSH DAYKE", "0545CS241041", "3rd Year", "active"),
            ("39", "PIYUSH PANSE", "0545CS241042", "3rd Year", "active"),
            ("40", "PRACHI GUPTA", "0545CS241043", "3rd Year", "active"),
            ("41", "PRANAV KAWADKAR", "0545CS241044", "3rd Year", "active"),
            ("42", "PRASHANT BARASKAR", "0545CS241045", "3rd Year", "active"),
            ("43", "PRATIKSHA", "0545CS241046", "3rd Year", "active"),
            ("44", "PRINCI PAWAR", "0545CS241047", "3rd Year", "active"),
            ("45", "PRIYANSHI CHOUKSEY", "0545CS241048", "3rd Year", "active"),
            ("46", "RAJ GAJANAN KASLIKAR", "0545CS241049", "3rd Year", "active"),
            ("47", "REHAN ALI", "0545CS241050", "3rd Year", "active"),
            ("48", "RISHITA TAWARE", "0545CS241051", "3rd Year", "active"),
            ("49", "RIYANSHI KOKNE", "0545CS241052", "3rd Year", "active"),
            ("50", "RUDRARAJ WAGH", "0545CS241053", "3rd Year", "active"),
            ("51", "SAKSHAM VERMA", "0545CS241054", "3rd Year", "active"),
            ("52", "SALMAN KHAN", "0545CS241055", "3rd Year", "active"),
            ("53", "SALONI BARANGE", "0545CS241056", "3rd Year", "active"),
            ("54", "SALONI GIRI", "0545CS241057", "3rd Year", "active"),
            ("55", "SANDEEP YADAV", "0545CS241058", "3rd Year", "active"),
            ("56", "SHAIKH MOHD ANAS NAWAZ", "0545CS241059", "3rd Year", "active"),
            ("57", "SHIVAM SAHU", "0545CS241060", "3rd Year", "active"),
            ("58", "SHRASHTI ANGHORE", "0545CS241061", "3rd Year", "active"),
            ("59", "SHUBHAM RAVANDHE", "0545CS241062", "3rd Year", "active"),
            ("60", "SUDEEP BUWADE", "0545CS241064", "3rd Year", "active"),
            ("61", "SUMIT CHOUHAN", "0545CS241065", "3rd Year", "active"),
            ("62", "TUSHAR PAWAR", "0545CS241066", "3rd Year", "active"),
            ("63", "VAISHNAVI SOLANKI", "0545CS241067", "3rd Year", "active"),
            ("64", "VANSHIKA KHANDWE", "0545CS241068", "3rd Year", "active"),
            ("65", "VISHAKHA FARKADE", "0545CS241069", "3rd Year", "active"),
            ("66", "VISHAL KAR", "0545CS241070", "3rd Year", "active"),
            ("67", "VIVEK VERMA", "0545CS241071", "3rd Year", "active"),
            ("68", "YASHIKA DANGE", "0545CS241072", "3rd Year", "active"),

            # 4th Year (7th Sem CSE - 58 Students)
            ("01", "AAKASH PAWAR", "0545CS231001", "4th Year", "active"),
            ("02", "ANJALI MALVIYA", "0545CS231002", "4th Year", "active"),
            ("03", "ANJALI SONI", "0545CS231003", "4th Year", "active"),
            ("04", "ANKIT KUMAR", "0545CS231004", "4th Year", "active"),
            ("05", "ASHVINI GOHITE", "0545CS231005", "4th Year", "active"),
            ("06", "BHARTI BISNURKAR", "0545CS231006", "4th Year", "active"),
            ("07", "BHUVAN YADAV", "0545CS231007", "4th Year", "active"),
            ("08", "DHANSHREE GALPHAT", "0545CS231008", "4th Year", "active"),
            ("09", "DHANSHRI WANKHADE", "0545CS231009", "4th Year", "active"),
            ("10", "DHYANVI RAGHUVANSHI", "0545CS231010", "4th Year", "active"),
            ("11", "DIPANSHU SURYAWANSHI", "0545CS231011", "4th Year", "active"),
            ("12", "DISHA PAWAR", "0545CS231012", "4th Year", "active"),
            ("13", "DIVYANSHI BARPETE", "0545CS231014", "4th Year", "active"),
            ("14", "HARSHAD WANODE", "0545CS231016", "4th Year", "active"),
            ("15", "HIMANSHU CHOUDHARY", "0545CS231017", "4th Year", "active"),
            ("16", "HIMANSHU NAGLE", "0545CS231018", "4th Year", "active"),
            ("17", "JITENDRA NAGVANSHI", "0545CS231019", "4th Year", "active"),
            ("18", "KARAN DONGRE", "0545CS231020", "4th Year", "active"),
            ("19", "KHUSHI WANJARE", "0545CS231021", "4th Year", "active"),
            ("20", "KULDEEP BALPANDE", "0545CS231022", "4th Year", "active"),
            ("21", "KUMKUM PARIHAR", "0545CS231023", "4th Year", "active"),
            ("22", "KUNAL ASREKER", "0545CS231024", "4th Year", "active"),
            ("23", "KUNAL PATWARI", "0545CS231025", "4th Year", "active"),
            ("24", "MEEZA KHAN", "0545CS231026", "4th Year", "active"),
            ("25", "MUSKAN SAHU", "0545CS231027", "4th Year", "active"),
            ("26", "NIKITA BARASKAR", "0545CS231028", "4th Year", "active"),
            ("27", "NISHA", "0545CS231029", "4th Year", "active"),
            ("28", "PAWAN JHAGEKAR", "0545CS231030", "4th Year", "active"),
            ("29", "PAYAL JHADE", "0545CS231031", "4th Year", "active"),
            ("30", "PIYUSH KADU", "0545CS231032", "4th Year", "active"),
            ("31", "PRAYUSH BELE", "0545CS231033", "4th Year", "active"),
            ("32", "PRIYA WANJARE", "0545CS231034", "4th Year", "active"),
            ("33", "PRIYANKA UGHADE", "0545CS231035", "4th Year", "active"),
            ("34", "PRIYANSHU ASHOK PAWAR", "0545CS231036", "4th Year", "active"),
            ("35", "PRIYANSHU RATHORE", "0545CS231037", "4th Year", "active"),
            ("36", "RITIKA MUKESH YADAV", "0545CS231039", "4th Year", "active"),
            ("37", "RITIKA PAL", "0545CS231040", "4th Year", "active"),
            ("38", "ROHAN GHORE", "0545CS231041", "4th Year", "active"),
            ("39", "SAKSHI DESHMUKH", "0545CS231042", "4th Year", "active"),
            ("40", "SAKSHI KUMBHARE", "0545CS231043", "4th Year", "active"),
            # 4th Year (7th Sem CSE - 58 Students)
            ("01", "AAKASH PAWAR", "0545CS231001", "4th Year (CSE)", "active"),
            ("02", "ANJALI MALVIYA", "0545CS231002", "4th Year (CSE)", "active"),
            ("03", "ANJALI SONI", "0545CS231003", "4th Year (CSE)", "active"),
            ("04", "ANKIT KUMAR", "0545CS231004", "4th Year (CSE)", "active"),
            ("05", "ASHVINI GOHITE", "0545CS231005", "4th Year (CSE)", "active"),
            ("06", "BHARTI BISNURKAR", "0545CS231006", "4th Year (CSE)", "active"),
            ("07", "BHUVAN YADAV", "0545CS231007", "4th Year (CSE)", "active"),
            ("08", "DHANSHREE GALPHAT", "0545CS231008", "4th Year (CSE)", "active"),
            ("09", "DHANSHRI WANKHADE", "0545CS231009", "4th Year (CSE)", "active"),
            ("10", "DHYANVI RAGHUVANSHI", "0545CS231010", "4th Year (CSE)", "active"),
            ("11", "DIPANSHU SURYAWANSHI", "0545CS231011", "4th Year (CSE)", "active"),
            ("12", "DISHA PAWAR", "0545CS231012", "4th Year (CSE)", "active"),
            ("13", "DIVYANSHI BARPETE", "0545CS231014", "4th Year (CSE)", "active"),
            ("14", "HARSHAD WANODE", "0545CS231016", "4th Year (CSE)", "active"),
            ("15", "HIMANSHU CHOUDHARY", "0545CS231017", "4th Year (CSE)", "active"),
            ("16", "HIMANSHU NAGLE", "0545CS231018", "4th Year (CSE)", "active"),
            ("17", "JITENDRA NAGVANSHI", "0545CS231019", "4th Year (CSE)", "active"),
            ("18", "KARAN DONGRE", "0545CS231020", "4th Year (CSE)", "active"),
            ("19", "KHUSHI WANJARE", "0545CS231021", "4th Year (CSE)", "active"),
            ("20", "KULDEEP BALPANDE", "0545CS231022", "4th Year (CSE)", "active"),
            ("21", "KUMKUM PARIHAR", "0545CS231023", "4th Year (CSE)", "active"),
            ("22", "KUNAL ASREKER", "0545CS231024", "4th Year (CSE)", "active"),
            ("23", "KUNAL PATWARI", "0545CS231025", "4th Year (CSE)", "active"),
            ("24", "MEEZA KHAN", "0545CS231026", "4th Year (CSE)", "active"),
            ("25", "MUSKAN SAHU", "0545CS231027", "4th Year (CSE)", "active"),
            ("26", "NIKITA BARASKAR", "0545CS231028", "4th Year (CSE)", "active"),
            ("27", "NISHA", "0545CS231029", "4th Year (CSE)", "active"),
            ("28", "PAWAN JHAGEKAR", "0545CS231030", "4th Year (CSE)", "active"),
            ("29", "PAYAL JHADE", "0545CS231031", "4th Year (CSE)", "active"),
            ("30", "PIYUSH KADU", "0545CS231032", "4th Year (CSE)", "active"),
            ("31", "PRAYUSH BELE", "0545CS231033", "4th Year (CSE)", "active"),
            ("32", "PRIYA WANJARE", "0545CS231034", "4th Year (CSE)", "active"),
            ("33", "PRIYANKA UGHADE", "0545CS231035", "4th Year (CSE)", "active"),
            ("34", "PRIYANSHU ASHOK PAWAR", "0545CS231036", "4th Year (CSE)", "active"),
            ("35", "PRIYANSHU RATHORE", "0545CS231037", "4th Year (CSE)", "active"),
            ("36", "RITIKA MUKESH YADAV", "0545CS231039", "4th Year (CSE)", "active"),
            ("37", "RITIKA PAL", "0545CS231040", "4th Year (CSE)", "active"),
            ("38", "ROHAN GHORE", "0545CS231041", "4th Year (CSE)", "active"),
            ("39", "SAKSHI DESHMUKH", "0545CS231042", "4th Year (CSE)", "active"),
            ("40", "SAKSHI KUMBHARE", "0545CS231043", "4th Year (CSE)", "active"),
            ("41", "SEJAL GULHANE", "0545CS231044", "4th Year (CSE)", "active"),
            ("42", "SHIVAM SONI", "0545CS231045", "4th Year (CSE)", "active"),
            ("43", "SHRADDHA DHOTE", "0545CS231046", "4th Year (CSE)", "active"),
            ("44", "SHRADDHA WAGMODE", "0545CS231047", "4th Year (CSE)", "active"),
            ("45", "SHUBHAM SONI", "0545CS231048", "4th Year (CSE)", "active"),
            ("46", "SONIYA DESHMUKH", "0545CS231049", "4th Year (CSE)", "active"),
            ("47", "TARUN PAWAR", "0545CS231050", "4th Year (CSE)", "active"),
            ("48", "THAKRE UTTARA ANIL", "0545CS231051", "4th Year (CSE)", "active"),
            ("49", "TUSHAR SHRIWAS", "0545CS231052", "4th Year (CSE)", "active"),
            ("50", "VIJAY", "0545CS231053", "4th Year (CSE)", "active"),
            ("51", "VIVEK WANJARE", "0545CS231054", "4th Year (CSE)", "active"),
            ("52", "YASH PAWAR", "0545CS231055", "4th Year (CSE)", "active"),
            ("53", "YASHIKA PAWAR", "0545CS231056", "4th Year (CSE)", "active"),
            ("54", "BUWADE GOPAL DILEEP", "0545CS243D01", "4th Year (CSE)", "active"),
            ("55", "CHETAN LONARE", "0545CS243D02", "4th Year (CSE)", "active"),
            ("56", "HITESH PARIHAR", "0545CS243D03", "4th Year (CSE)", "active"),
            ("57", "KHUSHBU LOHARE", "0545CS243D04", "4th Year (CSE)", "active"),
            ("58", "POOJA", "0545CS243D05", "4th Year (CSE)", "active"),

            # 4th Year (7th Sem AI-DS - 23 Students)
            ("01", "ABHISHEK GAYAKWAD", "0545AD231001", "4th Year (AI-DS)", "active"),
            ("02", "AMIT KUMAR PAWAR", "0545AD231002", "4th Year (AI-DS)", "active"),
            ("03", "ANSH KHANDARE", "0545AD231003", "4th Year (AI-DS)", "active"),
            ("04", "ANUSH VERMA", "0545AD231004", "4th Year (AI-DS)", "active"),
            ("05", "DISHA PANKAR", "0545AD231005", "4th Year (AI-DS)", "active"),
            ("06", "HARSHITA MOTWANI", "0545AD231007", "4th Year (AI-DS)", "active"),
            ("07", "HIMANI MANEKAR", "0545AD231008", "4th Year (AI-DS)", "active"),
            ("08", "JAY TIWARI", "0545AD231009", "4th Year (AI-DS)", "active"),
            ("09", "MOHIT MALVIYA", "0545AD231010", "4th Year (AI-DS)", "active"),
            ("10", "NANDANI MOTWANI", "0545AD231011", "4th Year (AI-DS)", "active"),
            ("11", "NISHITA BARDE", "0545AD231012", "4th Year (AI-DS)", "active"),
            ("12", "PARAS BHALAVE", "0545AD231013", "4th Year (AI-DS)", "active"),
            ("13", "RUPESH FARKADE", "0545AD231014", "4th Year (AI-DS)", "active"),
            ("14", "SHWETA BARASKAR", "0545AD231015", "4th Year (AI-DS)", "active"),
            ("15", "VISHAL SABLE", "0545AD231016", "4th Year (AI-DS)", "active"),
            ("16", "YACHIKA RANE", "0545AD231017", "4th Year (AI-DS)", "active"),
            ("17", "YASH RATHORE", "0545AD231018", "4th Year (AI-DS)", "active"),
            ("18", "YOGESH SAHU", "0545AD231019", "4th Year (AI-DS)", "active"),
            ("19", "ARCHANA PAWAR", "0545AD243D01", "4th Year (AI-DS)", "active"),
            ("20", "KAPIL GADGE", "0545AD243D02", "4th Year (AI-DS)", "active"),
            ("21", "NIDHI ALONE", "0545AD243D03", "4th Year (AI-DS)", "active"),
            ("22", "TANUPRIYA CHOUKIKAR", "0545AD243D04", "4th Year (AI-DS)", "active"),
            ("23", "GITANJALI NARWARE", "0863IS231017", "4th Year (AI-DS)", "active"),
        ]
        cursor.executemany("""
        INSERT INTO students (roll_no, name, enrollment_no, year, status)
        VALUES (?, ?, ?, ?, ?)
        """, students_data)

    # Seed sample holidays
    cursor.execute("SELECT COUNT(*) as count FROM holidays")
    if cursor.fetchone()['count'] == 0:
        holidays_data = [
            ("2026-09-05", "Teacher's Day Celebration"),
            ("2026-09-12", "Second Saturday College Holiday"),
            ("2026-08-15", "Independence Day"),
        ]
        cursor.executemany("INSERT OR IGNORE INTO holidays (date, reason) VALUES (?, ?)", holidays_data)

    # Seed historical attendance records for the past 14 days (excluding Sundays & Holidays)
    cursor.execute("SELECT COUNT(*) as count FROM attendance")
    if cursor.fetchone()['count'] == 0:
        cursor.execute("SELECT id, assigned_year FROM faculty")
        faculty_map = {row['assigned_year']: row['id'] for row in cursor.fetchall()}

        # Generate dates for past 10 working days
        today = datetime.now().date()
        date_list = []
        for i in range(1, 15):
            d = today - timedelta(days=i)
            # Exclude Weekends (Saturday=5, Sunday=6 in python)
            if d.weekday() in (5, 6):
                continue
            d_str = d.strftime('%Y-%m-%d')
            # Exclude dates prior to session start (31 Aug 2026)
            if d_str < '2026-08-31':
                continue
            # Exclude holidays
            cursor.execute("SELECT id FROM holidays WHERE date = ?", (d_str,))
            if cursor.fetchone():
                continue
            date_list.append(d_str)

        # Seed attendance from session start (31 Aug 2026) onwards
        for year in ['2nd Year (CSE)', '3rd Year (CSE)', '4th Year (CSE)', '4th Year (AI-DS)']:
            f_id = faculty_map.get(year)
            cursor.execute("SELECT id FROM students WHERE year = ?", (year,))
            studs = cursor.fetchall()
            if not studs:
                continue

            for date_str in date_list[-8:]:  # Seed last 8 working days
                cursor.execute("""
                INSERT INTO attendance (year, date, faculty_id, submitted_at, status)
                VALUES (?, ?, ?, ?, 'submitted')
                """, (year, date_str, f_id, f"{date_str} 09:30:00"))
                att_id = cursor.lastrowid

                # Deterministic pattern for present/absent
                rec_tuples = []
                for s_idx, s in enumerate(studs):
                    is_present = ((s_idx + int(date_str.replace('-', ''))) % 7) != 0
                    rec_tuples.append((att_id, s['id'], 'Present' if is_present else 'Absent'))
                cursor.executemany("INSERT INTO attendance_records (attendance_id, student_id, status) VALUES (?, ?, ?)", rec_tuples)

    conn.commit()

if __name__ == '__main__':
    init_db()
    print("Database initialized and seeded successfully.")
