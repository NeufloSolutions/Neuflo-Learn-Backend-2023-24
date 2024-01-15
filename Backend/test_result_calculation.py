from Backend.db_connection import create_pg_connection, release_pg_connection, pg_connection_pool

def calculate_test_results(student_id, test_instance_id):
    conn = create_pg_connection(pg_connection_pool)
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

            # Check if all subjects in a full practice test are completed
            if test_type == "Practice":
                cur.execute("""
                    SELECT IsCompleted
                    FROM PracticeTestCompletion
                    WHERE PracticeTestID = %s AND StudentID = %s
                """, (test_id, student_id))
                completion_data = cur.fetchone()
                if not completion_data or not completion_data[0]:
                    return None, "Please complete all subjects in the practice test before proceeding."


                # Depending on the test type, join the appropriate questions table
                question_table = "PracticeTestQuestions"
            elif test_type == "Mock":
                question_table = "NEETMockTestQuestions"

            # Query to get the student responses and the correct answers
            cur.execute(f"""
                SELECT SR.StudentResponse, Q.Answer, SR.AnsweringTimeInSeconds, SR.ResponseDate
                FROM StudentResponses SR
                JOIN {question_table} PTQ ON SR.QuestionID = PTQ.QuestionID
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

                if answer == 'na':
                    correct_answers += 1
                elif ',' in answer:
                    if student_response in [choice.strip() for choice in answer.split(',')]:
                        correct_answers += 1
                    else:
                        incorrect_answers += 1
                else:
                    if student_response == answer:
                        correct_answers += 1
                    else:
                        incorrect_answers += 1

                total_answering_time += answering_time if answering_time else 0
                if last_test_datetime is None or response_date > last_test_datetime:
                    last_test_datetime = response_date

            avg_answering_time = total_answering_time / len(responses) if responses else None
            questions_attempted = len(responses)
            score = correct_answers * 4 - incorrect_answers  # Modify as per your scoring logic

            # Insert into TestHistory table
            cur.execute("""
                INSERT INTO TestHistory (TestInstanceID, StudentID, Score, QuestionsAttempted, CorrectAnswers, IncorrectAnswers, AverageAnsweringTimeInSeconds, LastTestAttempt)
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (TestInstanceID, StudentID)
                DO UPDATE SET 
                    Score = EXCLUDED.Score, 
                    QuestionsAttempted = EXCLUDED.QuestionsAttempted,
                    CorrectAnswers = EXCLUDED.CorrectAnswers, 
                    IncorrectAnswers = EXCLUDED.IncorrectAnswers, 
                    AverageAnsweringTimeInSeconds = EXCLUDED.AverageAnsweringTimeInSeconds,
                    LastTestAttempt = EXCLUDED.LastTestAttempt;
            """, (test_instance_id, student_id, score, questions_attempted, correct_answers, incorrect_answers, avg_answering_time, last_test_datetime))

            # Update proficiency tables
            print("Updating Proficiency Tables")
            update_proficiency_tables(cur, student_id, test_instance_id)

            # Update the proficiency table specific to the test type
            if test_type == "Practice":
                print("Updating Practice Test Proficiency")
                update_practice_test_proficiency(cur, student_id, score, correct_answers, incorrect_answers, avg_answering_time, last_test_datetime)
            elif test_type == "Mock":
                print("Updating Mock Test Proficiency")
                update_mock_test_proficiency(cur, student_id, score, correct_answers, incorrect_answers, avg_answering_time, last_test_datetime)


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
            conn.commit()
            release_pg_connection(pg_connection_pool, conn)



def update_proficiency_tables(cur, student_id, test_instance_id):
    # Fetch all questions and responses
    cur.execute("""
        SELECT Q.ChapterID, Q.SubtopicID, SR.StudentResponse, Q.Answer
        FROM StudentResponses SR
        JOIN Questions Q ON SR.QuestionID = Q.QuestionID
        WHERE SR.StudentID = %s AND SR.TestInstanceID = %s
    """, (student_id, test_instance_id))

    chapter_proficiency_data = []
    subtopic_proficiency_data = []

    # Aggregate counts
    for chapter_id, subtopic_id, student_response, correct_answer in cur.fetchall():
        is_correct = student_response.lower() == correct_answer.lower()
        chapter_proficiency_data.append((student_id, chapter_id, is_correct))
        subtopic_proficiency_data.append((student_id, subtopic_id, is_correct))

    # Perform bulk update for ChapterProficiency
    update_proficiency_bulk(cur, chapter_proficiency_data, "ChapterProficiency", "ChapterID")
    # Perform bulk update for SubtopicProficiency
    update_proficiency_bulk(cur, subtopic_proficiency_data, "SubtopicProficiency", "SubtopicID")




def update_proficiency_bulk(cur, proficiency_data, table_name, id_column_name):
    # Construct a single query for bulk update
    args_str = ','.join(cur.mogrify("(%s,%s,%s)", (x[0], x[1], x[2])).decode('utf-8') for x in proficiency_data)

    # SQL query to update the specified proficiency table
    cur.execute(f"""
        WITH data(StudentID, ID, IsCorrect) AS (VALUES {args_str}),
        aggregated AS (
            SELECT 
                StudentID, 
                ID, 
                SUM(CASE WHEN IsCorrect THEN 1 ELSE 0 END) AS CorrectAnswers,
                SUM(CASE WHEN IsCorrect THEN 0 ELSE 1 END) AS IncorrectAnswers
            FROM data
            GROUP BY StudentID, ID
        )
        UPDATE {table_name} P
        SET CorrectAnswers = P.CorrectAnswers + agg.CorrectAnswers,
            IncorrectAnswers = P.IncorrectAnswers + agg.IncorrectAnswers
        FROM aggregated agg
        WHERE P.StudentID = agg.StudentID AND P.{id_column_name} = agg.ID;
    """)

    # Repeat the WITH clause for the INSERT statement
    cur.execute(f"""
        WITH data(StudentID, ID, IsCorrect) AS (VALUES {args_str}),
        aggregated AS (
            SELECT 
                StudentID, 
                ID, 
                SUM(CASE WHEN IsCorrect THEN 1 ELSE 0 END) AS CorrectAnswers,
                SUM(CASE WHEN IsCorrect THEN 0 ELSE 1 END) AS IncorrectAnswers
            FROM data
            GROUP BY StudentID, ID
        )
        INSERT INTO {table_name} (StudentID, {id_column_name}, CorrectAnswers, IncorrectAnswers)
        SELECT 
            agg.StudentID, 
            agg.ID, 
            agg.CorrectAnswers,
            agg.IncorrectAnswers
        FROM aggregated agg
        WHERE NOT EXISTS (
            SELECT 1 
            FROM {table_name} P
            WHERE P.StudentID = agg.StudentID AND P.{id_column_name} = agg.ID
        );
    """)


def update_practice_test_proficiency(cur, student_id, score, correct_answers, incorrect_answers, avg_answering_time, last_test_datetime):
    # Define the number of recent tests to consider and the initial weight
    num_recent_tests = 5  # Adjust this number as needed

    # Fetch the most recent test data for the student from TestHistory
    cur.execute("""
        SELECT Score, CorrectAnswers, IncorrectAnswers, AverageAnsweringTimeInSeconds
        FROM TestHistory
        WHERE StudentID = %s
        ORDER BY LastTestAttempt DESC
        LIMIT %s
    """, (student_id, num_recent_tests))

    results = cur.fetchall()

    # Initialize weighted sum and total weights
    weighted_sum_correct = 0
    weighted_sum_incorrect = 0
    weighted_sum_time = 0
    total_weights = 0

    # Calculate weighted sums
    for i, (test_score, test_correct, test_incorrect, test_time) in enumerate(results):
        weight = num_recent_tests - i
        weighted_sum_correct += test_correct * weight
        weighted_sum_incorrect += test_incorrect * weight
        weighted_sum_time += (test_time or 0) * weight  # Handle None values
        total_weights += weight

    # Calculate new weighted averages
    new_avg_correct = weighted_sum_correct / total_weights if total_weights else correct_answers
    new_avg_incorrect = weighted_sum_incorrect / total_weights if total_weights else incorrect_answers
    new_avg_time = weighted_sum_time / total_weights if total_weights else avg_answering_time

    # Calculate new average score
    new_avg_score = (new_avg_correct * 4) - new_avg_incorrect  # Modify as per your scoring logic

    # Update or insert into PracticeTestProficiency
    cur.execute("""
        INSERT INTO PracticeTestProficiency (StudentID, AverageScore, AverageCorrectAnswers, AverageIncorrectAnswers, AverageAnsweringTimeInSeconds, TotalTestsTaken, LastResponseDate)
        VALUES (%s, %s, %s, %s, %s, 1, %s)
        ON CONFLICT (StudentID)
        DO UPDATE SET 
            AverageScore = %s, 
            AverageCorrectAnswers = %s, 
            AverageIncorrectAnswers = %s, 
            AverageAnsweringTimeInSeconds = %s, 
            TotalTestsTaken = PracticeTestProficiency.TotalTestsTaken + 1,
            LastResponseDate = %s
    """, (student_id, new_avg_score, new_avg_correct, new_avg_incorrect, new_avg_time, last_test_datetime, new_avg_score, new_avg_correct, new_avg_incorrect, new_avg_time, last_test_datetime))

def update_mock_test_proficiency(cur, student_id, score, correct_answers, incorrect_answers, avg_answering_time, last_test_datetime):
    # Define the number of recent mock tests to consider and the initial weight
    num_recent_tests = 5  # Adjust this number as needed

    # Fetch the most recent mock test data for the student from TestHistory
    cur.execute("""
        SELECT Score, CorrectAnswers, IncorrectAnswers, AverageAnsweringTimeInSeconds
        FROM TestHistory
        WHERE StudentID = %s AND TestType = 'Mock'
        ORDER BY LastTestAttempt DESC
        LIMIT %s
    """, (student_id, num_recent_tests))

    results = cur.fetchall()

    # Initialize weighted sum and total weights
    weighted_sum_correct = 0
    weighted_sum_incorrect = 0
    weighted_sum_time = 0
    total_weights = 0

    # Calculate weighted sums
    for i, (test_score, test_correct, test_incorrect, test_time) in enumerate(results):
        weight = num_recent_tests - i
        weighted_sum_correct += test_correct * weight
        weighted_sum_incorrect += test_incorrect * weight
        weighted_sum_time += (test_time or 0) * weight  # Handle None values
        total_weights += weight

    # Calculate new weighted averages
    new_avg_correct = weighted_sum_correct / total_weights if total_weights else correct_answers
    new_avg_incorrect = weighted_sum_incorrect / total_weights if total_weights else incorrect_answers
    new_avg_time = weighted_sum_time / total_weights if total_weights else avg_answering_time

    # Calculate new average score
    new_avg_score = (new_avg_correct * 4) - new_avg_incorrect  # Modify as per your scoring logic

    # Update or insert into MockTestProficiency
    cur.execute("""
        INSERT INTO MockTestProficiency (StudentID, AverageScore, AverageCorrectAnswers, AverageIncorrectAnswers, AverageAnsweringTimeInSeconds, TotalTestsTaken, LastResponseDate)
        VALUES (%s, %s, %s, %s, %s, 1, %s)
        ON CONFLICT (StudentID)
        DO UPDATE SET 
            AverageScore = %s, 
            AverageCorrectAnswers = %s, 
            AverageIncorrectAnswers = %s, 
            AverageAnsweringTimeInSeconds = %s, 
            TotalTestsTaken = MockTestProficiency.TotalTestsTaken + 1,
            LastResponseDate = %s
    """, (student_id, new_avg_score, new_avg_correct, new_avg_incorrect, new_avg_time, last_test_datetime, new_avg_score, new_avg_correct, new_avg_incorrect, new_avg_time, last_test_datetime))
