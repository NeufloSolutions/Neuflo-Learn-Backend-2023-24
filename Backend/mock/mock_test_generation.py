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
    # Assuming subject IDs for Physics, Chemistry, Botany, and Zoology are 1, 2, 3, and 4
    subject_ids = [1, 2, 3, 4]
    mock_test_questions = []

    # Select questions for each subject and section
    for subject_id in subject_ids:
        for section in ['A', 'B']:
            questions = select_questions_for_subject(subject_id, student_id, section)
            mock_test_questions.extend(questions)

    print(f"Total questions selected for the mock test: {len(mock_test_questions)}")

    # Create test instance and return the response
    test_instance_id = create_test_instance(student_id, mock_test_questions)
    if test_instance_id:
        return {"message": "Mock test generated successfully", "testInstanceID": test_instance_id}
    else:
        return {"message": "Error in generating mock test", "testInstanceID": None}

def get_chapter_id_for_question(question_id):
    """
    Retrieves the chapter ID for a given question ID.
    
    :param question_id: ID of the question.
    :return: ID of the chapter.
    """
    connection = create_pg_connection(pg_connection_pool)
    cursor = connection.cursor()
    try:
        cursor.execute("SELECT ChapterID FROM Questions WHERE QuestionID = %s", (question_id,))
        result = cursor.fetchone()
        return result[0] if result else None
    except Exception as e:
        print(f"Error fetching chapter ID for question {question_id}: {e}")
        return None
    finally:
        release_pg_connection(pg_connection_pool, connection)

def select_questions_for_subject(subject_id, student_id, section):
    """
    Selects questions for a given subject and section, considering the student's history
    and chapter weightage.
    
    :param subject_id: ID of the subject.
    :param student_id: ID of the student.
    :param section: Section of the test ('A' or 'B').
    :return: List of selected question IDs.
    """

    # Define the number of questions to select for each section
    num_questions = 35 if section == 'A' else 15  # 35 for Section A, 15 for Section B

    # Retrieve the student's history of attempted questions
    used_questions = set(get_cached_questions(student_id))
    print(f"Used questions for student {student_id}: {used_questions}")
    

    # Fetch chapters and their weightages for the subject
    chapters_weightage = get_chapter_weightage(subject_id)
    print(chapters_weightage)

    # Fetch all questions for the subject, excluding ones the student has already attempted
    all_questions = get_questions_for_subject(subject_id, used_questions)

    # Select questions based on chapter weightage
    selected_questions = weighted_question_selection(all_questions, chapters_weightage, num_questions)
    print(selected_questions)

    # Update the cache with the newly selected questions
    updated_used_questions = used_questions | set(selected_questions)
    cache_questions(student_id, list(updated_used_questions))  # Converting back to list
    
    print(f"Selected questions for subject {subject_id}, section {section}: {selected_questions}")

    return selected_questions


def create_test_instance(student_id, question_ids_with_sections):
    """
    Enhanced version of create_test_instance for better efficiency and error handling.
    
    :param student_id: ID of the student.
    :param question_ids_with_sections: List of tuples with selected question IDs and their sections.
    :return: ID of the created test instance.
    """
    connection = create_pg_connection(pg_connection_pool)
    cursor = connection.cursor()

    try:
        # Insert a new mock test instance and get its MockTestID
        cursor.execute("INSERT INTO NEETMockTests (StudentID) VALUES (%s) RETURNING MockTestID", (student_id,))
        mock_test_id = cursor.fetchone()[0]

        # Prepare data for bulk insert
        questions_data = [(mock_test_id, qid, sec) for qid, sec in question_ids_with_sections]
        
        # Bulk insert selected questions into NEETMockTestQuestions with section info
        insert_query = "INSERT INTO NEETMockTestQuestions (MockTestID, QuestionID, Section) VALUES %s"
        psycopg2.extras.execute_values(cursor, insert_query, questions_data)

        # Record the test instance and get its TestInstanceID
        cursor.execute("INSERT INTO TestInstances (StudentID, TestID, TestType) VALUES (%s, %s, 'Mock') RETURNING TestInstanceID", (student_id, mock_test_id))
        test_instance_id = cursor.fetchone()[0]

        # Commit the transaction
        connection.commit()

        return test_instance_id

    except Exception as e:
        print(f"Error creating test instance: {e}")
        connection.rollback()
        return None
    finally:
        release_pg_connection(pg_connection_pool, connection)

def get_chapter_weightage(subject_id):
    """
    Retrieves the weightage for chapters in a subject.
    
    :param subject_id: ID of the subject.
    :return: Dictionary of chapter ID to weightage.
    """
    connection = create_pg_connection(pg_connection_pool)
    cursor = connection.cursor()
    weightages = {}

    try:
        cursor.execute("SELECT ChapterID, Weightage FROM MockTestChapterWeightage WHERE SubjectID = %s", (subject_id,))
        for chapter_id, weightage in cursor.fetchall():
            weightages[chapter_id] = weightage
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


import numpy as np

def weighted_question_selection(question_ids, weightage, num_questions):
    """
    Selects questions based on chapter weightage.
    
    :param question_ids: List of question IDs.
    :param weightage: Dictionary of chapter ID to weightage.
    :param num_questions: Number of questions to select.
    :return: List of selected question IDs.
    """
    if not question_ids:
        return []

    # Create a list of chapter IDs for each question
    chapter_ids_for_questions = [get_chapter_id_for_question(qid) for qid in question_ids]

    # Convert weightage to a list of weights corresponding to each question
    weights = [weightage.get(ch_id, 0) for ch_id in chapter_ids_for_questions]

    # Normalize the weights to sum to 1
    total_weight = sum(weights)
    if total_weight > 0:
        normalized_weights = [w / total_weight for w in weights]
    else:
        # If total weight is 0 (to avoid division by zero), use equal weights
        normalized_weights = [1 / len(weights)] * len(weights)

    # Use numpy's choice function for weighted random selection
    selected_indices = np.random.choice(len(question_ids), size=num_questions, replace=False, p=normalized_weights)
    selected_questions = [question_ids[i] for i in selected_indices]

    return selected_questions



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

def get_questions_for_mock_test_instance(mock_test_id):
    """
    Retrieves all question IDs for a given mock test instance, categorized by subject and section.
    
    :param mock_test_id: ID of the mock test instance.
    :return: Dictionary with subject-wise and section-wise question IDs.
    """
    connection = create_pg_connection(pg_connection_pool)
    cursor = connection.cursor()
    questions_dict = {}

    try:
        query = """
        SELECT s.SubjectName, q.Section, q.QuestionID 
        FROM NEETMockTestQuestions mtq
        JOIN Questions q ON mtq.QuestionID = q.QuestionID
        JOIN Chapters c ON q.ChapterID = c.ChapterID
        JOIN Subjects s ON c.SubjectID = s.SubjectID
        WHERE mtq.MockTestID = %s
        """
        cursor.execute(query, (mock_test_id,))
        for subject_name, section, question_id in cursor.fetchall():
            if subject_name not in questions_dict:
                questions_dict[subject_name] = {"SectionA": [], "SectionB": []}
            if section == 'A':
                questions_dict[subject_name]["SectionA"].append(question_id)
            else:
                questions_dict[subject_name]["SectionB"].append(question_id)
    except Exception as e:
        print(f"Error fetching questions for mock test instance: {e}")
    finally:
        release_pg_connection(pg_connection_pool, connection)

    return questions_dict