# db_connection.py
import psycopg2
from psycopg2 import pool
import redis
from Backend.dbconfig.config import DB_CONFIG

# Initialize the connection pool for PostgreSQL
def init_pg_connection_pool():
    connection_pool = pool.SimpleConnectionPool(1, 10, **DB_CONFIG)
    if connection_pool.closed:
        print("Failed to create the PostgreSQL connection pool")
    return connection_pool

# Initialize Redis client
def init_redis_client():
    return redis.Redis(host='localhost', port=6379, db=0)

# Function to create and return a new PostgreSQL connection
def create_pg_connection(connection_pool):
    try:
        return connection_pool.getconn()
    except (Exception, psycopg2.DatabaseError) as error:
        print(error)
        return None

# Function to release a PostgreSQL connection back to the pool
def release_pg_connection(connection_pool, connection):
    if connection:
        connection_pool.putconn(connection)

# Initialize connection pools and clients
pg_connection_pool = init_pg_connection_pool()
redis_client = init_redis_client()
