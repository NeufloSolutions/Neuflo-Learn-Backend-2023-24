import psycopg2
from psycopg2 import pool
import random
import redis
import json
from Backend.config import DB_CONFIG

# Initialize the connection pool
connection_pool = pool.SimpleConnectionPool(1, 10, **DB_CONFIG)

if connection_pool.closed:
    print("Failed to create the connection pool")

# Initialize Redis client
redis_client = redis.Redis(host='localhost', port=6379, db=0)

def create_connection():
    try:
        return connection_pool.getconn()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        return None


def get_cached_questions(student_id):
    cached_data = redis_client.get(str(student_id))
    if cached_data:
        return json.loads(cached_data)
    else:
        return {}


def cache_questions(student_id, used_questions):
    redis_client.set(str(student_id), json.dumps(used_questions))

def generate_practice_test(student_id):
    conn = create_connection()
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
        # Release the connection back to the pool
        if conn:
            connection_pool.putconn(conn)


def get_practice_test_question_ids(practice_test_id):
    conn = create_connection()
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
        # Release the connection back to the pool
        if conn:
            connection_pool.putconn(conn)


def get_question_details(question_id):
    conn = create_connection()
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT Q.Question, Q.OptionA, Q.OptionB, Q.OptionC, Q.OptionD, I.ImageURL, I.ContentType
                FROM Questions Q
                LEFT JOIN Images I ON Q.QuestionID = I.QuestionID
                WHERE Q.QuestionID = %s AND (I.ContentType IS NULL OR I.ContentType IN ('QUE', 'OptionA', 'OptionB', 'OptionC', 'OptionD'))
            """, (question_id,))
            questions = cur.fetchall()

            result = {}
            for q in questions:
                if not result:
                    result = {"Question": q[0], "Options": {"A": q[1], "B": q[2], "C": q[3], "D": q[4]}, "Images": []}
                if q[5]:
                    result["Images"].append({"URL": q[5], "Type": q[6]})
            return result, None
    except Exception as e:
        return None, str(e)
    finally:
        # Release the connection back to the pool
        if conn:
            connection_pool.putconn(conn)

def get_answer(question_id):
    conn = create_connection()
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT Q.Answer, Q.Explanation, I.ImageURL
                FROM Questions Q
                LEFT JOIN Images I ON Q.QuestionID = I.QuestionID AND I.ContentType = 'EXP'
                WHERE Q.QuestionID = %s
            """, (question_id,))
            result = cur.fetchone()
            if result:
                answer, explanation, image_url = result
                return {"Answer": answer, "Explanation": explanation, "ImageURL": image_url}, None
            else:
                return None, "Question not found"
    except Exception as e:
        return None, str(e)
    finally:
        # Release the connection back to the pool
        if conn:
            connection_pool.putconn(conn)

def get_test_answers_only(testid):
    conn = create_connection()
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT Q.Answer
                FROM Questions Q
                JOIN PracticeTestQuestions PTQ ON Q.QuestionID = PTQ.QuestionID
                WHERE PTQ.PracticeTestID = %s
            """, (testid,))
            
            results = cur.fetchall()
            if results:
                # Extracting just the answers from the query results
                answers = [result[0] for result in results]
                return answers, None
            else:
                return None, "No answers found for the given test ID"
    except Exception as e:
        return None, str(e)
    finally:
        # Release the connection back to the pool
        if conn:
            connection_pool.putconn(conn)


def submit_practice_test_answers(student_id, test_id, answers):
    conn = create_connection()
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
        # Release the connection back to the pool
        if conn:
            connection_pool.putconn(conn)






def calculate_test_results(student_id, test_instance_id):
    conn = create_connection()
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            # Get the test type and test ID for the test instance
            cur.execute("""
                SELECT TestType, TestID
                FROM TestInstances
                WHERE TestInstanceID = %s
            """, (test_instance_id,))
            test_instance_data = cur.fetchone()
            if test_instance_data:
                test_type, test_id = test_instance_data
            else:
                return None, "Test instance not found"

            # Depending on the test type, join the appropriate questions table
            question_table = "PracticeTestQuestions" if test_type == "Practice" else "NEETMockTestQuestions"
            # Query to get the student responses and the correct answers
            cur.execute(f"""
                SELECT SR.StudentResponse, Q.Answer, SR.AnsweringTimeInSeconds, SR.responsedate   
                FROM StudentResponses SR
                JOIN {question_table} PTQ ON SR.QuestionID = PTQ.QuestionID AND SR.TestInstanceID = PTQ.PracticeTestID
                JOIN Questions Q ON PTQ.QuestionID = Q.QuestionID
                WHERE SR.StudentID = %s AND SR.TestInstanceID = %s
            """, (student_id, test_instance_id))

            responses = cur.fetchall()
            correct_answers = 0
            incorrect_answers = 0
            total_answering_time = 0
            last_test_datetime = None

            for student_response, answer, answering_time, response_date in responses:
                student_response = student_response.lower() if student_response else ''
                answer = answer.lower() if answer else ''

                # Print statements for debugging (can be removed in production)
                print(f"Student Answer: {student_response}\t\tActual Answer: {answer}")

                # Treat 'na' as always correct, or check if the student's response matches any of the correct answers
                if answer == 'na':
                    correct_answers += 1
                elif ',' in answer:
                    # If the answer contains multiple choices, split and check
                    if student_response in [choice.strip() for choice in answer.split(',')]:
                        correct_answers += 1
                    else:
                        incorrect_answers += 1
                else:
                    # For single option answers
                    if student_response == answer:
                        correct_answers += 1
                    else:
                        incorrect_answers += 1

                # Sum up answering time for each question
                total_answering_time += answering_time if answering_time else 0

                # Update last_test_datetime if the current response_date is more recent
                if last_test_datetime is None or response_date > last_test_datetime:
                    last_test_datetime = response_date

            # Calculate average answering time
            avg_answering_time = total_answering_time / len(responses) if responses else None
            questions_attempted = len(responses)
            score = correct_answers * 4 - incorrect_answers  # Modify as per your scoring logic


            # Insert into TestHistory table
            cur.execute("""
                INSERT INTO TestHistory (TestInstanceID, StudentID, Score, QuestionsAttempted, CorrectAnswers, IncorrectAnswers, AverageAnsweringTimeInSeconds)
                VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (test_instance_id, student_id, score, questions_attempted, correct_answers, incorrect_answers, avg_answering_time))

            print("Updating Proficiency Tables")
            # Update ChapterProficiency and SubtopicProficiency
            update_proficiency_tables(cur, student_id, test_instance_id)
            print("Updating Practice Test Tables")
            # Update PracticeTestProficiency
            update_practice_test_proficiency(cur, student_id, score, correct_answers, incorrect_answers, avg_answering_time, last_test_datetime)
            return {
                "score": score,
                "correct_answers": correct_answers,
                "incorrect_answers": incorrect_answers,
                "average_answering_time": avg_answering_time,
                "last_test_datetime": last_test_datetime 
            }, None
    except Exception as e:
        print("Entered Exception - Rollback")
        conn.rollback()
        return None, str(e)
    finally:
        if conn:
            connection_pool.putconn(conn)





def update_proficiency_tables(cur, student_id, test_instance_id):
    # Fetch all questions along with student responses for the test instance
    cur.execute("""
        SELECT Q.ChapterID, Q.SubtopicID, SR.StudentResponse, Q.Answer
        FROM StudentResponses SR
        JOIN Questions Q ON SR.QuestionID = Q.QuestionID
        WHERE SR.StudentID = %s AND SR.TestInstanceID = %s
    """, (student_id, test_instance_id))

    results = cur.fetchall()

    # Dictionaries to store correct and incorrect counts for chapters and subtopics
    chapter_correct_counts = {}
    chapter_incorrect_counts = {}
    subtopic_correct_counts = {}
    subtopic_incorrect_counts = {}

    # Process each question's response
    for chapter_id, subtopic_id, student_response, correct_answer in results:
        # Comparing responses case-insensitively
        is_correct = student_response.lower() == correct_answer.lower() if isinstance(student_response, str) and isinstance(correct_answer, str) else student_response == correct_answer

        chapter_correct_counts.setdefault(chapter_id, 0)
        chapter_incorrect_counts.setdefault(chapter_id, 0)
        subtopic_correct_counts.setdefault(subtopic_id, 0)
        subtopic_incorrect_counts.setdefault(subtopic_id, 0)

        if is_correct:
            chapter_correct_counts[chapter_id] += 1
            if subtopic_id:
                subtopic_correct_counts[subtopic_id] += 1
        else:
            chapter_incorrect_counts[chapter_id] += 1
            if subtopic_id:
                subtopic_incorrect_counts[subtopic_id] += 1

    # Update proficiency for each chapter
    for chapter_id in chapter_correct_counts:
        correct_count = chapter_correct_counts[chapter_id]
        incorrect_count = chapter_incorrect_counts[chapter_id]
        update_proficiency(cur, student_id, chapter_id, correct_count, incorrect_count, 'ChapterProficiency')

    # Update proficiency for each subtopic
    for subtopic_id, correct_count in subtopic_correct_counts.items():
        incorrect_count = subtopic_incorrect_counts[subtopic_id]
        if subtopic_id:  # Ensure subtopic_id is not None
            update_proficiency(cur, student_id, subtopic_id, correct_count, incorrect_count, 'SubtopicProficiency')



def update_proficiency(cur, student_id, item_id, correct_answers, incorrect_answers, table_name):
    # SQL to update proficiency
    update_sql = f"""
        INSERT INTO {table_name} (StudentID, {('ChapterID' if table_name == 'ChapterProficiency' else 'SubtopicID')}, CorrectAnswers, IncorrectAnswers)
        VALUES (%s, %s, %s, %s)
        ON CONFLICT (StudentID, {('ChapterID' if table_name == 'ChapterProficiency' else 'SubtopicID')})
        DO UPDATE SET CorrectAnswers = {table_name}.CorrectAnswers + EXCLUDED.CorrectAnswers,
                      IncorrectAnswers = {table_name}.IncorrectAnswers + EXCLUDED.IncorrectAnswers
    """
    # Execute the query with appropriate values
    cur.execute(update_sql, (student_id, item_id, correct_answers, incorrect_answers))


def update_practice_test_proficiency(cur, student_id, score, correct_answers, incorrect_answers, avg_answering_time, last_test_datetime):
    # Fetch the most recent test data for the student from PracticeTestProficiency
    cur.execute("""
        SELECT AverageScore, AverageCorrectAnswers, AverageIncorrectAnswers, AverageAnsweringTimeInSeconds
        FROM PracticeTestProficiency
        WHERE StudentID = %s
        ORDER BY LastResponseDate DESC
        LIMIT 1
    """, (student_id,))

    result = cur.fetchone()

    # Handling NULL values
    avg_answering_time = avg_answering_time or 60  # Set default if None

    # Calculate new averages based on the last test and the current test
    if result:
        (prev_avg_score, prev_avg_correct, prev_avg_incorrect, prev_avg_time) = result

        # Ensure values are floats for arithmetic operations
        prev_avg_score = float(prev_avg_score) if prev_avg_score is not None else 0
        prev_avg_correct = float(prev_avg_correct) if prev_avg_correct is not None else 0
        prev_avg_incorrect = float(prev_avg_incorrect) if prev_avg_incorrect is not None else 0
        prev_avg_time = float(prev_avg_time) if prev_avg_time is not None else 0

        new_avg_score = (prev_avg_score + score) / 2
        new_avg_correct = (prev_avg_correct + correct_answers) / 2
        new_avg_incorrect = (prev_avg_incorrect + incorrect_answers) / 2
        new_avg_time = (prev_avg_time + avg_answering_time) / 2 if prev_avg_time is not None else avg_answering_time

        # Update the record with new averages and LastResponseDate
        cur.execute("""
            UPDATE PracticeTestProficiency
            SET AverageScore = %s, AverageCorrectAnswers = %s, AverageIncorrectAnswers = %s, 
                AverageAnsweringTimeInSeconds = %s, LastResponseDate = %s
            WHERE StudentID = %s
        """, (new_avg_score, new_avg_correct, new_avg_incorrect, new_avg_time, last_test_datetime, student_id))
    else:
        # Insert a new record if no existing record is found
        cur.execute("""
            INSERT INTO PracticeTestProficiency (StudentID, AverageScore, AverageCorrectAnswers, AverageIncorrectAnswers, AverageAnsweringTimeInSeconds, TotalTestsTaken, LastResponseDate)
            VALUES (%s, %s, %s, %s, %s, 1, %s)
        """, (student_id, score, correct_answers, incorrect_answers, avg_answearing_time, last_test_datetime))


def get_student_test_history(student_id):
    conn = create_connection()
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
        # Release the connection back to the pool
        if conn:
            connection_pool.putconn(conn)



def get_chapter_proficiency(student_id):
    conn = create_connection()
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            # Join with all chapters to include those without proficiency records
            cur.execute("""
                SELECT C.ChapterTitle, 
                       COALESCE(CP.CorrectAnswers, 0) AS CorrectAnswers, 
                       COALESCE(CP.IncorrectAnswers, 0) AS IncorrectAnswers
                FROM Chapters C
                LEFT JOIN ChapterProficiency CP ON C.ChapterID = CP.ChapterID AND CP.StudentID = %s
            """, (student_id,))
            proficiency = cur.fetchall()
            return proficiency, None
    except Exception as e:
        return None, str(e)
    finally:
        # Release the connection back to the pool
        if conn:
            connection_pool.putconn(conn)


def get_subtopic_proficiency(student_id):
    conn = create_connection()
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            # Join with all subtopics to include those without proficiency records
            cur.execute("""
                SELECT S.SubtopicName, 
                       COALESCE(SP.CorrectAnswers, 0) AS CorrectAnswers, 
                       COALESCE(SP.IncorrectAnswers, 0) AS IncorrectAnswers
                FROM Subtopics S
                LEFT JOIN SubtopicProficiency SP ON S.SubtopicID = SP.SubtopicID AND SP.StudentID = %s
            """, (student_id,))
            proficiency = cur.fetchall()
            return proficiency, None
    except Exception as e:
        return None, str(e)
    finally:
        # Release the connection back to the pool
        if conn:
            connection_pool.putconn(conn)
