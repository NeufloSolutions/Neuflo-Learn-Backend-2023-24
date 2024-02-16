import datetime
from Backend.dbconfig.db_connection import create_pg_connection, release_pg_connection, pg_connection_pool

def calculate_section_practice_test_results(student_id, test_instance_id, subject_code):
    # Mapping subject_code to SubjectID
    subject_id_map = {1: 'Physics', 2: 'Chemistry', 3: 'Biology'}
    subject_name = subject_id_map.get(subject_code, None)
    if not subject_name:
        return None, "Invalid subject code provided."

    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return None, "Database connection failed."

    try:
        with conn.cursor() as cur:
            # Assuming Subjects table has a SubjectName column for fetching the SubjectID based on subject_name
            cur.execute("SELECT SubjectID FROM Subjects WHERE SubjectName = %s", (subject_name,))
            subject_id_row = cur.fetchone()
            if not subject_id_row:
                return None, "Subject not found."
            subject_id = subject_id_row[0]

            # Fetch responses and question details for the specified subject within the test instance
            cur.execute("""
                SELECT SR.QuestionID, SR.StudentResponse, Q.Answer, CH.SubjectID, SR.AnsweringTimeInSeconds, SR.ResponseDate
                FROM StudentResponses SR
                JOIN Questions Q ON SR.QuestionID = Q.QuestionID
                JOIN Chapters CH ON Q.ChapterID = CH.ChapterID
                WHERE SR.StudentID = %s AND SR.TestInstanceID = %s AND CH.SubjectID = %s
            """, (student_id, test_instance_id, subject_id))
            responses = cur.fetchall()

            correct_answers, incorrect_answers, total_answering_time = 0, 0, 0
            last_response_date = None
            for question_id, student_response, answer, _, answering_time, response_date in responses:
                correct, incorrect = evaluate_response(student_response, answer)
                correct_answers += correct
                incorrect_answers += incorrect
                answer_correct = correct > 0
                total_answering_time += answering_time if answering_time else 0
                last_response_date = max(last_response_date, response_date) if last_response_date else response_date
                
                # Update the StudentResponses with the correctness of the answer
                cur.execute("""
                    UPDATE StudentResponses
                    SET AnswerCorrect = %s
                    WHERE TestInstanceID = %s AND QuestionID = %s
                """, (answer_correct, test_instance_id, question_id))

            # Calculate score based on correct and incorrect answers
            score = correct_answers * 4 - incorrect_answers

            # Update TestHistory for this test instance with new score and details
            cur.execute("""
                UPDATE TestHistory
                SET Score = %s, QuestionsAttempted = QuestionsAttempted + %s, CorrectAnswers = CorrectAnswers + %s, 
                    IncorrectAnswers = IncorrectAnswers + %s, AverageAnsweringTimeInSeconds = %s, LastTestAttempt = %s
                WHERE TestInstanceID = %s AND StudentID = %s
            """, (score, len(responses), correct_answers, incorrect_answers, total_answering_time / len(responses) if responses else None, last_response_date, test_instance_id, student_id))

            # Update proficiency tables
            update_proficiency_tables(cur, student_id, test_instance_id)
            update_practice_test_proficiency(cur, student_id, score, correct_answers, incorrect_answers, total_answering_time / len(responses) if responses else None, last_response_date)

            conn.commit()
            return {
                "message": "Section test results calculated and updated successfully.",
                "details": {
                    "score": score,
                    "correct_answers": correct_answers,
                    "incorrect_answers": incorrect_answers,
                    "average_answering_time_seconds": total_answering_time / len(responses) if responses else 0,
                    "last_response_date": last_response_date.strftime('%Y-%m-%d %H:%M:%S') if last_response_date else None
                }
            }, None
    except Exception as e:
        conn.rollback()
        return None, "Error calculating section test results: " + str(e)
    finally:
        if conn:
            release_pg_connection(pg_connection_pool, conn)




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
                WHERE TestInstanceID = %s AND StudentID = %s
            """, (test_instance_id, student_id))
            test_instance_data = cur.fetchone() 
            if test_instance_data:
                test_type, test_id = test_instance_data
            else:
                return None, "Test instance not found"

            # Check if the test is completed based on test type
            if test_type == "Practice":
                cur.execute("""
                    SELECT IsCompleted
                    FROM PracticeTestCompletion
                    WHERE PracticeTestID = %s AND StudentID = %s
                """, (test_id, student_id))
            elif test_type == "Mock":
                cur.execute("""
                    SELECT IsCompleted
                    FROM MockTestCompletion
                    WHERE MockTestID = %s AND StudentID = %s
                """, (test_id, student_id))
            else:
                return None, "Invalid test type"

            completion_data = cur.fetchone()
            if not completion_data or not completion_data[0]:
                return None, "Test not completed"

            # Call the appropriate function based on test type
            if test_type == "Practice":
                print("Entered Practice Test Calculation Function")
                return calculate_practice_test_results(cur, student_id, test_instance_id, test_id)
            elif test_type == "Mock":
                print("Entered Mock Test Calculation Function")
                return calculate_mock_test_results(cur, student_id, test_instance_id, test_id)

    except Exception as e:
        print("Entered Exception - Rollback")
        conn.rollback()
        return None, str(e)
    finally:
        if conn:
            conn.commit()
            release_pg_connection(pg_connection_pool, conn)


def calculate_practice_test_results(cur, student_id, test_instance_id, practice_test_id):
    # Adjusted query to join the tables based on your schema
    cur.execute("""
        SELECT SR.QuestionID, SR.StudentResponse, Q.Answer, CH.SubjectID, SR.AnsweringTimeInSeconds, SR.ResponseDate
        FROM StudentResponses SR
        JOIN Questions Q ON SR.QuestionID = Q.QuestionID
        JOIN Chapters CH ON Q.ChapterID = CH.ChapterID
        JOIN PracticeTestQuestions PTQ ON Q.QuestionID = PTQ.QuestionID
        JOIN PracticeTestSubjects PTS ON PTQ.PracticeTestSubjectID = PTS.PracticeTestSubjectID
        JOIN PracticeTests PT ON PTS.PracticeTestID = PT.PracticeTestID
        WHERE SR.StudentID = %s AND PT.PracticeTestID = %s;
    """, (student_id, practice_test_id))
    responses = cur.fetchall()

    if not responses:
        return None, "No responses found for given student and test instance"

    correct_answers = 0
    incorrect_answers = 0
    total_answering_time = 0
    last_test_datetime = None

    for question_id, student_response, answer, subject_id, answering_time, response_date in responses:
        correct, incorrect = evaluate_response(student_response, answer)
        correct_answers += correct
        incorrect_answers += incorrect

        # Update the AnswerCorrect column for each response
        answer_correct = correct > 0
        cur.execute("""
            UPDATE StudentResponses
            SET AnswerCorrect = %s
            WHERE StudentID = %s AND QuestionID = %s AND TestInstanceID = %s
        """, (answer_correct, student_id, question_id, test_instance_id))

        total_answering_time += answering_time if answering_time else 0
        last_test_datetime = max(last_test_datetime, response_date) if last_test_datetime else response_date

    questions_attempted = len(responses)
    avg_answering_time = total_answering_time / questions_attempted if questions_attempted else None
    score = correct_answers * 4 - incorrect_answers  # Scoring logic for practice tests

    # Update TestHistory table
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

    # Call the functions to update proficiency tables and practice test proficiency
    print("Updating Proficiency Tables")
    update_proficiency_tables(cur, student_id, test_instance_id)

    print("Updating Practice Test Proficiency")
    update_practice_test_proficiency(cur, student_id, score, correct_answers, incorrect_answers, avg_answering_time, last_test_datetime)

    return {
        "score": score,
        "correct_answers": correct_answers,
        "incorrect_answers": incorrect_answers,
        "average_answering_time": avg_answering_time,
        "last_test_datetime": last_test_datetime.strftime('%Y-%m-%d %H:%M:%S') if last_test_datetime else None
    }, None


def calculate_mock_test_results(cur, student_id, test_instance_id, test_id):
    try:
        print("Entering calculate_mock_test_results")
        # Retrieve responses, including subject and section information
        cur.execute("""
            SELECT SR.QuestionID, SR.StudentResponse, Q.Answer, CH.SubjectID, NMTQ.Section, SR.AnsweringTimeInSeconds, SR.ResponseDate
            FROM StudentResponses SR
            JOIN Questions Q ON SR.QuestionID = Q.QuestionID
            JOIN Chapters CH ON Q.ChapterID = CH.ChapterID
            JOIN NEETMockTestQuestions NMTQ ON Q.QuestionID = NMTQ.QuestionID AND NMTQ.MockTestID = %s
            WHERE SR.StudentID = %s AND SR.TestInstanceID = %s
        """, (test_id, student_id, test_instance_id))

        responses = cur.fetchall()

        correct_questions = []
        incorrect_questions = []
        skipped_questions = []

        correct_answers = 0
        incorrect_answers = 0
        total_answering_time = 0

        for question_id, student_response, answer, subject_id, section, answering_time, response_date in responses:
            correct, incorrect = evaluate_response(student_response, answer)
            if correct:
                correct_answers += 1
                correct_questions.append(question_id)
            elif incorrect:
                incorrect_answers += 1
                incorrect_questions.append(question_id)
            else:
                # Assuming 'na' or an empty string indicates a skipped question
                skipped_questions.append(question_id)

            # Update the AnswerCorrect column for each response
            answer_correct = correct > 0
            cur.execute("""
                UPDATE StudentResponses
                SET AnswerCorrect = %s
                WHERE StudentID = %s AND QuestionID = %s AND TestInstanceID = %s
            """, (answer_correct, student_id, question_id, test_instance_id))

            total_answering_time += answering_time if answering_time else 0

        # Sorting the question lists
        correct_questions.sort()
        incorrect_questions.sort()
        skipped_questions.sort()

        avg_answering_time = total_answering_time / len(responses) if responses else 0
        score = correct_answers * 4 - incorrect_answers  # Scoring logic for mock tests

        last_response_date = max(r[6] for r in responses) if responses else None

        # Update TestHistory table
        cur.execute("""
            INSERT INTO TestHistory (TestInstanceID, StudentID, Score, QuestionsAttempted, CorrectAnswers, IncorrectAnswers, AverageAnsweringTimeInSeconds, LastTestAttempt)
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (TestInstanceID, StudentID) DO UPDATE SET 
                Score = EXCLUDED.Score, 
                QuestionsAttempted = EXCLUDED.QuestionsAttempted,
                CorrectAnswers = EXCLUDED.CorrectAnswers, 
                IncorrectAnswers = EXCLUDED.IncorrectAnswers, 
                AverageAnsweringTimeInSeconds = EXCLUDED.AverageAnsweringTimeInSeconds,
                LastTestAttempt = EXCLUDED.LastTestAttempt;
        """, (test_instance_id, student_id, score, len(responses), correct_answers, incorrect_answers, avg_answering_time, last_response_date))

        # Update proficiency tables
        update_proficiency_tables(cur, student_id, test_instance_id)

        # Update mock test proficiency (assuming this function is defined elsewhere in your code)
        update_mock_test_proficiency(cur, student_id, score, correct_answers, incorrect_answers, avg_answering_time, last_response_date)

        return {
            "score": score,
            "correct_answers": correct_answers,
            "incorrect_answers": incorrect_answers,
            "average_answering_time": avg_answering_time,
            "last_test_datetime": last_response_date,
            "correct_questions": correct_questions,
            "incorrect_questions": incorrect_questions,
            "skipped_questions": skipped_questions
        }, None

    except Exception as e:
        print(f"Error encountered: {e}")
        raise


def evaluate_response(student_response, correct_answer):
    student_response = student_response.strip().lower() if student_response else ''
    correct_answer = correct_answer.strip().lower() if correct_answer else ''
    correct = student_response == correct_answer
    incorrect = not correct and student_response != '' and student_response != 'na'
    return correct, incorrect


def update_proficiency_tables(cur, student_id, test_instance_id):
    # Debugging: Print input parameters
    print(f"Updating proficiency tables for student_id: {student_id}, test_instance_id: {test_instance_id}")

    cur.execute("""
        SELECT Q.ChapterID, Q.SubtopicID, SR.StudentResponse, Q.Answer
        FROM StudentResponses SR
        JOIN Questions Q ON SR.QuestionID = Q.QuestionID
        WHERE SR.StudentID = %s AND SR.TestInstanceID = %s
    """, (student_id, test_instance_id))

    chapter_proficiency_data = []
    subtopic_proficiency_data = []

    for chapter_id, subtopic_id, student_response, correct_answer in cur.fetchall():
        is_correct = student_response.lower() == correct_answer.lower()
        chapter_proficiency_data.append((student_id, chapter_id, is_correct))
        subtopic_proficiency_data.append((student_id, subtopic_id, is_correct))

    # Debugging: Print fetched data
    if not chapter_proficiency_data and not subtopic_proficiency_data:
        print(f"No proficiency data found for student_id: {student_id}, test_instance_id: {test_instance_id}")
    # else:
    #     print("Chapter Proficiency Data:", chapter_proficiency_data)
    #     print("Subtopic Proficiency Data:", subtopic_proficiency_data)

    update_proficiency_bulk(cur, chapter_proficiency_data, "ChapterProficiency", "ChapterID")
    update_proficiency_bulk(cur, subtopic_proficiency_data, "SubtopicProficiency", "SubtopicID")


def update_proficiency_bulk(cur, proficiency_data, table_name, id_column_name):
    # Check if proficiency_data is empty
    if not proficiency_data:
        print(f"No data to update for {table_name}")
        return

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
    SELECT TH.Score, TH.CorrectAnswers, TH.IncorrectAnswers, TH.AverageAnsweringTimeInSeconds
    FROM TestHistory TH
    JOIN TestInstances TI ON TH.TestInstanceID = TI.TestInstanceID
    WHERE TI.StudentID = %s AND TI.TestType = 'Practice'
    ORDER BY TH.LastTestAttempt DESC
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
    num_recent_tests = 5

    # Fetch recent mock test data from TestHistory
    cur.execute("""
    SELECT TH.Score, TH.CorrectAnswers, TH.IncorrectAnswers, TH.AverageAnsweringTimeInSeconds
    FROM TestHistory TH
    JOIN TestInstances TI ON TH.TestInstanceID = TI.TestInstanceID
    WHERE TI.StudentID = %s AND TI.TestType = 'Mock'
    ORDER BY TH.LastTestAttempt DESC
    LIMIT %s
    """, (student_id, num_recent_tests))

    results = cur.fetchall()

    # Include current test results in the calculation
    total_correct_answers = correct_answers
    total_incorrect_answers = incorrect_answers
    total_answering_time = avg_answering_time
    total_tests = 1  # Start with the current test
    
    # Aggregate past test results
    for test_score, test_correct, test_incorrect, test_time in results:
        total_correct_answers += test_correct
        total_incorrect_answers += test_incorrect
        total_answering_time += test_time
        total_tests += 1

    # Calculate new averages
    new_avg_correct = total_correct_answers / total_tests
    new_avg_incorrect = total_incorrect_answers / total_tests
    new_avg_time = total_answering_time / total_tests
    new_avg_score = (new_avg_correct * 4) - new_avg_incorrect

    # Update MockTestProficiency table
    cur.execute("""
        INSERT INTO MockTestProficiency (StudentID, AverageScore, AverageCorrectAnswers, AverageIncorrectAnswers, AverageAnsweringTimeInSeconds, TotalTestsTaken, LastResponseDate)
        VALUES (%s, %s, %s, %s, %s, %s, %s)
        ON CONFLICT (StudentID)
        DO UPDATE SET 
            AverageScore = EXCLUDED.AverageScore, 
            AverageCorrectAnswers = EXCLUDED.AverageCorrectAnswers, 
            AverageIncorrectAnswers = EXCLUDED.AverageIncorrectAnswers, 
            AverageAnsweringTimeInSeconds = EXCLUDED.AverageAnsweringTimeInSeconds, 
            TotalTestsTaken = MockTestProficiency.TotalTestsTaken + 1,
            LastResponseDate = EXCLUDED.LastResponseDate
    """, (student_id, new_avg_score, new_avg_correct, new_avg_incorrect, new_avg_time, total_tests, last_test_datetime))

    print("MockTestProficiency table updated")


