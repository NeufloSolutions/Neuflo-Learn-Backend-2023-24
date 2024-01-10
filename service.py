from fastapi import FastAPI, HTTPException
from typing import List, Dict, Union
from pydantic import BaseModel
from Backend.db_connection import create_pg_connection, release_pg_connection
from Backend.cache_management import get_cached_questions, cache_questions
from Backend.practice_test_management import generate_practice_test, get_practice_test_question_ids, submit_practice_test_answers

app = FastAPI()

@app.get("/")
def read_root():
    return {"message": "Welcome to the NEET Exam Preparation API"}

@app.get("/generate-practice-test/{student_id}")
async def api_generate_practice_test(student_id: int):
    result, error = generate_practice_test(student_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return result

@app.get("/practice-test/{practice_test_id}/questions", response_model=List[int])
async def api_get_practice_test_question_ids(practice_test_id: int):
    question_ids, error = get_practice_test_question_ids(practice_test_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return question_ids

@app.get("/questions/{question_id}/details", response_model=Dict[str, Union[str, Dict[str, str], List[Dict[str, str]]]])
async def api_get_question_details(question_id: int):
    question_details, error = get_question_details(question_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return question_details

@app.get("/get-answer/{question_id}")
def api_get_answer(question_id: int):
    result, error = get_answer(question_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return result

@app.get("/get-test-answers/", response_model=list[str])
async def api_get_test_answers_only(test_id: int):
    answers, error = get_test_answers_only(test_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return answers

@app.post("/submit-practice-test-answers/{student_id}/{test_id}")
def api_submit_practice_test_answers(student_id: int, test_id: int, answers: dict):
    result = submit_practice_test_answers(student_id, test_id, answers)
    if result is None or isinstance(result, str):
        return {"error": result or "An error occurred"}
    return result

class TestResult(BaseModel):
    student_id: int
    test_instance_id: int

@app.post("/test-results/")
async def get_test_results(test_result: TestResult):
    conn = create_connection()
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")

    results, error = calculate_test_results(test_result.student_id, test_result.test_instance_id)
    
    if error:
        raise HTTPException(status_code=404, detail=error)

    return results


@app.get("/student-test-history/{student_id}")
def api_get_student_test_history(student_id: int):
    history, error = get_student_test_history(student_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return history

@app.get("/chapter-proficiency/{student_id}")
def api_get_chapter_proficiency(student_id: int):
    proficiency, error = get_chapter_proficiency(student_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return proficiency

@app.get("/subtopic-proficiency/{student_id}")
def api_get_subtopic_proficiency(student_id: int):
    proficiency, error = get_subtopic_proficiency(student_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return proficiency


if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5912)