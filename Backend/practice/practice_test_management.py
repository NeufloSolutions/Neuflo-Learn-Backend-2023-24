import random
from psycopg2 import DatabaseError
from Backend.dbconfig.db_connection import create_pg_connection, release_pg_connection, pg_connection_pool
from Backend.dbconfig.cache_management import get_cached_questions, cache_questions

def fetch_chapters(cur, subject_id):
    print(f"Fetching chapters for subject ID: {subject_id}")
    cur.execute("""
        SELECT ChapterID 
        FROM Chapters 
        WHERE SubjectID = %s AND IsActive = TRUE
    """, (subject_id,))
    chapters = [chapter[0] for chapter in cur.fetchall()]
    print(f"Found chapters: {chapters}")
    return chapters

def generate_practice_test(student_id):
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            practice_test_id = random.randint(1000, 99999)
            print(f"Generated PracticeTestID: {practice_test_id}")

            cur.execute("INSERT INTO PracticeTests (PracticeTestID, StudentID) VALUES (%s, %s) RETURNING PracticeTestID", (practice_test_id, student_id,))
            # Ensure that the practice_test_id is actually inserted
            assert cur.fetchone()[0] == practice_test_id

            # Insert a default completion status for the new practice test
            cur.execute("""
                INSERT INTO PracticeTestCompletion (PracticeTestID, StudentID, IsCompleted)
                VALUES (%s, %s, FALSE)
            """, (practice_test_id, student_id,))

            subjects = {
                1: {"name": "Physics", "total_questions": 30},
                2: {"name": "Chemistry", "total_questions": 30},
                3: {"name": "Biology", "total_questions": 30}
            }

            print("Before getting cached questions")
            used_questions = get_cached_questions(student_id, "practice")
            print(f"Used questions from cache: {used_questions}")

            if not isinstance(used_questions, list):
                used_questions = []

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
                    if question_id not in used_questions:
                        used_questions.append(question_id)

            print("Before Caching")
            cache_questions(student_id, "practice", used_questions)
            print("After Caching")

            test_instance_id = random.randint(1000, 99999)
            cur.execute("""
                INSERT INTO TestInstances (TestInstanceID, StudentID, TestID, TestType)
                VALUES (%s, %s, %s, 'Practice') RETURNING TestInstanceID
            """, (test_instance_id, student_id, practice_test_id,))
            assert cur.fetchone()[0] == test_instance_id

            conn.commit()
            print("Practice test generated successfully")
            return {"testInstanceID": test_instance_id, "subject_tests": subjects}, None
    except Exception as e:
        conn.rollback()
        return None, str(e)
    finally:
        release_pg_connection(pg_connection_pool, conn)

def get_practice_test_details(instance_id: int, student_id: int):
    # Initialize the connection variable
    conn = None
    
    try:
        # Use the create_pg_connection function to get a connection from the pool
        conn = create_pg_connection(pg_connection_pool)
        cur = conn.cursor()
        
        # Corrected SQL query with the proper column name 'IsCompleted'
        sql = """
        SELECT ti.TestInstanceID, pts.SubjectName, pts.IsCompleted
        FROM TestInstances ti
        JOIN PracticeTestSubjects pts ON ti.TestID = pts.PracticeTestID
        WHERE ti.TestInstanceID = %s AND ti.StudentID = %s;
        """
        # Execute the query
        cur.execute(sql, (instance_id, student_id))
        # Fetch the results
        results = cur.fetchall()
        
        # Format the results into the desired JSON structure
        subjects_status = [
            {"testinstanceid": row[0], "subjectname": row[1], "iscompleted": row[2]}
            for row in results
        ]
        # Close the cursor
        cur.close()
        return subjects_status
    
    except (Exception, DatabaseError) as error:
        print(f"Error: {error}")
        return []
    finally:
        # Ensure the connection is released back to the pool regardless of success or error
        if conn is not None:
            release_pg_connection(pg_connection_pool, conn)

def select_questions(cur, chapters, used_questions, total_questions, subject_id):
    selected_questions = []
    
    # Gather all available questions from the active chapters and their active subtopics
    all_questions = []
    for chapter_id in chapters:
        # Select questions from the chapters where the corresponding subtopics are active or if there is no subtopic associated with the question
        cur.execute("""
            SELECT q.QuestionID 
            FROM Questions q 
            INNER JOIN Chapters c ON q.ChapterID = c.ChapterID
            LEFT JOIN Subtopics s ON q.SubtopicID = s.SubtopicID
            WHERE q.ChapterID = %s AND c.SubjectID = %s AND c.IsActive = TRUE
            AND (s.IsActive IS TRUE OR q.SubtopicID IS NULL)
        """, (chapter_id, subject_id))
        chapter_questions = [question[0] for question in cur.fetchall()]
        
        # Exclude already used questions
        chapter_questions = [q for q in chapter_questions if q not in used_questions]
        all_questions.extend(chapter_questions)

    # Randomly select questions ensuring no repetition
    while len(selected_questions) < total_questions and all_questions:
        selected_question = random.choice(all_questions)
        if selected_question not in selected_questions: # Ensure uniqueness in selection
            selected_questions.append(selected_question)
            all_questions.remove(selected_question)

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

def get_practice_test_questions(test_instance_id, student_id):
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
                # For each question ID, fetch question details
                cur.execute("""
                    SELECT Q.Question, Q.OptionA, Q.OptionB, Q.OptionC, Q.OptionD, I.ImageURL, I.ContentType
                    FROM Questions Q
                    LEFT JOIN Images I ON Q.QuestionID = I.QuestionID
                    WHERE Q.QuestionID = %s
                """, (question_id,))
                questions = cur.fetchall()

                question_details = {}
                for q in questions:
                    if not question_details:
                        question_details = {"Question": q[0], "Options": {"A": q[1], "B": q[2], "C": q[3], "D": q[4]}, "Images": []}
                    if q[5] and q[6] in ['QUE', 'OptionA', 'OptionB', 'OptionC', 'OptionD']:
                        question_details["Images"].append({"URL": q[5], "Type": q[6]})

                if subject_name not in subject_questions:
                    subject_questions[subject_name] = []
                subject_questions[subject_name].append(question_details)
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
    print("Subject ID Name: ", subject_id)

    if subject_id is None:
        return "Invalid subject ID"

    try:
        with conn.cursor() as cur:
            # Retrieve TestID (which is the PracticeTestID) related to TestInstanceID
            cur.execute("""
                SELECT TestID FROM TestInstances
                WHERE TestInstanceID = %s
            """, (testInstanceID,))
            practice_test_result = cur.fetchone()
            if practice_test_result is None:
                return "Practice test not found"

            practice_test_id = practice_test_result[0]

            # Retrieve PracticeTestSubjectID for the subject test
            cur.execute("""
                SELECT PracticeTestSubjectID FROM PracticeTestSubjects
                WHERE PracticeTestID = %s AND SubjectName = %s
            """, (practice_test_id, subject_id))
            subject_test_result = cur.fetchone()
            if subject_test_result is None:
                return "Subject test not found"

            subject_test_id = subject_test_result[0]

            for question_id, response in answers.items():
                answering_time = response.get('time', 60)
                student_response = response.get('answer', '')

                # Retrieve the correct answer for the question
                cur.execute("""
                    SELECT Answer FROM Questions
                    WHERE QuestionID = %s
                """, (question_id,))
                correct_answer_result = cur.fetchone()
                if correct_answer_result is None:
                    continue  # Skip if question not found
                correct_answer = correct_answer_result[0]

                # Determine if the answer is correct
                answer_correct = (student_response.lower() == correct_answer.lower())

                # Record the student response along with correctness
                cur.execute("""
                    INSERT INTO StudentResponses (TestInstanceID, StudentID, QuestionID, StudentResponse, AnsweringTimeInSeconds, AnswerCorrect)
                    VALUES (%s, %s, %s, %s, %s, %s)
                    ON CONFLICT (TestInstanceID, StudentID, QuestionID)
                    DO UPDATE SET 
                        StudentResponse = EXCLUDED.StudentResponse,
                        AnsweringTimeInSeconds = EXCLUDED.AnsweringTimeInSeconds,
                        AnswerCorrect = EXCLUDED.AnswerCorrect,
                        ResponseDate = CURRENT_TIMESTAMP
                """, (testInstanceID, student_id, question_id, student_response, answering_time, answer_correct))

            # Mark subject test as completed
            cur.execute("""
                UPDATE PracticeTestSubjects
                SET IsCompleted = TRUE
                WHERE PracticeTestSubjectID = %s
            """, (subject_test_id,))

            # Check if all subject tests are completed for the practice test
            cur.execute("""
                SELECT COUNT(*) FROM PracticeTestSubjects
                WHERE PracticeTestID = %s AND IsCompleted = FALSE
            """, (practice_test_id,))
            remaining_tests = cur.fetchone()[0]
            if remaining_tests == 0:
                # Mark the full practice test as completed
                cur.execute("""
                    INSERT INTO PracticeTestCompletion (PracticeTestID, StudentID, IsCompleted, CompletionDate)
                    VALUES (%s, %s, TRUE, CURRENT_TIMESTAMP)
                    ON CONFLICT (PracticeTestID, StudentID)
                    DO UPDATE SET 
                        IsCompleted = TRUE,
                        CompletionDate = CURRENT_TIMESTAMP
                """, (practice_test_id, student_id))

            conn.commit()
            return {"message": "Answers submitted successfully."}
    except Exception as e:
        conn.rollback()
        return "Error submitting answers: " + str(e)
    finally:
        if conn:
            release_pg_connection(pg_connection_pool, conn)

