from db_connection import create_pg_connection, release_pg_connection

def get_student_test_history(student_id):
    """
    Retrieve the test history of a student.
    """
    conn = create_pg_connection()
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT TI.TestInstanceID, TI.TestType, TI.TestID, TH.Score, TH.QuestionsAttempted, 
                       TH.CorrectAnswers, TH.IncorrectAnswers, 
                       TH.AverageAnsweringTimeInSeconds, TI.TestDateTime
                FROM TestInstances TI
                JOIN TestHistory TH ON TI.TestInstanceID = TH.TestInstanceID
                WHERE TI.StudentID = %s
            """, (student_id,))
            history = cur.fetchall()
            return history, None
    except Exception as e:
        return None, str(e)
    finally:
        release_pg_connection(conn)

def get_chapter_proficiency(student_id):
    """
    Retrieve the chapter proficiency for a student.
    """
    conn = create_pg_connection()
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT C.ChapterID, C.ChapterName, COALESCE(CP.CorrectAnswers, 0) AS CorrectAnswers, 
                       COALESCE(CP.IncorrectAnswers, 0) AS IncorrectAnswers
                FROM Chapters C
                LEFT JOIN ChapterProficiency CP ON C.ChapterID = CP.ChapterID AND CP.StudentID = %s
            """, (student_id,))
            proficiency = cur.fetchall()
            return proficiency, None
    except Exception as e:
        return None, str(e)
    finally:
        release_pg_connection(conn)

def get_subtopic_proficiency(student_id):
    """
    Retrieve the subtopic proficiency for a student.
    """
    conn = create_pg_connection()
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT S.SubtopicID, S.SubtopicName, COALESCE(SP.CorrectAnswers, 0) AS CorrectAnswers, 
                       COALESCE(SP.IncorrectAnswers, 0) AS IncorrectAnswers
                FROM Subtopics S
                LEFT JOIN SubtopicProficiency SP ON S.SubtopicID = SP.SubtopicID AND SP.StudentID = %s
            """, (student_id,))
            proficiency = cur.fetchall()
            return proficiency, None
    except Exception as e:
        return None, str(e)
    finally:
        release_pg_connection(conn)
