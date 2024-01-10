from db_connection import create_pg_connection, release_pg_connection

def get_test_answers_only(test_id):
    """
    Retrieve only the answers for a given test.
    """
    conn = create_pg_connection()
    if not conn:
        return None, "Database connection failed"

    try:
        with conn.cursor() as cur:
            cur.execute("""
                SELECT Q.QuestionID, Q.Answer
                FROM Questions Q
                JOIN PracticeTestQuestions PTQ ON Q.QuestionID = PTQ.QuestionID
                WHERE PTQ.PracticeTestID = %s
            """, (test_id,))
            
            results = cur.fetchall()
            if results:
                # Extracting the question IDs and their respective answers
                answers = {result[0]: result[1] for result in results}
                return answers, None
            else:
                return None, "No answers found for the given test ID"
    except Exception as e:
        return None, str(e)
    finally:
        release_pg_connection(conn)
