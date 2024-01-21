import random
from Backend.dbconfig.db_connection import create_pg_connection, release_pg_connection, pg_connection_pool
from Backend.dbconfig.cache_management import get_cached_questions, cache_questions

def fetch_chapters(cur, subject_id):
    cur.execute("SELECT ChapterID FROM Chapters WHERE SubjectID = %s", (subject_id,))
    return [chapter[0] for chapter in cur.fetchall()]

def generate_practice_test(student_id):
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            # Generate a random 4 or 5 digit integer for PracticeTestID
            practice_test_id = random.randint(1000, 99999)

            cur.execute("INSERT INTO PracticeTests (PracticeTestID, StudentID) VALUES (%s, %s) RETURNING PracticeTestID", (practice_test_id, student_id,))
            # Ensure that the practice_test_id is actually inserted
            assert cur.fetchone()[0] == practice_test_id

            subjects = {
                1: {"name": "Physics", "total_questions": 30},
                2: {"name": "Chemistry", "total_questions": 30},
                3: {"name": "Biology", "total_questions": 30}
            }

            used_questions = get_cached_questions(student_id)
            if not isinstance(used_questions, dict):
                used_questions = {}

            for subject_id, details in subjects.items():
                chapters = fetch_chapters(cur, subject_id)
                questions = select_questions(cur, chapters, used_questions, details["total_questions"], subject_id)

                cur.execute("""
                    INSERT INTO PracticeTestSubjects (PracticeTestID, SubjectName)
                    VALUES (%s, %s) RETURNING PracticeTestSubjectID
                """, (practice_test_id, details["name"]))
                subject_test_id = cur.fetchone()[0]

                for question_id in questions:
                    cur.execute("""
                        INSERT INTO PracticeTestQuestions (PracticeTestSubjectID, QuestionID)
                        VALUES (%s, %s)
                    """, (subject_test_id, question_id))

            cache_questions(student_id, used_questions)

            # Generate a random 4 or 5 digit integer for TestInstanceID
            test_instance_id = random.randint(1000, 99999)

            # Insert into TestInstances with the generated TestInstanceID
            cur.execute("""
                INSERT INTO TestInstances (TestInstanceID, StudentID, TestID, TestType)
                VALUES (%s, %s, %s, 'Practice') RETURNING TestInstanceID
            """, (test_instance_id, student_id, practice_test_id))
            assert cur.fetchone()[0] == test_instance_id

            conn.commit()
            return {"testInstanceID": test_instance_id, "subject_tests": subjects}, None
    except Exception as e:
        conn.rollback()
        return None, str(e)
    finally:
        release_pg_connection(pg_connection_pool, conn)

def select_questions(cur, chapters, used_questions, total_questions, subject_id):
    selected_questions = []
    
    # Gather all available questions from the chapters
    all_questions = []
    for chapter_id in chapters:
        cur.execute("""
            SELECT q.QuestionID 
            FROM Questions q 
            INNER JOIN Chapters c ON q.ChapterID = c.ChapterID 
            WHERE q.ChapterID = %s AND c.SubjectID = %s
        """, (chapter_id, subject_id))
        chapter_questions = [question[0] for question in cur.fetchall()]
        
        # Exclude already used questions
        chapter_questions = [q for q in chapter_questions if q not in used_questions.get(chapter_id, [])]
        all_questions.extend(chapter_questions)

    # Randomly select questions ensuring no repetition
    while len(selected_questions) < total_questions and all_questions:
        selected_question = random.choice(all_questions)
        selected_questions.append(selected_question)
        used_questions.setdefault(chapters[0], []).append(selected_question)  # Assign to the first chapter in used_questions
        all_questions.remove(selected_question)

    random.shuffle(selected_questions)
    return selected_questions[:total_questions]

def get_practice_test_question_ids(test_instance_id, student_id):
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            # First, retrieve the PracticeTestID from the TestInstances table
            cur.execute("""
                SELECT TestID
                FROM TestInstances
                WHERE TestInstanceID = %s AND StudentID = %s AND TestType = 'Practice'
            """, (test_instance_id, student_id))
            
            result = cur.fetchone()
            if result is None:
                return None, "Test instance not found or not a practice test."

            practice_test_id = result[0]

            # Now, fetch the questions associated with the practice test
            cur.execute("""
                SELECT PTS.SubjectName, Q.QuestionID
                FROM Questions Q
                JOIN PracticeTestQuestions PTQ ON Q.QuestionID = PTQ.QuestionID
                JOIN PracticeTestSubjects PTS ON PTQ.PracticeTestSubjectID = PTS.PracticeTestSubjectID
                JOIN PracticeTests PT ON PTS.PracticeTestID = PT.PracticeTestID
                WHERE PT.PracticeTestID = %s AND PT.StudentID = %s
            """, (practice_test_id, student_id))

            subject_questions = {}
            for subject_name, question_id in cur.fetchall():
                if subject_name not in subject_questions:
                    subject_questions[subject_name] = []
                subject_questions[subject_name].append(question_id)
            return subject_questions, None
    except Exception as e:
        return None, str(e)
    finally:
        release_pg_connection(pg_connection_pool, conn)


def submit_practice_test_answers(student_id, testInstanceID, subject_ID, answers):
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return "Database connection failed"

    subject_mapping = {1: 'Physics', 2: 'Chemistry', 3: 'Biology'}
    subject_id = subject_mapping.get(subject_ID)

    if subject_id is None:
        return None, "Invalid subject name"

    try:
        with conn.cursor() as cur:
            # Retrieve TestID (which is the PracticeTestID) related to TestInstanceID
            cur.execute("""
                SELECT TestID FROM TestInstances
                WHERE TestInstanceID = %s
            """, (testInstanceID,))
            practice_test_result = cur.fetchone()
            if practice_test_result is None:
                return None, "Practice test not found"

            practice_test_id = practice_test_result[0]

            # Retrieve PracticeTestSubjectID for the subject test
            cur.execute("""
                SELECT PracticeTestSubjectID FROM PracticeTestSubjects
                WHERE PracticeTestID = %s AND SubjectName = %s
            """, (practice_test_id, subject_id))
            subject_test_result = cur.fetchone()
            if subject_test_result is None:
                return None, "Subject test not found"

            subject_test_id = subject_test_result[0]

            # Record each student response using TestInstanceID (test_id)
            for question_id, response in answers.items():
                answering_time = response.get('time', 60)
                student_response = response.get('answer', '')

                cur.execute("""
                    INSERT INTO StudentResponses (TestInstanceID, StudentID, QuestionID, StudentResponse, AnsweringTimeInSeconds)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (TestInstanceID, StudentID, QuestionID)
                    DO UPDATE SET 
                        StudentResponse = EXCLUDED.StudentResponse,
                        AnsweringTimeInSeconds = EXCLUDED.AnsweringTimeInSeconds,
                        ResponseDate = CURRENT_TIMESTAMP
                """, (practice_test_id, student_id, question_id, student_response, answering_time))

            # Mark subject test as completed
            cur.execute("""
                UPDATE PracticeTestSubjects
                SET IsCompleted = TRUE
                WHERE PracticeTestSubjectID = %s
            """, (subject_test_id,))

            # Check if all subject tests are completed
            cur.execute("""
                SELECT COUNT(*) FROM PracticeTestSubjects
                WHERE PracticeTestID= %s AND IsCompleted = FALSE
                        """, (practice_test_id,))
            remaining_tests = cur.fetchone()[0]
            if remaining_tests == 0:
                # Mark full practice test as completed
                cur.execute("""
                    INSERT INTO PracticeTestCompletion (PracticeTestID, StudentID, IsCompleted, CompletionDate)
                    VALUES (%s, %s, TRUE, CURRENT_TIMESTAMP)
                    ON CONFLICT (PracticeTestID, StudentID)
                    DO UPDATE SET 
                        IsCompleted = TRUE,
                        CompletionDate = CURRENT_TIMESTAMP
                """, (practice_test_id, student_id))

            conn.commit()
            return {"message": "Submission successful"}
    except Exception as e:
        conn.rollback()
        return None, str(e)
    finally:
        release_pg_connection(pg_connection_pool, conn)
