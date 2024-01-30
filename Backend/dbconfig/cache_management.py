import json
from Backend.dbconfig.db_connection import redis_client
from Backend.dbconfig.db_connection import create_pg_connection, release_pg_connection, pg_connection_pool

def get_cached_questions(student_id):
    """
    Retrieve cached questions for a given student from Redis.
    """
    cached_data = redis_client.get(str(student_id))
    if cached_data:
        return json.loads(cached_data)
    else:
        return {} 

def cache_questions(student_id, used_questions):
    """
    Cache questions used by a student in Redis.
    """
    redis_client.set(str(student_id), json.dumps(used_questions))

def clear_student_cache(student_id=None):
    """
    Clear all cached data in Redis.
    If a specific student_id is provided, clear only that student's data.
    If no student_id is provided, clear all cache.
    """
    if student_id is None:
        # Clear entire Redis cache
        redis_client.flushall()
        return "All cache cleared."
    else:
        # Clear cache for specific student
        redis_client.delete(str(student_id))
        return f"Cache cleared for student {student_id}."


def delete_all_test_data():
    conn = create_pg_connection(pg_connection_pool)
    if not conn:
        return "Database connection failed"

    try:
        with conn.cursor() as cur:
            # List of tables to be cleared
            tables_to_clear = [
                "PracticeTests", "PracticeTestSubjects", "PracticeTestQuestions",
                "PracticeTestCompletion", "NEETMockTests", "NEETMockTestQuestions",
                "MockTestChapterWeightage", "MockTestConfiguration", "StudentMockTestHistory",
                "TestInstances", "StudentResponses", "TestHistory", "ChapterProficiency",
                "SubtopicProficiency", "StudentTestTargets", "PracticeTestProficiency",
                "MockTestProficiency"
            ]

            # Executing delete statements for each table
            for table in tables_to_clear:
                cur.execute(f"DELETE FROM {table};")
                print(f"Cleared data from {table}")

            # Commit the changes
            conn.commit()
            return "All test data cleared successfully"

    except Exception as e:
        conn.rollback()
        return f"An error occurred: {str(e)}"
    finally:
        if conn:
            release_pg_connection(pg_connection_pool, conn)