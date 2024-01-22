import random
import psycopg2.extras
import numpy as np
from Backend.dbconfig.cache_management import get_cached_questions, cache_questions
from Backend.dbconfig.db_connection import create_pg_connection, release_pg_connection, pg_connection_pool

def generate_mock_test(student_id):
    """
    Main function to generate a mock test.
    
    :param student_id: ID of the student.
    :return: Dictionary with message and testInstanceID.
    """
    subject_ids = [1, 2, 3, 4]
    mock_test_questions = []

    for subject_id in subject_ids:
        questions_a = select_questions_for_subject(subject_id, student_id, 'A')
        questions_b = select_questions_for_subject(subject_id, student_id, 'B')
        mock_test_questions.extend(questions_a + questions_b)

    print(f"Total questions selected for the mock test: {len(mock_test_questions)}")

    success = False
    while not success:
        mock_test_id = random.randint(1000, 99999)
        test_instance_id = random.randint(1000, 99999)
        success = create_test_instance(student_id, mock_test_id, test_instance_id, mock_test_questions)

    return {"message": "Mock test generated successfully", "testInstanceID": test_instance_id}

def get_chapter_ids_for_questions(question_ids):
    """
    Retrieves the chapter IDs for a given list of question IDs.
    
    :param question_ids: List of question IDs.
    :return: Dictionary of question IDs to their corresponding chapter IDs.
    """
    if not question_ids:
        return {}

    question_chapter_mapping = {}
    connection = create_pg_connection(pg_connection_pool)
    cursor = connection.cursor()
    try:
        format_strings = ','.join(['%s'] * len(question_ids))
        cursor.execute(f"SELECT QuestionID, ChapterID FROM Questions WHERE QuestionID IN ({format_strings})", tuple(question_ids))
        for question_id, chapter_id in cursor.fetchall():
            question_chapter_mapping[question_id] = chapter_id
    except Exception as e:
        print(f"Error fetching chapter IDs: {e}")
    finally:
        release_pg_connection(pg_connection_pool, connection)
    return question_chapter_mapping


def select_questions_for_subject(subject_id, student_id, section):
    """
    Optimized selection of questions for a given subject, considering the student's history
    and chapter weightage.
    
    :param subject_id: ID of the subject.
    :param student_id: ID of the student.
    :param section: Section of the test ('A' or 'B').
    :return: List of selected question IDs with their section.
    """
    used_questions = set(get_cached_questions(student_id))
    chapters_weightage = get_chapter_weightage(subject_id)
    all_questions = get_questions_for_subject(subject_id, used_questions)

    # Define the number of questions required for each section
    total_questions_required = 35 if section == 'A' else 15
    selected_questions = list(set(weighted_question_selection(all_questions, chapters_weightage, total_questions_required)))

    # If not enough unique questions, get more from higher weightage chapters
    while len(selected_questions) < total_questions_required:
        additional_questions_needed = total_questions_required - len(selected_questions)
        more_questions = get_additional_questions(subject_id, selected_questions, chapters_weightage, additional_questions_needed)
        selected_questions.extend(more_questions)
        selected_questions = list(set(selected_questions))  # Remove any new duplicates

    # Update the cache with the newly selected questions
    cache_questions(student_id, list(used_questions | set(selected_questions)))

    # Assign section label and return
    return [(qid, section) for qid in selected_questions[:total_questions_required]]

def get_additional_questions(subject_id, excluded_questions, chapters_weightage, num_required):
    """
    Fetches additional questions from higher weightage chapters.
    
    :param subject_id: ID of the subject.
    :param excluded_questions: Set of question IDs already used or selected.
    :param chapters_weightage: Dictionary of chapter ID to weightage.
    :param num_required: Number of additional questions needed.
    :return: List of additional question IDs.
    """
    connection = create_pg_connection(pg_connection_pool)
    cursor = connection.cursor()
    additional_questions = []

    # Ensure excluded_questions is a set
    excluded_questions = set(excluded_questions)

    try:
        # Sort chapters by weightage, descending
        sorted_chapters = sorted(chapters_weightage, key=chapters_weightage.get, reverse=True)

        for chapter_id in sorted_chapters:
            if len(additional_questions) >= num_required:
                break

            query = """
            SELECT QuestionID FROM Questions
            WHERE ChapterID = %s AND QuestionID NOT IN %s
            ORDER BY RANDOM() 
            LIMIT %s
            """
            remaining_needed = num_required - len(additional_questions)
            excluded_questions_tuple = tuple(excluded_questions) if excluded_questions else (-1,)

            cursor.execute(query, (chapter_id, excluded_questions_tuple, remaining_needed))
            results = cursor.fetchall()

            for row in results:
                question_id = row[0]
                additional_questions.append(question_id)
                excluded_questions.add(question_id)  # Update the excluded questions set

    except Exception as e:
        print(f"Error fetching additional questions: {e}")
    finally:
        release_pg_connection(pg_connection_pool, connection)

    return additional_questions


def create_test_instance(student_id, mock_test_id, test_instance_id, question_ids_with_sections):
    connection = create_pg_connection(pg_connection_pool)
    cursor = connection.cursor()

    try:
        # Check for existing MockTestID and TestInstanceID
        cursor.execute("SELECT COUNT(*) FROM NEETMockTests WHERE MockTestID = %s", (mock_test_id,))
        if cursor.fetchone()[0] > 0:
            return False

        cursor.execute("SELECT COUNT(*) FROM TestInstances WHERE TestInstanceID = %s", (test_instance_id,))
        if cursor.fetchone()[0] > 0:
            return False

        # Insert into NEETMockTests
        cursor.execute("INSERT INTO NEETMockTests (MockTestID, StudentID) VALUES (%s, %s)", (mock_test_id, student_id))

        # Validate and prepare data for bulk insert
        if not all(isinstance(q, tuple) and len(q) == 2 for q in question_ids_with_sections):
            raise ValueError("Invalid format in question_ids_with_sections. Expected list of tuples (QuestionID, Section).")
        questions_data = [(mock_test_id, qid, sec) for qid, sec in question_ids_with_sections]

        # Bulk insert selected questions into NEETMockTestQuestions with section info
        insert_query = "INSERT INTO NEETMockTestQuestions (MockTestID, QuestionID, Section) VALUES %s"
        psycopg2.extras.execute_values(cursor, insert_query, questions_data)

        # Insert into TestInstances
        cursor.execute("INSERT INTO TestInstances (TestInstanceID, StudentID, TestID, TestType) VALUES (%s, %s, %s, 'Mock')", (test_instance_id, student_id, mock_test_id))

        connection.commit()
        return True

    except Exception as e:
        print(f"Rollback: Error creating test instance: {e}")
        connection.rollback()
        return False
    finally:
        release_pg_connection(pg_connection_pool, connection)


def get_chapter_weightage(subject_id):
    """
    Retrieves and rounds the weightage for chapters in a subject.
    
    :param subject_id: ID of the subject.
    :return: Dictionary of chapter ID to rounded weightage.
    """
    connection = create_pg_connection(pg_connection_pool)
    cursor = connection.cursor()
    weightages = {}

    try:
        cursor.execute("SELECT ChapterID, Weightage FROM MockTestChapterWeightage WHERE SubjectID = %s", (subject_id,))
        for chapter_id, weightage in cursor.fetchall():
            # Round weightage to 4 decimal places
            rounded_weightage = round(weightage, 4)
            weightages[chapter_id] = rounded_weightage
    except Exception as e:
        print(f"Error fetching chapter weightages: {e}")
    finally:
        release_pg_connection(pg_connection_pool,connection)

    return weightages


def get_questions_for_mock_test_instance(mock_test_id):
    """
    Retrieves all question IDs for a given mock test instance categorized by subject and section.
    
    :param mock_test_id: ID of the mock test instance.
    :return: Dictionary of questions categorized by subject and section.
    """
    connection = create_pg_connection(pg_connection_pool)
    cursor = connection.cursor()
    questions_dict = {}

    try:
        query = """
        SELECT s.SubjectName, q.Section, q.QuestionID 
        FROM NEETMockTestQuestions nmtq
        JOIN Questions q ON nmtq.QuestionID = q.QuestionID
        JOIN Chapters c ON q.ChapterID = c.ChapterID
        JOIN Subjects s ON c.SubjectID = s.SubjectID
        WHERE nmtq.MockTestID = %s
        ORDER BY s.SubjectName, q.Section
        """
        cursor.execute(query, (mock_test_id,))
        for subject, section, question_id in cursor.fetchall():
            if subject not in questions_dict:
                questions_dict[subject] = {"SectionA": [], "SectionB": []}
            questions_dict[subject]["SectionA" if section == 'A' else "SectionB"].append(question_id)
    except Exception as e:
        print(f"Error fetching questions for mock test instance: {e}")
    finally:
        release_pg_connection(pg_connection_pool, connection)

    return questions_dict


def weighted_question_selection(question_ids, weightage, num_questions):
    """
    Optimized selection of questions based on chapter weightage.
    
    :param question_ids: List of question IDs.
    :param weightage: Dictionary of chapter ID to weightage.
    :param num_questions: Number of questions to select.
    :return: List of selected question IDs.
    """
    if not question_ids:
        return []

    # Batch fetch chapter IDs for questions
    chapter_ids_for_questions = get_chapter_ids_for_questions(question_ids)

    # Normalize weights and prepare for selection
    total_weight = sum(weightage.values())
    normalized_weights = {k: (v / total_weight) for k, v in weightage.items()}

    # Prepare for weighted selection
    weighted_selection_pool = []
    for question_id in question_ids:
        chapter_id = chapter_ids_for_questions.get(question_id)
        if chapter_id and chapter_id in normalized_weights:
            weight = normalized_weights[chapter_id]
            weighted_selection_pool.extend([question_id] * int(weight * 100))

    # Perform selection
    if weighted_selection_pool:
        return random.sample(weighted_selection_pool, min(len(weighted_selection_pool), num_questions))
    else:
        return random.sample(question_ids, num_questions)


def get_questions_for_subject(subject_id, used_questions):
    """
    Fetches all questions for a given subject, excluding those already attempted by the student.
    
    :param subject_id: ID of the subject.
    :param used_questions: Set of question IDs already attempted by the student.
    :return: List of question IDs.
    """
    connection = create_pg_connection(pg_connection_pool)
    cursor = connection.cursor()
    questions = []

    try:
        query = """
        SELECT QuestionID FROM Questions 
        WHERE ChapterID IN (SELECT ChapterID FROM Chapters WHERE SubjectID = %s)
        AND QuestionID NOT IN %s
        """
        # Handling the case where used_questions is empty
        if not used_questions:
            used_questions = {-1}  # PostgreSQL doesn't support empty lists in queries. Using a placeholder.

        cursor.execute(query, (subject_id, tuple(used_questions)))
        questions = [row[0] for row in cursor.fetchall()]
    except Exception as e:
        print(f"Error fetching questions for subject: {e}")
    finally:
        release_pg_connection(pg_connection_pool, connection)

    # print(f"Questions fetched for subject {subject_id}, excluding {used_questions}: {questions}")
    if not questions:
        print(f"No questions available for subject {subject_id} after excluding used questions.")
    return questions

def get_questions_for_mock_test_instance(testInstanceID, student_id):
    """
    Retrieves all question IDs for a given mock test instance, categorized by subject and section,
    for a specific student, using the test instance ID.

    :param testInstanceID: ID of the test instance.
    :param student_id: ID of the student.
    :return: Dictionary with subject-wise and section-wise question IDs.
    """
    connection = create_pg_connection(pg_connection_pool)
    cursor = connection.cursor()
    questions_dict = {}

    try:
        # First, get the MockTestID from the TestInstances table
        cursor.execute("SELECT TestID FROM TestInstances WHERE TestInstanceID = %s AND StudentID = %s", (testInstanceID, student_id))
        result = cursor.fetchone()
        if not result:
            raise Exception("No MockTestID found for the given TestInstanceID and StudentID.")
        mock_test_id = result[0]

        # Now fetch the questions using MockTestID
        query = """
        SELECT s.SubjectName, mtq.Section, q.QuestionID 
        FROM NEETMockTestQuestions mtq
        JOIN Questions q ON mtq.QuestionID = q.QuestionID
        JOIN Chapters c ON q.ChapterID = c.ChapterID
        JOIN Subjects s ON c.SubjectID = s.SubjectID
        JOIN NEETMockTests nmt ON mtq.MockTestID = nmt.MockTestID
        WHERE mtq.MockTestID = %s AND nmt.StudentID = %s
        ORDER BY s.SubjectName
        """
        cursor.execute(query, (mock_test_id,student_id))
        for subject_name, section, question_id in cursor.fetchall():
            if subject_name not in questions_dict:
                questions_dict[subject_name] = {"SectionA": [], "SectionB": []}
            section_key = "SectionA" if section == 'A' else "SectionB"
            questions_dict[subject_name][section_key].append(question_id)

    except Exception as e:
        print(f"Error fetching questions for mock test instance: {e}")
    finally:
        release_pg_connection(pg_connection_pool, connection)

    return questions_dict

def submit_mock_test_answers(student_id, testInstanceID, answers):
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return "Database connection failed"

    try:
        with conn.cursor() as cur:
            # Retrieve MockTestID related to TestInstanceID
            cur.execute("""
                SELECT TestID FROM TestInstances
                WHERE TestInstanceID = %s
            """, (testInstanceID,))
            mock_test_result = cur.fetchone()
            if mock_test_result is None:
                return None, "Mock test not found"

            mock_test_id = mock_test_result[0]

            # Record each student response
            for question_id, response in answers.items():
                answering_time = response.get('time', 60)  # Default time if not provided
                student_response = response.get('answer', 'n')  # Default to 'n' if not provided or empty

                cur.execute("""
                    INSERT INTO StudentResponses (TestInstanceID, StudentID, QuestionID, StudentResponse, AnsweringTimeInSeconds)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (TestInstanceID, StudentID, QuestionID)
                    DO UPDATE SET 
                        StudentResponse = EXCLUDED.StudentResponse,
                        AnsweringTimeInSeconds = EXCLUDED.AnsweringTimeInSeconds,
                        ResponseDate = CURRENT_TIMESTAMP
                """, (testInstanceID, student_id, question_id, student_response, answering_time))

            # Mark mock test as completed
            cur.execute("""
                INSERT INTO MockTestCompletion (MockTestID, StudentID, IsCompleted, CompletionDate)
                VALUES (%s, %s, TRUE, CURRENT_TIMESTAMP)
                ON CONFLICT (MockTestID, StudentID)
                DO UPDATE SET 
                    IsCompleted = TRUE,
                    CompletionDate = CURRENT_TIMESTAMP
            """, (mock_test_id, student_id))

            conn.commit()
            return {"message": "Submission successful"}
    except Exception as e:
        conn.rollback()
        return None, str(e)
    finally:
        release_pg_connection(pg_connection_pool, conn)
