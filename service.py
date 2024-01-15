from fastapi import FastAPI, HTTPException
from typing import List, Dict, Union
from pydantic import BaseModel
from Backend.db_connection import create_pg_connection, release_pg_connection, pg_connection_pool
from Backend.cache_management import get_cached_questions, cache_questions, clear_student_cache  
from Backend.practice_test_management import generate_practice_test, get_practice_test_question_ids, submit_practice_test_answers
from Backend.question_management import get_question_details, get_answer
from Backend.test_result_calculation import calculate_test_results
from Backend.student_proficiency import get_student_test_history, get_chapter_proficiency, get_subtopic_proficiency
from Backend.answer_retrieval import get_practice_test_answers_only


app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Welcome to the NEET Exam Preparation API"}

@app.get("/generate-practice-test/{student_id}")
async def api_generate_practice_test(student_id: int):
    """
    Endpoint to generate a new practice test for a given student.
    
    - Path Parameter:
      - student_id: The unique identifier of the student for whom the practice test is being generated.
    
    - Functionality:
      This endpoint calls the generate_practice_test function, which is responsible for creating a new 
      practice test based on the updated NEET syllabus structure. The practice test comprises subject-wise tests 
      for Biology (divided into Botany and Zoology), Chemistry, and Physics. Each subject test will have a 
      specific number of questions as defined in the updated requirements.

    - Returns:
      On success: A JSON object containing details of the generated practice test, including the practice test ID,
                  and the structure of the subject-wise tests.
      On failure: An HTTPException with status code 500 indicating an internal server error.
    """
    result, error = generate_practice_test(student_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    
    # Update the return statement to provide more detailed information about the generated practice test
    return {
        "message": "Practice test generated successfully",
        "practice_test_id": result["practice_test_id"],
        "subject_tests": result["subject_tests"]  # Assuming 'result' contains detailed info about subject-wise tests
    }


@app.get("/practice-test/{practice_test_id}/questions", response_model=Dict[str, List[int]])
async def api_get_practice_test_question_ids(practice_test_id: int, student_id: int):
    subject_questions, error = get_practice_test_question_ids(practice_test_id, student_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return subject_questions

@app.get("/get-practice-test-answers/", response_model=List)
async def api_get_practice_test_answers_only(test_id: int, student_id: int, subject_id: int):
    answers, error = get_practice_test_answers_only(test_id, student_id, subject_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return answers

@app.post("/submit-practice-test-answers/{student_id}/{test_id}/{subject_test_id}")
def api_submit_practice_test_answers(student_id: int, test_id: int, subject_test_id: int, answers: dict):
    result = submit_practice_test_answers(student_id, test_id, subject_test_id, answers)
    if result is None or isinstance(result, str):
        return {"error": result or "An error occurred"}
    return result

@app.post("/test-results/{student_id}/{test_instance_id}")
async def get_test_results(student_id: int, test_instance_id: int):
    conn = create_pg_connection(pg_connection_pool)
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        results, error = calculate_test_results(student_id, test_instance_id)
        if error:
            raise HTTPException(status_code=404, detail=error)
        return results
    finally:
        # Release the connection back to the pool
        release_pg_connection(pg_connection_pool, conn)

@app.get("/student-test-history/{student_id}")
def api_get_student_test_history(student_id: int):
    # This endpoint retrieves the test history of a specific student.
    # It returns a history of all the tests (practice, mock, etc.) taken by the student identified by 'student_id'.
    # If there's an error (e.g., student not found or database error), it raises an HTTP exception with a status code of 500.
    history, error = get_student_test_history(student_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return history

@app.get("/chapter-proficiency/{student_id}")
def api_get_chapter_proficiency(student_id: int):
    # This endpoint fetches the chapter-wise proficiency for a given student.
    # It calculates and returns the student's proficiency in each chapter, 
    # which could include metrics like correct and incorrect answers, percentage score, etc., for that chapter.
    # In case of an error, it raises an HTTP exception with a status code of 500.
    proficiency, error = get_chapter_proficiency(student_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return proficiency

@app.get("/subtopic-proficiency/{student_id}")
def api_get_subtopic_proficiency(student_id: int):
    # This endpoint is responsible for providing the subtopic-wise proficiency of a student.
    # It details the student's performance in various subtopics under different chapters,
    # potentially including metrics like accuracy, number of attempts, etc., per subtopic.
    # If an error occurs, it triggers an HTTP exception with a status code of 500.
    proficiency, error = get_subtopic_proficiency(student_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return proficiency


@app.get("/questions/{question_id}/details", response_model=Dict[str, Union[str, Dict[str, str], List[Dict[str, str]]]])
async def api_get_question_details(question_id: int):
    # This endpoint retrieves the details of a specific question based on the provided question_id.
    # It returns a dictionary containing various elements of the question, like the question text, options, and related information.
    question_details, error = get_question_details(question_id)
    if error:
        # Raises an HTTPException if there's an error in fetching the question details.
        raise HTTPException(status_code=500, detail=error)
    return question_details

@app.get("/get-answer/{question_id}")
def api_get_answer(question_id: int):
    # This endpoint provides the correct answer for a given question identified by question_id.
    # It returns the answer, which could be in various formats depending on how the answer is stored (e.g., option A, B, C, D).
    result, error = get_answer(question_id)
    if error:
        # If there is an error in retrieving the answer, an HTTPException is raised.
        raise HTTPException(status_code=500, detail=error)
    return result
    
@app.post("/clear-cache/{student_id}")
async def clear_cache(student_id: int):
    # This endpoint clears the cache for a specific student identified by student_id.
    # It is useful for ensuring that the student's latest data is fetched from the database rather than using outdated cached data.
    try:
        clear_student_cache(student_id)
        return {"message": f"Cache cleared for student {student_id}"}
    except Exception as e:
        # If any exception occurs during cache clearing, an HTTPException is raised.
        raise HTTPException(status_code=500, detail=str(e))


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5912)