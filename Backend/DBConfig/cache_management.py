import json
from Backend.dbconfig.db_connection import redis_client
from Backend.dbconfig.db_connection import create_pg_connection, release_pg_connection, pg_connection_pool

# def get_cached_questions(student_id):
#     """
#     Retrieve cached questions for a given student from Redis.
#     """
#     cached_data = redis_client.get(str(student_id))
#     if cached_data:
#         return json.loads(cached_data)
#     else:
#         return {}

# def cache_questions(student_id, used_questions):
#     """
#     Cache questions used by a student in Redis.
#     """
#     redis_client.set(str(student_id), json.dumps(used_questions))

# def clear_student_cache(student_id=None):
#     """
#     Clear all cached data in Redis.
#     If a specific student_id is provided, clear only that student's data.
#     If no student_id is provided, clear all cache.
#     """
#     if student_id is None:
#         # Clear entire Redis cache
#         redis_client.flushall()
#         return "All cache cleared."
#     else:
#         # Clear cache for specific student
#         redis_client.delete(str(student_id))
#         return f"Cache cleared for student {student_id}."


def get_cached_questions(student_id, test_type):
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return []
    try:
        with conn.cursor() as cur:
            cur.execute("SELECT cached_questions FROM question_cache WHERE student_id = %s AND test_type = %s", (student_id, test_type))
            result = cur.fetchone()
            if result and result[0]:
                # Assuming the structure to be a flat list of question IDs
                return result[0]
            else:
                return []
    except Exception as e:
        print(f"Error retrieving cached questions for student_id {student_id} and test_type {test_type}: {e}")
        return []
    finally:
        release_pg_connection(pg_connection_pool, conn)

def cache_questions(student_id, test_type, used_questions):
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return "Database connection failed"
    try:
        with conn.cursor() as cur:
            # Assuming used_questions is a list of question IDs
            json_used_questions = json.dumps(used_questions)
            cur.execute("""
                INSERT INTO question_cache (student_id, test_type, cached_questions)
                VALUES (%s, %s, %s::jsonb)
                ON CONFLICT (student_id, test_type) DO UPDATE
                SET cached_questions = EXCLUDED.cached_questions, last_updated = CURRENT_TIMESTAMP
            """, (student_id, test_type, json_used_questions))
            conn.commit()
    finally:
        release_pg_connection(pg_connection_pool, conn)



def clear_student_cache(student_id=None, test_type=None):
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return "Database connection failed"
    try:
        with conn.cursor() as cur:
            if student_id is None:
                cur.execute("TRUNCATE TABLE question_cache")
            elif test_type is None:
                cur.execute("DELETE FROM question_cache WHERE student_id = %s", (student_id,))
            else:
                cur.execute("DELETE FROM question_cache WHERE student_id = %s AND test_type = %s", (student_id, test_type))
            conn.commit()
            return "Cache cleared successfully."
    finally:
        release_pg_connection(pg_connection_pool, conn)



def delete_all_test_data():
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return "Database connection failed"

    try:
        with conn.cursor() as cur:
            # List of tables to be cleared
            tables_to_clear = [
                "PracticeTests", "PracticeTestSubjects", "PracticeTestQuestions",
                "PracticeTestCompletion", "NEETMockTests", "NEETMockTestQuestions", "StudentMockTestHistory",
                "testinstances", "StudentResponses", "TestHistory", "ChapterProficiency",
                "SubtopicProficiency", "StudentTestTargets", "PracticeTestProficiency",
                "MockTestProficiency"
            ]

            # Executing delete statements for each table
            for table in tables_to_clear:
                cur.execute(f"TRUNCATE {table} CASCADE")
            print(f"Cleared data from all tables")

            # Commit the changes
            conn.commit()
            return "All test data cleared successfully"

    except Exception as e:
        conn.rollback()
        return f"An error occurred: {str(e)}"
    finally:
        if conn:
            release_pg_connection(pg_connection_pool, conn)