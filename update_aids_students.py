import os
from database import get_db_connection

final_year_aids_students = [
    ("1", "ABHISHEK GAYAKWAD", "0545AD231001", "4th Year (AI-DS)", "active"),
    ("2", "AMIT KUMAR PAWAR", "0545AD231002", "4th Year (AI-DS)", "active"),
    ("3", "ANSH KHANDARE", "0545AD231003", "4th Year (AI-DS)", "active"),
    ("4", "ANUSH VERMA", "0545AD231004", "4th Year (AI-DS)", "active"),
    ("5", "DISHA PANKAR", "0545AD231005", "4th Year (AI-DS)", "active"),
    ("6", "HARSHITA MOTWANI", "0545AD231007", "4th Year (AI-DS)", "active"),
    ("8", "JAY TIWARI", "0545AD231009", "4th Year (AI-DS)", "active"),
    ("9", "MOHIT MALVIYA", "0545AD231010", "4th Year (AI-DS)", "active"),
    ("10", "NANDANI MOTWANI", "0545AD231011", "4th Year (AI-DS)", "active"),
    ("11", "NISHITA BARDE", "0545AD231012", "4th Year (AI-DS)", "active"),
    ("13", "RUPESH FARKADE", "0545AD231014", "4th Year (AI-DS)", "active"),
    ("14", "SHWETA BARASKAR", "0545AD231015", "4th Year (AI-DS)", "active"),
    ("15", "VISHAL SABLE", "0545AD231016", "4th Year (AI-DS)", "active"),
    ("16", "YACHIKA RANE", "0545AD231017", "4th Year (AI-DS)", "active"),
    ("18", "YOGESH SAHU", "0545AD231019", "4th Year (AI-DS)", "active"),
    ("19", "ARCHANA", "0545AD243D01", "4th Year (AI-DS)", "active"),
    ("21", "TANUPRIYA", "0545AD243D04", "4th Year (AI-DS)", "active"),
    ("22", "GITANJALI NARWARE", "0863IS231017", "4th Year (AI-DS)", "active"),
]

third_year_aids_students = [
    ("1", "AASTHA MALVIYA", "0545AD241002", "3rd Year (AI-DS)", "active"),
    ("2", "ANANYA SHARMA", "0545AD241003", "3rd Year (AI-DS)", "active"),
    ("3", "ANJALI KAUSHIK", "0545AD241004", "3rd Year (AI-DS)", "active"),
    ("4", "ARNAV GUPTA", "0545AD241005", "3rd Year (AI-DS)", "active"),
    ("5", "CHANDNI BAMNEY", "0545AD241008", "3rd Year (AI-DS)", "active"),
    ("6", "DIVYANKA BOBADE", "0545AD241009", "3rd Year (AI-DS)", "active"),
    ("7", "GAUTAM RATHORE", "0545AD241011", "3rd Year (AI-DS)", "active"),
    ("8", "GUNJAN AMARGHADE", "0545AD241012", "3rd Year (AI-DS)", "active"),
    ("9", "HARSHIT KUMAR KHATARKAR", "0545AD241014", "3rd Year (AI-DS)", "active"),
    ("10", "HARSHIT LOKHANDE", "0545AD241015", "3rd Year (AI-DS)", "active"),
    ("11", "HARSHIT MAKODE", "0545AD241016", "3rd Year (AI-DS)", "active"),
    ("12", "KANAKNANDANI GANGARE", "0545AD241017", "3rd Year (AI-DS)", "active"),
    ("13", "KHUSHBOO PINJARE", "0545AD241019", "3rd Year (AI-DS)", "active"),
    ("14", "KRISH GHORSE", "0545AD241020", "3rd Year (AI-DS)", "active"),
    ("15", "KRISHNAKANT LILHORE", "0545AD241021", "3rd Year (AI-DS)", "active"),
    ("16", "LAXMI AMRUTE", "0545AD241023", "3rd Year (AI-DS)", "active"),
    ("17", "MAYANK HAJARE", "0545AD241024", "3rd Year (AI-DS)", "active"),
    ("18", "MAYUR GIRHARE", "0545AD241025", "3rd Year (AI-DS)", "active"),
    ("19", "PRACHI KAWDETI", "0545AD241029", "3rd Year (AI-DS)", "active"),
    ("20", "PRAVESH CHAURASIYA", "0545AD241030", "3rd Year (AI-DS)", "active"),
    ("21", "PRAVIN PARIHAR", "0545AD241031", "3rd Year (AI-DS)", "active"),
    ("22", "ROSHNEE CHOUHAN", "0545AD241032", "3rd Year (AI-DS)", "active"),
    ("23", "SWATI CHOURSE", "0545AD241034", "3rd Year (AI-DS)", "active"),
    ("24", "YASH DESHMUKH", "0545AD241035", "3rd Year (AI-DS)", "active"),
    ("25", "YASHRAJ PAL", "0545AD241036", "3rd Year (AI-DS)", "active"),
    ("26", "TARUN PUNDE", "0545EX241011", "3rd Year (AI-DS)", "active"),
    ("27", "AATIF SHEKH", "0545ME241001", "3rd Year (AI-DS)", "active"),
    ("28", "YASH RATHORE", "0545AD231018", "3rd Year (AI-DS)", "active"),
]

def update_aids_students():
    conn = get_db_connection()
    cur = conn.cursor()
    
    # 1. Clear old 4th Year (AI-DS) and 3rd Year (AI-DS) students to cleanly insert the official list
    print("Updating 4th Year (AI-DS) students...")
    cur.execute("DELETE FROM students WHERE year = '4th Year (AI-DS)'")
    cur.executemany("""
        INSERT INTO students (roll_no, name, enrollment_no, year, status)
        VALUES (?, ?, ?, ?, ?)
    """, final_year_aids_students)
    print(f"Successfully inserted {len(final_year_aids_students)} official 4th Year (AI-DS) students!")
    
    print("\nUpdating 3rd Year (AI-DS) students...")
    cur.execute("DELETE FROM students WHERE year = '3rd Year (AI-DS)'")
    cur.executemany("""
        INSERT INTO students (roll_no, name, enrollment_no, year, status)
        VALUES (?, ?, ?, ?, ?)
    """, third_year_aids_students)
    print(f"Successfully inserted {len(third_year_aids_students)} official 3rd Year (AI-DS) students!")
    
    # Update AI-DS V Sem subjects year to '3rd Year (AI-DS)' so they load the 28 students
    cur.execute("""
        UPDATE subjects 
        SET year = '3rd Year (AI-DS)' 
        WHERE department = 'AI-DS' AND semester = 'V'
    """)
    print("Updated AI-DS 5th Semester subjects to '3rd Year (AI-DS)'!")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    update_aids_students()
