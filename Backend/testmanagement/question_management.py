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
