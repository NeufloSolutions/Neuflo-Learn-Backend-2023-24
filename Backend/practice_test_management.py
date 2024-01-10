import random
from db_connection import create_pg_connection, release_pg_connection
from cache_management import get_cached_questions, cache_questions

def generate_practice_test(student_id):
    conn = create_pg_connection()
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            # Fetch all chapters
            cur.execute("SELECT ChapterID FROM Chapters")
            chapters = [chapter[0] for chapter in cur.fetchall()]

            # Fetch previously used questions for the student from cache
            used_questions = get_cached_questions(student_id)

            practice_test_questions = []
            for chapter_id in chapters:
                # Fetch questions for the chapter
                cur.execute("""
                    SELECT QuestionID, SubtopicID FROM Questions
                    WHERE ChapterID = %s
                """, (chapter_id,))
                chapter_questions = cur.fetchall()

                # Randomize order of questions
                random.shuffle(chapter_questions)
                selected_question = None
                for question_id, subtopic_id in chapter_questions:
                    if subtopic_id not in used_questions.get(chapter_id, {}) or question_id not in used_questions[chapter_id].get(subtopic_id, []):
                        selected_question = question_id
                        used_questions.setdefault(chapter_id, {}).setdefault(subtopic_id, []).append(question_id)
                        break

                if selected_question:
                    practice_test_questions.append(selected_question)

            if not practice_test_questions:
                return None, "No questions available for the practice test"

            # Insert the new practice test
            cur.execute("INSERT INTO PracticeTests (StudentID) VALUES (%s) RETURNING PracticeTestID", (student_id,))
            practice_test_id = cur.fetchone()[0]

            # Link questions to the practice test
            for qid in practice_test_questions:
                cur.execute("INSERT INTO PracticeTestQuestions (PracticeTestID, QuestionID) VALUES (%s, %s)", (practice_test_id, qid))

            # Update the cache with newly used questions
            cache_questions(student_id, used_questions)

            conn.commit()
            return practice_test_id, None
    except Exception as e:
        print("Entered Exception - Rollback")
        conn.rollback()
        return None, str(e)
    finally:
        release_pg_connection(conn)

def get_practice_test_question_ids(practice_test_id):
    conn = create_pg_connection()
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT Q.QuestionID
                FROM Questions Q
                JOIN PracticeTestQuestions PTQ ON Q.QuestionID = PTQ.QuestionID
                WHERE PTQ.PracticeTestID = %s
            """, (practice_test_id,))
            question_ids = [row[0] for row in cur.fetchall()]
            return question_ids, None
    except Exception as e:
        return None, str(e)
    finally:
        release_pg_connection(conn)

def submit_practice_test_answers(student_id, test_id, answers):
    conn = create_pg_connection()
    if not conn:
        return "Database connection failed"

    try:
        with conn.cursor() as cur:
            test_instance_id = None  # Initialize test_instance_id

            # Check if the specific TestInstance already exists
            cur.execute("""
                SELECT TestInstanceID FROM TestInstances
                WHERE TestID = %s AND StudentID = %s AND TestType = %s
            """, (test_id, student_id, 'Practice'))
            fetched = cur.fetchone()

            if fetched:
                test_instance_id = fetched[0]
            else:
                # Insert a new TestInstance
                cur.execute("""
                    INSERT INTO TestInstances (StudentID, TestID, TestType)
                    VALUES (%s, %s, %s)
                    RETURNING TestInstanceID
                """, (student_id, test_id, 'Practice'))
                test_instance_id = cur.fetchone()[0]

            # Ensure test_instance_id is not None before proceeding
            if test_instance_id is None:
                raise Exception("Failed to retrieve or create TestInstanceID.")

            # Now record or update each student response
            for question_id, response in answers.items():
                answering_time = response.get('time', 60)  # Default time to 60 if not provided
                student_response = response.get('answer', '')

                # UPSERT operation: Insert or update the student's response
                cur.execute("""
                    INSERT INTO StudentResponses (TestInstanceID, StudentID, QuestionID, StudentResponse, AnsweringTimeInSeconds)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (TestInstanceID, StudentID, QuestionID)
                    DO UPDATE SET 
                        StudentResponse = EXCLUDED.StudentResponse,
                        AnsweringTimeInSeconds = EXCLUDED.AnsweringTimeInSeconds,
                        ResponseDate = CURRENT_TIMESTAMP
                """, (test_instance_id, student_id, question_id, student_response, answering_time))
            conn.commit()
            return {"message": "Submission successful"}
    except Exception as e:
        print("Entered Exception - Rollback")
        conn.rollback()
        return None, str(e)
    finally:
        release_pg_connection(conn)
