import random
from psycopg2.extensions import AsIs
from Backend.dbconfig.db_connection import create_pg_connection, release_pg_connection, pg_connection_pool

def get_mock_test_answers_only(test_instance_id, student_id):
    """
    Retrieve all the answers for a mock test, specific to a student, in a format with keys as 'subject_section_question'.
    The function takes in TestInstanceID and retrieves the corresponding MockTestID.
    """
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            # Retrieve MockTestID from TestInstances
            cur.execute("""
                SELECT TestID FROM TestInstances
                WHERE TestInstanceID = %s AND StudentID = %s
            """, (test_instance_id, student_id))
            mock_test_result = cur.fetchone()
            if mock_test_result is None:
                return None, "Mock test not found"
            mock_test_id = mock_test_result[0]

            # Retrieve the answers, including subject and section information
            cur.execute("""
                SELECT S.SubjectName, MTQ.Section, Q.QuestionID, Q.Answer
                FROM Questions Q
                JOIN NEETMockTestQuestions MTQ ON Q.QuestionID = MTQ.QuestionID
                JOIN Chapters C ON Q.ChapterID = C.ChapterID
                JOIN Subjects S ON C.SubjectID = S.SubjectID
                WHERE MTQ.MockTestID = %s
            """, (mock_test_id,))

            results = cur.fetchall()
            if results:
                # Organize answers in the flattened format
                organized_answers = {}
                for subject, section, question_id, answer in results:
                    subject_key = {
                        "Physics": "0",
                        "Chemistry": "1",
                        "Botany": "2",
                        "Zoology": "3"
                    }.get(subject, "Unknown")

                    composite_key = f"{subject_key}_Section{section}_{question_id}"
                    answering_time = random.randint(30, 100)  # Random answering time
                    organized_answers[composite_key] = {"answer": answer, "time": answering_time}

                return {"answers": organized_answers}, None
            else:
                return None, "No answers found for the given mock test instance ID and student ID"
    except Exception as e:
        return None, str(e)
    finally:
        release_pg_connection(pg_connection_pool, conn)


def report_app_issue(user_id, issue_description):
    """
    Report an app issue into the database.

    :param user_id: The ID of the user reporting the issue.
    :param issue_description: The description of the issue.
    :return: A message indicating success or failure.
    """
    # Establish a database connection
    conn = create_pg_connection(pg_connection_pool)
    if conn is None:
        return "Failed to connect to the database."

    try:
        # Create a cursor to perform database operations
        cur = conn.cursor()
        
        # SQL query to insert a new issue
        query = """
        INSERT INTO AppIssues (UserID, IssueDescription)
        VALUES (%s, %s);
        """
        
        # Execute the query
        cur.execute(query, (user_id, issue_description))
        
        # Commit the transaction
        conn.commit()
        
        # Close the cursor
        cur.close()
        
        return "Issue reported successfully."
    except Exception as e:
        # In case of any errors, rollback the transaction
        conn.rollback()
        return f"An error occurred: {e}"
    finally:
        # Release the connection back to the pool
        release_pg_connection(pg_connection_pool, conn)