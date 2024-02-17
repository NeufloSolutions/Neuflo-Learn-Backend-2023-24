import logging
from datetime import datetime
from Backend.dbconfig.db_connection import create_pg_connection, release_pg_connection, pg_connection_pool

def get_student_test_history(student_id):
    """
    Retrieve the test history of a student along with average correct and incorrect answers for each subject (Physics, Chemistry, Biology).
    Biology is considered as both Botany and Zoology together.
    """
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return None, "Database connection failed"

    subject_averages = {
        "Physics": {"AverageCorrect": 0, "AverageIncorrect": 0},
        "Chemistry": {"AverageCorrect": 0, "AverageIncorrect": 0},
        "Biology": {"AverageCorrect": 0, "AverageIncorrect": 0}  # Botany and Zoology together
    }

    try:
        with conn.cursor() as cur:
            # Fetch test history
            cur.execute("""
                SELECT TI.TestInstanceID, TI.TestType, TI.TestID, TH.Score, TH.QuestionsAttempted, 
                       TH.CorrectAnswers, TH.IncorrectAnswers, 
                       TH.AverageAnsweringTimeInSeconds, TI.TestDateTime
                FROM TestInstances TI
                JOIN TestHistory TH ON TI.TestInstanceID = TH.TestInstanceID
                WHERE TI.StudentID = %s
            """, (student_id,))
            history = cur.fetchall()
            formatted_history = [{
                "test_instance_id": row[0],
                "test_type": row[1],
                "test_id": row[2],
                "score": row[3],
                "questions_attempted": row[4],
                "correct_answers": row[5],
                "incorrect_answers": row[6],
                "average_answering_time_in_seconds": row[7],
                "test_date_time": row[8]
            } for row in history]

            # Calculate average correct and incorrect answers for Physics, Chemistry, and Biology (Botany + Zoology)
            subject_ids = {"Physics": 1, "Chemistry": 2, "Biology": [3, 4]}  # Map subject names to IDs, Biology includes both Botany and Zoology
            for subject, ids in subject_ids.items():
                if isinstance(ids, list):  # Handle Biology
                    placeholders = ','.join(['%s'] * len(ids))
                    query = f"""
                        SELECT AVG(SR.AnswerCorrect::int) AS AverageCorrect, AVG((NOT SR.AnswerCorrect)::int) AS AverageIncorrect
                        FROM StudentResponses SR
                        JOIN Questions Q ON SR.QuestionID = Q.QuestionID
                        JOIN Chapters C ON Q.ChapterID = C.ChapterID
                        WHERE SR.StudentID = %s AND C.SubjectID IN ({placeholders}) AND SR.AnswerCorrect IS NOT NULL
                    """
                    cur.execute(query, (student_id, *ids))
                else:  # Handle Physics and Chemistry
                    cur.execute("""
                        SELECT AVG(SR.AnswerCorrect::int) AS AverageCorrect, AVG((NOT SR.AnswerCorrect)::int) AS AverageIncorrect
                        FROM StudentResponses SR
                        JOIN Questions Q ON SR.QuestionID = Q.QuestionID
                        JOIN Chapters C ON Q.ChapterID = C.ChapterID
                        WHERE SR.StudentID = %s AND C.SubjectID = %s AND SR.AnswerCorrect IS NOT NULL
                    """, (student_id, ids))
                
                avg_result = cur.fetchone()
                if avg_result:
                    # Update averages with fetched results
                    subject_averages[subject]["AverageCorrect"] = float(avg_result[0] or 0) * 100  # Convert to percentage
                    subject_averages[subject]["AverageIncorrect"] = float(avg_result[1] or 0) * 100  # Convert to percentage

        # Integration of calculate_chapterwise_report
        chapterwise_report = calculate_chapterwise_report(student_id)
        if "error" in chapterwise_report:
            return None, "Error retrieving chapterwise report: " + chapterwise_report["error"]

        # Combine the test history and chapterwise report in the return value
        return {"history": formatted_history, "averages": subject_averages, "chapterwise_report": chapterwise_report}, None

    except Exception as e:
        return None, "Error retrieving student test history: " + str(e)
    finally:
        release_pg_connection(pg_connection_pool, conn)

def calculate_chapterwise_report(student_id: int):
    conn = create_pg_connection(pg_connection_pool)
    if conn is None:
        logging.error("Database connection failed")
        return {"error": "Database connection failed"}

    report = {}
    try:
        cursor = conn.cursor()
        query = """
        SELECT CASE WHEN s.SubjectName IN ('Botany', 'Zoology') THEN 'Biology' ELSE s.SubjectName END AS SubjectName, 
               c.ChapterTitle,
               SUM(CASE WHEN sr.AnswerCorrect THEN 1 ELSE 0 END) as CorrectAnswers,
               SUM(CASE WHEN NOT sr.AnswerCorrect THEN 1 ELSE 0 END) as IncorrectAnswers,
               COUNT(sr.AnswerCorrect) as TotalQuestions
        FROM StudentResponses sr
        INNER JOIN Questions q ON sr.QuestionID = q.QuestionID
        INNER JOIN Chapters c ON q.ChapterID = c.ChapterID
        INNER JOIN Subjects s ON c.SubjectID = s.SubjectID
        WHERE sr.StudentID = %s AND sr.AnswerCorrect IS NOT NULL
        GROUP BY CASE WHEN s.SubjectName IN ('Botany', 'Zoology') THEN 'Biology' ELSE s.SubjectName END, c.ChapterTitle
        """
        cursor.execute(query, (student_id,))
        results = cursor.fetchall()

        logging.info("Query results: %s", results)

        for subject_name, chapter_title, correct_answers, incorrect_answers, total_questions in results:
            percent_correct = (correct_answers / total_questions) * 100
            percent_incorrect = (incorrect_answers / total_questions) * 100

            logging.info("Chapter: %s, Correct: %s, Incorrect: %s", chapter_title, percent_correct, percent_incorrect)

            if subject_name not in report:
                report[subject_name] = {"Strengths": {}, "Weakness": {}}

            # Instead of deciding based on higher percent_correct, add both strengths and weaknesses
            report[subject_name]["Strengths"][chapter_title] = round(percent_correct, 2)
            report[subject_name]["Weakness"][chapter_title] = round(percent_incorrect, 2)

        # Sort strengths and weaknesses by values
        for subject in report:
            report[subject]["Strengths"] = dict(sorted(report[subject]["Strengths"].items(), key=lambda item: item[1], reverse=True))
            report[subject]["Weakness"] = dict(sorted(report[subject]["Weakness"].items(), key=lambda item: item[1], reverse=True))

    except Exception as e:
        logging.error("An error occurred: %s", e)
        return {"error": str(e)}
    finally:
        release_pg_connection(pg_connection_pool, conn)

    return report



def get_chapter_proficiency(student_id):
    """
    Retrieve the chapter proficiency for a student.
    """
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            cur.execute("""
            SELECT C.ChapterID, C.ChapterTitle, COALESCE(CP.CorrectAnswers, 0) AS CorrectAnswers, 
                COALESCE(CP.IncorrectAnswers, 0) AS IncorrectAnswers
            FROM Chapters C
            LEFT JOIN ChapterProficiency CP ON C.ChapterID = CP.ChapterID AND CP.StudentID = %s
            """, (student_id,))
            proficiency = cur.fetchall()
            return proficiency, None
    except Exception as e:
        return None, str(e)
    finally:
        release_pg_connection(pg_connection_pool, conn)

def get_subtopic_proficiency(student_id):
    """
    Retrieve the subtopic proficiency for a student.
    """
    conn = create_pg_connection(pg_connection_pool)
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
        release_pg_connection(pg_connection_pool, conn)

def set_student_target_score(student_id, target_score):
    """
    Adds or updates a student's target score in the StudentTestTargets table.
    If the student already exists, it updates their TargetScore, SetDate, and sets FinishedFirstWeek to True.

    :param student_id: ID of the student.
    :param target_score: The target score to be set for the student.
    """
    conn = create_pg_connection(pg_connection_pool)
    if conn is None:
        print("Failed to obtain database connection.")
        return False

    try:
        with conn.cursor() as cur:
            # SQL statement to insert or update student's target score
            sql = """
            INSERT INTO StudentTestTargets (StudentID, TargetScore, FinishedFirstWeek, SetDate)
            VALUES (%s, %s, TRUE, CURRENT_TIMESTAMP)
            ON CONFLICT (StudentID) DO UPDATE
            SET TargetScore = EXCLUDED.TargetScore,
                FinishedFirstWeek = EXCLUDED.FinishedFirstWeek,
                SetDate = EXCLUDED.SetDate;
            """
            cur.execute(sql, (student_id, target_score))
            conn.commit()
            print("Student's target score has been set successfully.")
            return True
    except Exception as e:
        print(f"An error occurred while setting the student's target score: {e}")
        conn.rollback()
        return False
    finally:
        release_pg_connection(pg_connection_pool, conn)