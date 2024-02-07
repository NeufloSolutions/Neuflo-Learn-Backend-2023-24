from Backend.dbconfig.db_connection import create_pg_connection, release_pg_connection, pg_connection_pool

def get_question_details(question_id):
    """
    Retrieve details for a specific question from the database.
    """
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT Q.Question, Q.OptionA, Q.OptionB, Q.OptionC, Q.OptionD, I.ImageURL, I.ContentType
                FROM Questions Q
                LEFT JOIN Images I ON Q.QuestionID = I.QuestionID
                WHERE Q.QuestionID = %s
            """, (question_id,))
            questions = cur.fetchall()

            result = {}
            for q in questions:
                if not result:
                    result = {"Question": q[0], "Options": {"A": q[1], "B": q[2], "C": q[3], "D": q[4]}, "Images": []}
                if q[5] and q[6] in ['QUE', 'OptionA', 'OptionB', 'OptionC', 'OptionD']:
                    result["Images"].append({"URL": q[5], "Type": q[6]})
            return result, None
    except Exception as e:
        return None, str(e)
    finally:
        release_pg_connection(pg_connection_pool, conn)


def get_answer(question_id):
    """
    Retrieve the answer for a specific question from the database.
    """
    conn = create_pg_connection(pg_connection_pool)
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
        release_pg_connection(pg_connection_pool, conn)


def list_tests_for_student(student_id):
    """
    List all tests for a particular student and indicate if each test is completed.

    :param student_id: ID of the student.
    :return: List of tests with completion status.
    """
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            # Retrieve all tests for the student
            cur.execute("""
                SELECT TestInstanceID, TestType, TestID
                FROM TestInstances
                WHERE StudentID = %s
            """, (student_id,))
            tests = cur.fetchall()
            
            test_list = []
            for test_instance_id, test_type, test_id in tests:
                # Check completion status based on test type
                if test_type == 'Mock':
                    completion_table = 'MockTestCompletion'
                    columnname_testid = "mocktestid"
                elif test_type == 'Practice':
                    completion_table = 'PracticeTestCompletion'
                    columnname_testid = "practicetestid"
                else:
                    continue  # Skip unknown test types
                
                # Check if the test is completed
                cur.execute(f"""
                    SELECT COUNT(*) FROM {completion_table}
                    WHERE {columnname_testid} = %s AND StudentID = %s AND IsCompleted = TRUE
                """, (test_id, student_id))
                is_completed = cur.fetchone()[0] > 0
                
                test_list.append({
                    "TestInstanceID": test_instance_id,
                    "TestID": test_id,
                    "TestType": test_type,
                    "IsCompleted": is_completed
                })
            
            return test_list, None
    except Exception as e:
        return None, str(e)
    finally:
        release_pg_connection(pg_connection_pool, conn)

def get_chapter_names(subjectID):
    """
    Retrieve chapter names from the database based on the subject ID.
    For Biology, it combines chapters from both Botany and Zoology.
    """
    # Assuming create_pg_connection and release_pg_connection are defined elsewhere
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            if subjectID in [1, 2]:  # For Physics or Chemistry
                cur.execute("""
                    SELECT ChapterID, ChapterTitle, ChapterNumber
                    FROM Chapters
                    WHERE IsActive = TRUE AND SubjectID = %s
                    ORDER BY ChapterNumber ASC;
                """, (subjectID,))
            elif subjectID == 3:  # For Biology (Botany and Zoology)
                cur.execute("""
                    SELECT ChapterID, ChapterTitle, ChapterNumber
                    FROM Chapters
                    WHERE IsActive = TRUE AND SubjectID IN (3, 4)
                    ORDER BY ChapterNumber ASC;
                """)
            else:
                return None, "Invalid subject ID"

            rows = cur.fetchall()
            if rows:
                # Convert fetched rows to a list of chapter names
                chapter_names = {row[1]:row[0] for row in rows}  # Assuming ChapterTitle is the second column
                return chapter_names, None
            else:
                return None, "No chapters found"
    except Exception as e:
        return None, str(e)
    finally:
        release_pg_connection(pg_connection_pool, conn)

def get_test_completion(instanceId, studentId):
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            # Fetch the TestID, TestType, and StudentID from TestInstances table
            cur.execute("""
                SELECT TestID, TestType FROM TestInstances WHERE TestInstanceID = %s AND StudentID = %s
            """, (instanceId, studentId,))
            test_info = cur.fetchone()

            if test_info is None:
                return None, "Test instance not found for the given student"

            test_id, test_type = test_info

            # Depending on the TestType, prepare the correct SQL query
            if test_type.lower() == 'practice':
                completion_column = "PracticeTestID"
                completion_table = "practicetestcompletion"
            elif test_type.lower() == 'mock':
                completion_column = "MockTestID"
                completion_table = "mocktestcompletion"
            else:
                return None, f"Unsupported test type: {test_type}"

            # Construct the SQL query with the correct column and table names
            query = f"""
                SELECT IsCompleted FROM {completion_table} WHERE {completion_column} = %s AND StudentID = %s
            """
            cur.execute(query, (test_id, studentId,))
            completion_info = cur.fetchone()

            if completion_info is None:
                return None, "Completion information not found for the given student"

            is_completed = completion_info[0]

            # Return the completion status
            return {"test_id": test_id, "test_type": test_type, "is_completed": is_completed, "student_id": studentId}, None
    except Exception as e:
        return None, str(e)
    finally:
        release_pg_connection(pg_connection_pool, conn)
