import json
from db_connection import redis_client

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
