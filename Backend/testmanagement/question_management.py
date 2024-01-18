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
                WHERE Q.QuestionID = %s AND (I.ContentType IS NULL OR I.ContentType IN ('QUE', 'OptionA', 'OptionB', 'OptionC', 'OptionD'))
            """, (question_id,))
            questions = cur.fetchall()

            result = {}
            for q in questions:
                if not result:
                    result = {"Question": q[0], "Options": {"A": q[1], "B": q[2], "C": q[3], "D": q[4]}, "Images": []}
                if q[5]:
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
