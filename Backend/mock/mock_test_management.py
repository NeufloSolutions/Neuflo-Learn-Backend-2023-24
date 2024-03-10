import random
import psycopg2.extras
import numpy as np
from Backend.dbconfig.cache_management import get_cached_questions, cache_questions
from Backend.dbconfig.db_connection import create_pg_connection, release_pg_connection, pg_connection_pool

def generate_mock_test(student_id):
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return {"message": "Database connection failed"}

    existing_mock_test_ids, existing_test_instance_ids = fetch_existing_ids()

    mock_test_id = generate_unique_id(existing_mock_test_ids)
    test_instance_id = generate_unique_id(existing_test_instance_ids)

    try:
        with conn.cursor() as cur:
            subject_ids = [1, 2, 3, 4]
            mock_test_questions = []
            current_selected_questions = []

            for subject_id in subject_ids:
                questions_a = select_questions_for_subject(subject_id, student_id, 'A', current_selected_questions)
                current_selected_questions.extend([q[0] for q in questions_a])
                questions_b = select_questions_for_subject(subject_id, student_id, 'B', current_selected_questions)
                mock_test_questions.extend(questions_a + questions_b)
                current_selected_questions.extend([q[0] for q in questions_b])
            
            success = create_test_instance(student_id, mock_test_id, test_instance_id, mock_test_questions)
            if success:
                cur.execute("""
                    INSERT INTO MockTestCompletion (MockTestID, StudentID, IsCompleted)
                    VALUES (%s, %s, FALSE)
                """, (mock_test_id, student_id,))
                conn.commit()
                
                return {"message": "Mock test generated successfully", "testInstanceID": test_instance_id}
    except Exception as e:
        conn.rollback()
        return {"message": f"An error occurred: {str(e)}"}
    finally:
        release_pg_connection(pg_connection_pool, conn)



def generate_unique_id(existing_ids, start=1000, end=9999):
    potential_id = random.randint(start, end)
    while potential_id in existing_ids:
        potential_id = random.randint(start, end)
    return potential_id

def fetch_existing_ids():
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        print("Database connection failed")
        return [], []

    try:
        with conn.cursor() as cur:
            cur.execute("SELECT MockTestID FROM NEETMockTests")
            existing_mock_test_ids = [row[0] for row in cur.fetchall()]

            cur.execute("SELECT TestInstanceID FROM TestInstances")
            existing_test_instance_ids = [row[0] for row in cur.fetchall()]

        return existing_mock_test_ids, existing_test_instance_ids
    except Exception as e:
        print(f"An error occurred while fetching existing IDs: {str(e)}")
        return [], []
    finally:
        release_pg_connection(pg_connection_pool, conn)

def select_questions_for_subject(subject_id, student_id, section, current_selected_questions):
    """
    Selects questions for a given subject, considering the student's history,
    chapter weightage, and ensuring no duplicates within the current mock test.
    Allows repetitions if the unique pool is exhausted.

    :param subject_id: ID of the subject.
    :param student_id: ID of the student.
    :param section: Section of the test ('A' or 'B').
    :param current_selected_questions: List of question IDs already selected for the current mock test.
    :return: List of selected question IDs with their section.
    """
    used_questions = set(get_cached_questions(student_id, "mock"))
    chapters_weightage = get_chapter_weightage(subject_id)
    all_questions = get_questions_for_subject(subject_id, used_questions)

    # Adjust to consider current mock test selections
    all_questions = [q for q in all_questions if q not in current_selected_questions]

    # Define the number of questions required for each section
    total_questions_required = 35 if section == 'A' else 15
    selected_questions = []
    print("all question::", len(all_questions))
    if len(set(all_questions)) >= total_questions_required:
        # Sufficient unique questions available, excluding current selections
        selected_questions = weighted_question_selection(all_questions, chapters_weightage, total_questions_required, used_questions)
        print("selected_questions from all question:", len(selected_questions))
    else:
        # Allow repetition, but ensure no duplicates within the current test
       
        excluded_questions = used_questions | set(current_selected_questions)
        additional_needed = total_questions_required - len(set(selected_questions))
        print("Not enough unique questions, allowing repetitions.",additional_needed)
        selected_questions += get_additional_questions(subject_id, excluded_questions, chapters_weightage, additional_needed, current_selected_questions)
    
    # Ensure the total number of selected questions meets the requirement
    while len(selected_questions) < total_questions_required:
        additional_needed = total_questions_required - len(set(selected_questions))
        # Fetch more questions, considering current mock test selections
        excluded_questions = set(selected_questions) | set(current_selected_questions)
        additional_questions = get_additional_questions(subject_id, excluded_questions, chapters_weightage, additional_needed, current_selected_questions)
        selected_questions += additional_questions
        # Ensure uniqueness after each addition
        print(additional_questions, " - Needed . Additional question:", len(set(additional_questions)))
        selected_questions = list(set(selected_questions))
    print("selected_questions question:", len(selected_questions))
    # Trim to required size to handle any over-selection
    selected_questions = list(set(selected_questions))[:total_questions_required]
    print("selected_questions after remove duplicate:", len(selected_questions))
    # Update the cache with the newly selected questions
    cache_questions(student_id, "mock", list(used_questions | set(selected_questions)))

    # Assign section label and return
    return [(qid, section) for qid in selected_questions]

def get_additional_questions(subject_id, excluded_questions, chapters_weightage, num_required, current_selected_questions):
    """
    Fetches additional questions for the subject, ensuring no duplicates in the current mock test.
    Allows using old questions if all available questions are used up.

    :param subject_id: ID of the subject to fetch questions for.
    :param excluded_questions: A set of question IDs to exclude from the initial selection.
    :param chapters_weightage: A dictionary mapping chapter IDs to their weightage.
    :param num_required: The number of additional questions needed.
    :param current_selected_questions: The current list of selected questions for the mock test to avoid duplicates.
    :return: A list of additional question IDs.
    """
    connection = create_pg_connection(pg_connection_pool)
    cursor = connection.cursor()
    additional_questions = []

    try:
        # If all questions have been used, allow reuse of questions excluding the current mock test's selected ones.
        if len(excluded_questions) >= get_total_question_count(subject_id):
            excluded_questions = set(current_selected_questions)

        # Prioritize chapters based on weightage
        sorted_chapters = sorted(chapters_weightage.keys(), key=lambda x: chapters_weightage[x], reverse=True)

        for chapter_id in sorted_chapters:
            if len(additional_questions) >= num_required:
                break  # Stop if the required number of additional questions has been met

            # Fetch questions, excluding those already selected for the current mock test
            query = """
            SELECT QuestionID FROM Questions
            WHERE ChapterID = %s AND QuestionID NOT IN %s
            ORDER BY RANDOM()
            LIMIT %s
            """
            excluded_questions_list = list(excluded_questions) if excluded_questions else [-1]

            cursor.execute(query, (chapter_id, tuple(excluded_questions_list), num_required - len(additional_questions)))
            fetched_questions = cursor.fetchall()

            for question_id in fetched_questions:
                question_id = question_id[0]
                if question_id not in current_selected_questions:
                    additional_questions.append(question_id)
                    excluded_questions.add(question_id)

    except Exception as e:
        print(f"Error fetching additional questions: {e}")
    finally:
        release_pg_connection(pg_connection_pool, connection)

    return additional_questions

def get_total_question_count(subject_id):
    """
    Fetches the total count of questions available for a given subject.

    :param subject_id: ID of the subject.
    :return: Total count of questions.
    """
    connection = create_pg_connection(pg_connection_pool)
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT COUNT(*) FROM Questions WHERE ChapterID IN (SELECT ChapterID FROM Chapters WHERE SubjectID = %s)", (subject_id,))
        total_count = cursor.fetchone()[0]
    except Exception as e:
        print(f"Error fetching total question count for subject {subject_id}: {e}")
        total_count = 0
    finally:
        release_pg_connection(pg_connection_pool, connection)
    return total_count

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

def weighted_question_selection(question_ids, weightage, num_questions, used_questions):
    """
    Selects questions based on chapter weightage, allowing for repetitions if necessary.

    :param question_ids: List of all question IDs eligible for selection.
    :param weightage: Dictionary mapping chapter IDs to their weightage.
    :param num_questions: Number of questions to select.
    :param used_questions: Set of question IDs that have been used previously.
    :return: List of selected question IDs.
    """
    question_ids = list(set(question_ids))
    # Fetch chapter IDs for all questions
    chapter_ids_for_questions = get_chapter_ids_for_questions(question_ids)

    # Calculate total weightage for normalization
    total_weightage = sum(weightage.values())

    # Normalize weightage for each chapter
    normalized_weightage = {chapter_id: weight / total_weightage for chapter_id, weight in weightage.items()}

    # Prepare a weighted list of questions for selection
    weighted_questions = []
    for question_id in question_ids:
        chapter_id = chapter_ids_for_questions.get(question_id)
        if chapter_id and chapter_id in normalized_weightage:
            # The number of times a question is added is proportional to its chapter's weightage
            repetitions = int(normalized_weightage[chapter_id] * 100)
            weighted_questions += [question_id] * repetitions

    # If the weighted list has enough questions for selection, perform the selection
    if len(weighted_questions) >= num_questions:
        selected_questions = list(set(random.sample(weighted_questions, num_questions)))
    else:
        # If not enough questions in the weighted list, fill the remainder with random choices, allowing repetitions
        remainder = num_questions - len(weighted_questions)

        additional_questions = set(random.choices(question_ids, k=remainder))
        selected_questions = weighted_questions + list(additional_questions)
    return selected_questions

def get_chapter_ids_for_questions(question_ids):
    """
    Retrieves the chapter IDs for a given list of question IDs.

    :param question_ids: List of question IDs.
    :return: Dictionary of question IDs to their corresponding chapter IDs.
    """
    chapter_ids_for_questions = {}
    if not question_ids:
        return chapter_ids_for_questions

    connection = create_pg_connection(pg_connection_pool)
    try:
        with connection.cursor() as cursor:
            format_strings = ','.join(['%s'] * len(question_ids))
            cursor.execute(f"SELECT QuestionID, ChapterID FROM Questions WHERE QuestionID IN ({format_strings})", tuple(question_ids))
            for question_id, chapter_id in cursor.fetchall():
                chapter_ids_for_questions[question_id] = chapter_id
    except Exception as e:
        print(f"Error fetching chapter IDs for questions: {e}")
    finally:
        release_pg_connection(pg_connection_pool, connection)

    return chapter_ids_for_questions

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
        print("Before insert questions_data set len", len(questions_data))
        print("QDATA----",questions_data)
        # Bulk insert selected questions into NEETMockTestQuestions with section info, ignoring duplicates
        # insert_query = """
        # INSERT INTO NEETMockTestQuestions (MockTestID, QuestionID, Section) VALUES %s
        # ON CONFLICT (MockTestID, QuestionID) DO NOTHING
        # """
        try:
            insert_query = """
            INSERT INTO NEETMockTestQuestions (MockTestID, QuestionID, Section) VALUES %s
            """
            psycopg2.extras.execute_values(cursor, insert_query, questions_data)
        except Exception as e:
            print("Error", e)

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

def get_mock_test_questions(test_instance_id, student_id):
    """
    Retrieves all question details for a given mock test instance, categorized by subject and section,
    for a specific student, using the test instance ID.

    :param test_instance_id: ID of the test instance.
    :param student_id: ID of the student.
    :return: Dictionary with subject-wise and section-wise question details.
    """
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return None, "Database connection failed"

    questions_dict = {}

    try:
        with conn.cursor() as cur:
            # First, get the MockTestID from the TestInstances table
            cur.execute("""
                SELECT TestID
                FROM TestInstances
                WHERE TestInstanceID = %s AND StudentID = %s AND TestType = 'Mock'
            """, (test_instance_id, student_id))
            
            result = cur.fetchone()
            if not result:
                return None, "No MockTestID found for the given TestInstanceID and StudentID."

            mock_test_id = result[0]

            # Fetch all question details using MockTestID in a single query
            cur.execute("""
                SELECT s.SubjectName, mtq.Section, q.QuestionID, q.Question, q.OptionA, q.OptionB, q.OptionC, q.OptionD, i.ImageURL, i.ContentType
                FROM NEETMockTestQuestions mtq
                JOIN Questions q ON mtq.QuestionID = q.QuestionID
                LEFT JOIN Images i ON q.QuestionID = i.QuestionID
                JOIN Chapters c ON q.ChapterID = c.ChapterID
                JOIN Subjects s ON c.SubjectID = s.SubjectID
                WHERE mtq.MockTestID = %s
                ORDER BY s.SubjectName, mtq.Section, q.QuestionID
            """, (mock_test_id,))

            for row in cur.fetchall():
                subject_name, section, question_id, question, option_a, option_b, option_c, option_d, image_url, content_type = row

                if subject_name not in questions_dict:
                    questions_dict[subject_name] = {"SectionA": [], "SectionB": []}

                section_key = "SectionA" if section == 'A' else "SectionB"

                # Organize question details
                question_details = {
                    "QuestionID": question_id,
                    "Question": question,
                    "Options": {"A": option_a, "B": option_b, "C": option_c, "D": option_d},
                    "Images": []
                }

                if image_url and content_type in ['QUE', 'OptionA', 'OptionB', 'OptionC', 'OptionD']:
                    question_details["Images"].append({"URL": image_url, "Type": content_type})

                # To avoid adding duplicate images, only add unique question details
                if question_details not in questions_dict[subject_name][section_key]:
                    questions_dict[subject_name][section_key].append(question_details)

    except Exception as e:
        print(f"Error fetching questions for mock test instance: {e}")
        return None, str(e)
    finally:
        release_pg_connection(pg_connection_pool, conn)

    return questions_dict, None



def get_questions_id_for_mock_test(testInstanceID, student_id):
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
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            # Retrieve MockTestID from TestInstances
            cur.execute("""
                SELECT TestID FROM TestInstances
                WHERE TestInstanceID = %s AND StudentID = %s
            """, (testInstanceID, student_id))
            mock_test_result = cur.fetchone()
            if mock_test_result is None:
                return None, "Mock test not found"
            mock_test_id = mock_test_result[0]

            # Record each student response
            for composite_key, response in answers.items():
                _, _, question_id = composite_key.split('_')
                student_response = response.get('answer', 'n')  # Default to 'n' if not provided
                answering_time = response.get('time', 60)  # Default time if not provided
                cur.execute("""
                    INSERT INTO StudentResponses (TestInstanceID, StudentID, QuestionID, StudentResponse, AnsweringTimeInSeconds)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (TestInstanceID, StudentID, QuestionID)
                    DO UPDATE SET 
                        StudentResponse = EXCLUDED.StudentResponse,
                        AnsweringTimeInSeconds = EXCLUDED.AnsweringTimeInSeconds,
                        ResponseDate = CURRENT_TIMESTAMP
                """, (testInstanceID, student_id, int(question_id), student_response, answering_time))

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
            return {"message": "Submission successful"}, None
    except Exception as e:
        conn.rollback()
        return None, str(e)
    finally:
        release_pg_connection(pg_connection_pool, conn)