import os
from database import get_db_connection

second_year_aids_students = [
    ("1", "AADITYA UGHADE", "0545AD251001", "2nd Year (AI-DS)", "active"),
    ("2", "AMAN PAL", "0545AD251002", "2nd Year (AI-DS)", "active"),
    ("3", "ANJALI SABLE", "0545AD251003", "2nd Year (AI-DS)", "active"),
    ("4", "ANURAG NARWARE", "0545AD251004", "2nd Year (AI-DS)", "active"),
    ("5", "ARYAN VISHWAKARMA", "0545AD251005", "2nd Year (AI-DS)", "active"),
    ("6", "AYAN ALI SHAH", "0545AD251006", "2nd Year (AI-DS)", "active"),
    ("7", "AYUSH KALMBE", "0545AD251007", "2nd Year (AI-DS)", "active"),
    ("8", "BHAGYASHRI SOLANKI", "0545AD251008", "2nd Year (AI-DS)", "active"),
    ("9", "BHUMIKA DIWAN", "0545AD251009", "2nd Year (AI-DS)", "active"),
    ("10", "DHANSHREE NAGORE", "0545AD251010", "2nd Year (AI-DS)", "active"),
    ("11", "DIVYA NAIK", "0545AD251011", "2nd Year (AI-DS)", "active"),
    ("12", "DIVYANSHA DHOTE", "0545AD251012", "2nd Year (AI-DS)", "active"),
    ("13", "DIVYANSHI DIWAN", "0545AD251013", "2nd Year (AI-DS)", "active"),
    ("14", "GAURAV RATHORE", "0545AD251014", "2nd Year (AI-DS)", "active"),
    ("15", "GEETANJALI PAWAR", "0545AD251015", "2nd Year (AI-DS)", "active"),
    ("16", "GOURAV BOBADE", "0545AD251016", "2nd Year (AI-DS)", "active"),
    ("17", "HARSH DANDHODE", "0545AD251017", "2nd Year (AI-DS)", "active"),
    ("18", "HARSH DHAKAD", "0545AD251018", "2nd Year (AI-DS)", "active"),
    ("19", "HARSH MISHRA", "0545AD251019", "2nd Year (AI-DS)", "active"),
    ("20", "JATIN KAVRETI", "0545AD251020", "2nd Year (AI-DS)", "active"),
    ("21", "JAY DHADSE", "0545AD251021", "2nd Year (AI-DS)", "active"),
    ("22", "JAYA VERMA", "0545AD251022", "2nd Year (AI-DS)", "active"),
    ("23", "KEERTI DAVANDEY", "0545AD251023", "2nd Year (AI-DS)", "active"),
    ("24", "KRISHTI PAWAR", "0545AD251024", "2nd Year (AI-DS)", "active"),
    ("25", "LALIT THAKRE", "0545AD251025", "2nd Year (AI-DS)", "active"),
    ("26", "LASHIKA SURYAWANSHI", "0545AD251026", "2nd Year (AI-DS)", "active"),
    ("27", "LOVELESH MAHATE", "0545AD251027", "2nd Year (AI-DS)", "active"),
    ("28", "MAHIMA JAIN", "0545AD251028", "2nd Year (AI-DS)", "active"),
    ("29", "MO REHAN KHAN", "0545AD251029", "2nd Year (AI-DS)", "active"),
    ("30", "NANDANI", "0545AD251030", "2nd Year (AI-DS)", "active"),
    ("31", "NAVIN GHORSE", "0545AD251031", "2nd Year (AI-DS)", "active"),
    ("32", "NEHA SONI", "0545AD251032", "2nd Year (AI-DS)", "active"),
    ("33", "PAYAL DHOLE", "0545AD251033", "2nd Year (AI-DS)", "active"),
    ("34", "PRACHI GAWANDE", "0545AD251034", "2nd Year (AI-DS)", "active"),
    ("35", "PRANJAL SABLE", "0545AD251035", "2nd Year (AI-DS)", "active"),
    ("36", "PRIYANSH DHOTE", "0545AD251036", "2nd Year (AI-DS)", "active"),
    ("37", "RAJESHVARI YADAV", "0545AD251037", "2nd Year (AI-DS)", "active"),
    ("38", "RISHABH DHOTE", "0545AD251038", "2nd Year (AI-DS)", "active"),
    ("39", "RITESH PARIHAR", "0545AD251039", "2nd Year (AI-DS)", "active"),
    ("40", "RIYA VARATHE", "0545AD251040", "2nd Year (AI-DS)", "active"),
    ("41", "SAMEER MAGARDE", "0545AD251041", "2nd Year (AI-DS)", "active"),
    ("42", "SATYADEEP VISHWAKARMA", "0545AD251042", "2nd Year (AI-DS)", "active"),
    ("43", "SHEKH REHAN", "0545AD251043", "2nd Year (AI-DS)", "active"),
    ("44", "SHRIOM SAHU", "0545AD251044", "2nd Year (AI-DS)", "active"),
    ("45", "SHUBHAM KAPSE", "0545AD251045", "2nd Year (AI-DS)", "active"),
    ("46", "TANUL YADAV", "0545AD251046", "2nd Year (AI-DS)", "active"),
    ("47", "YASH SAHU", "0545AD251047", "2nd Year (AI-DS)", "active"),
    ("48", "YATI PAWAR", "0545AD251048", "2nd Year (AI-DS)", "active"),
    ("49", "YUSHI LOKHANDE", "0545AD251049", "2nd Year (AI-DS)", "active"),
]

def update_2nd_year_aids():
    conn = get_db_connection()
    cur = conn.cursor()
    
    print("Inserting 2nd Year (AI-DS) official students...")
    cur.execute("DELETE FROM students WHERE year = '2nd Year (AI-DS)'")
    cur.executemany("""
        INSERT INTO students (roll_no, name, enrollment_no, year, status)
        VALUES (?, ?, ?, ?, ?)
    """, second_year_aids_students)
    print(f"Successfully added {len(second_year_aids_students)} students for 2nd Year (AI-DS)!")
    
    # Update AI-DS 3rd Sem subjects year to '2nd Year (AI-DS)'
    cur.execute("""
        UPDATE subjects 
        SET year = '2nd Year (AI-DS)' 
        WHERE department = 'AI-DS' AND semester = 'III'
    """)
    print("Updated AI-DS 3rd Semester subjects to '2nd Year (AI-DS)'!")
    
    conn.commit()
    conn.close()

if __name__ == '__main__':
    update_2nd_year_aids()
