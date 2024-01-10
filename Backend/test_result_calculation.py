from db_connection import create_pg_connection, release_pg_connection

def calculate_test_results(student_id, test_instance_id):
    """
    Calculate the results for a given test instance of a student.
    """
    conn = create_pg_connection()
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            # Retrieve test type and ID
            cur.execute("""
                SELECT TestType, TestID
                FROM TestInstances
                WHERE TestInstanceID = %s
            """, (test_instance_id,))
            test_instance_data = cur.fetchone()
            if not test_instance_data:
                return None, "Test instance not found"

            test_type, test_id = test_instance_data
            question_table = "PracticeTestQuestions" if test_type == "Practice" else "NEETMockTestQuestions"

            # Retrieve student responses and correct answers
            cur.execute(f"""
                SELECT SR.StudentResponse, Q.Answer, SR.AnsweringTimeInSeconds   
                FROM StudentResponses SR
                JOIN {question_table} PTQ ON SR.QuestionID = PTQ.QuestionID AND SR.TestInstanceID = PTQ.PracticeTestID
                JOIN Questions Q ON PTQ.QuestionID = Q.QuestionID
                WHERE SR.StudentID = %s AND SR.TestInstanceID = %s
            """, (student_id, test_instance_id))

            responses = cur.fetchall()
            correct_answers = 0
            incorrect_answers = 0
            total_answering_time = 0

            for student_response, answer, answering_time in responses:
                is_correct = student_response.lower() == answer.lower()
                if is_correct:
                    correct_answers += 1
                else:
                    incorrect_answers += 1
                total_answering_time += answering_time if answering_time else 0

            avg_answering_time = total_answering_time / len(responses) if responses else 0
            score = correct_answers * 4 - incorrect_answers  # Modify scoring logic as needed

            # Update proficiency tables
            update_proficiency_tables(cur, student_id, test_instance_id)
            return {
                "score": score,
                "correct_answers": correct_answers,
                "incorrect_answers": incorrect_answers,
                "average_answering_time": avg_answering_time
            }, None
    except Exception as e:
        conn.rollback()
        return None, str(e)
    finally:
        release_pg_connection(conn)


def update_proficiency_tables(cur, student_id, test_instance_id):
    """
    Update proficiency tables based on the test results.
    """
    # Fetch all questions along with student responses
    cur.execute("""
        SELECT Q.ChapterID, Q.SubtopicID, SR.StudentResponse, Q.Answer
        FROM StudentResponses SR
        JOIN Questions Q ON SR.QuestionID = Q.QuestionID
        WHERE SR.StudentID = %s AND SR.TestInstanceID = %s
    """, (student_id, test_instance_id))

    for chapter_id, subtopic_id, student_response, correct_answer in cur.fetchall():
        is_correct = student_response.lower() == correct_answer.lower()
        update_proficiency(cur, student_id, chapter_id, is_correct, 'ChapterProficiency')
        if subtopic_id:
            update_proficiency(cur, student_id, subtopic_id, is_correct, 'SubtopicProficiency')


def update_proficiency(cur, student_id, item_id, is_correct, table_name):
    """
    Update the proficiency record for a student in a given table.
    """
    field_name = 'ChapterID' if table_name == 'ChapterProficiency' else 'SubtopicID'
    correct_field = 'CorrectAnswers' if is_correct else 'IncorrectAnswers'
    cur.execute(f"""
        INSERT INTO {table_name} (StudentID, {field_name}, {correct_field})
        VALUES (%s, %s, 1)
        ON CONFLICT (StudentID, {field_name})
        DO UPDATE SET {correct_field} = {table_name}.{correct_field} + 1
    """, (student_id, item_id))


def update_practice_test_proficiency(cur, student_id, score, correct_answers, incorrect_answers, avg_answering_time):
    """
    Update proficiency records based on the results of a practice test.
    """
    # Fetch existing record, if any
    cur.execute("""
        SELECT AverageScore, AverageCorrectAnswers, AverageIncorrectAnswers, AverageAnsweringTimeInSeconds, TotalTestsTaken
        FROM PracticeTestProficiency
        WHERE StudentID = %s
    """, (student_id,))

    result = cur.fetchone()
    if result:
        prev_avg_score, prev_avg_correct, prev_avg_incorrect, prev_avg_time, total_tests = result
        new_avg_score = (prev_avg_score * total_tests + score) / (total_tests + 1)
        new_avg_correct = (prev_avg_correct * total_tests + correct_answers) / (total_tests + 1)
        new_avg_incorrect = (prev_avg_incorrect * total_tests + incorrect_answers) / (total_tests + 1)
        new_avg_time = (prev_avg_time * total_tests + avg_answering_time) / (total_tests + 1)

        cur.execute("""
            UPDATE PracticeTestProficiency
            SET AverageScore = %s, AverageCorrectAnswers = %s, AverageIncorrectAnswers = %s, 
                AverageAnsweringTimeInSeconds = %s, TotalTestsTaken = TotalTestsTaken + 1
            WHERE StudentID = %s
        """, (new_avg_score, new_avg_correct, new_avg_incorrect, new_avg_time, student_id))
    else:
        cur.execute("""
            INSERT INTO PracticeTestProficiency (StudentID, AverageScore, AverageCorrectAnswers, AverageIncorrectAnswers, AverageAnsweringTimeInSeconds, TotalTestsTaken)
            VALUES (%s, %s, %s, %s, %s, 1)
        """, (student_id, score, correct_answers, incorrect_answers, avg_answearing_time))
