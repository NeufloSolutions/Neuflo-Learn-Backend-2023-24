from fastapi import FastAPI, HTTPException, Query, Header, Body, Response
from typing import List, Dict, Union, Any
from fastapi.responses import StreamingResponse
from pydantic import BaseModel
import os
from Backend.dbconfig.db_connection import create_pg_connection, release_pg_connection, pg_connection_pool
from Backend.dbconfig.cache_management import clear_student_cache, delete_all_test_data  
from Backend.practice.practice_test_management import generate_practice_test, get_practice_test_details, get_practice_test_question_ids,get_practice_test_questions, submit_practice_test_answers
from Backend.testmanagement.question_management import get_unique_student_ids, get_question_details, get_answer, list_tests_for_student,get_chapter_names, get_test_completion
from Backend.testmanagement.test_result_calculation import calculate_test_results, calculate_section_practice_test_results
from Backend.testmanagement.student_proficiency import set_student_target_score, get_student_test_history, student_test_history_in_excel, get_chapter_proficiency, get_subtopic_proficiency, calculate_chapterwise_report
from Backend.practice.practice_answer_retrieval import get_practice_test_answers_only
from Backend.mock.mock_test_management import generate_mock_test, get_questions_id_for_mock_test, submit_mock_test_answers, get_mock_test_questions
from Backend.mock.mock_answer_retrieval import get_mock_test_answers_only, report_app_issue
from Backend.customtest.custom_test_management import generate_custom_test
from Backend.chatsystem.chatbot import prepare_and_chat_with_neet_instructor
from Backend.testmanagement.question_management import add_question_issue
from fastapi.middleware.cors import CORSMiddleware
from Backend.logging import LogLatencyMiddleware
from fastapi.responses import JSONResponse
from starlette.requests import Request
from fastapi.responses import FileResponse
import traceback
from opencensus.ext.azure.trace_exporter import AzureExporter
from opencensus.trace.tracer import Tracer
from opencensus.trace.samplers import ProbabilitySampler
from opencensus.ext.azure.log_exporter import AzureLogHandler
import logging
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from azure.monitor.opentelemetry import configure_azure_monitor
from opentelemetry import trace
from opentelemetry.trace import (
    get_tracer_provider,
)

from opentelemetry.propagate import extract
from logging import getLogger, INFO

os.environ["APPLICATIONINSIGHTS_CONNECTION_STRING"] = r"InstrumentationKey=66db3b47-d39b-47e4-8430-e5e04da1435c;IngestionEndpoint=https://centralindia-0.in.applicationinsights.azure.com/;LiveEndpoint=https://centralindia.livediagnostics.monitor.azure.com/"

if os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING"):
    configure_azure_monitor(
        connection_string=os.getenv("APPLICATIONINSIGHTS_CONNECTION_STRING")
    )

tracer = trace.get_tracer(__name__,
                          tracer_provider=get_tracer_provider())

logger = getLogger(__name__)

app = FastAPI()
app.add_middleware(LogLatencyMiddleware)
FastAPIInstrumentor.instrument_app(app)

origins = [
    "https://neuflo-learn.netlify.app",
    # Add other origins here if necessary
]

# Add CORSMiddleware to the application
app.add_middleware(
    CORSMiddleware,
    allow_origins=origins,  # Allows only specified origins
    allow_credentials=True,
    allow_methods=["*"],  # Allows all methods
    allow_headers=["*"],  # Allows all headers
)

@app.exception_handler(HTTPException)
async def http_exception_handler(request: Request, exc: HTTPException):
    # Log the error details using the configured logger
    error_message = f"Error: {exc.detail}"
    logger.error(error_message, exc_info=True)  # Log with stack trace
    # Return the original error response
    return JSONResponse(status_code=exc.status_code, content={"detail": exc.detail})


@app.get("/")
def read_root():
    return {"message": "Welcome to the NEET Exam Preparation API"}

@app.get("/favicon.ico")
async def favicon():
    return FileResponse("favicon.ico")

@app.get("/unique-student-ids/") 
async def api_get_unique_student_ids():
    student_ids, error = get_unique_student_ids()
    if error:
        raise HTTPException(status_code=500, detail=error)
    return {"student_ids": student_ids}

@app.get("/list-tests")
def api_list_tests_for_student(student_id: int = Query(...)):
    """
    Endpoint to list all tests for a specific student.

    - Path Parameter:
      - student_id: The unique identifier of the student.

    - Returns:
      On success: A JSON object containing a list of tests with their completion status.
      On failure: An error message.
    """
    tests, error = list_tests_for_student(student_id)
    if error:
        return {"error": error}
    return {"tests": tests}

class StudentIdModel(BaseModel):
    student_id: int

@app.post("/generate-practice-test")
async def api_generate_practice_test(student_data: StudentIdModel):
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
    result, error = generate_practice_test(student_data.student_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    
    # Update the return statement to provide more detailed information about the generated practice test
    return {
        "message": "Practice test generated successfully",
        "testInstanceID": result["testInstanceID"],
        "subject_tests": result["subject_tests"]  # Assuming 'result' contains detailed info about subject-wise tests
    }

@app.get("/practice-test/questions")
async def api_get_practice_test_question_ids(testInstanceID: int = Query(...), student_id: int = Query(...)):
    subject_questions, error = get_practice_test_question_ids(testInstanceID, student_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return subject_questions

class PracticeTestRequest(BaseModel):
    test_instance_id: int
    student_id: int

@app.post("/get-practice-test-questions", response_model=Any)
async def get_practice_test_questions_endpoint(request: PracticeTestRequest):
    # Unpack the request body
    test_instance_id = request.test_instance_id
    student_id = request.student_id

    # Call the function with the provided input
    questions, error = get_practice_test_questions(test_instance_id, student_id)

    if error:
        raise HTTPException(status_code=500, detail=error)
    
    return questions


@app.get("/get-practice-test-answers")
async def api_get_practice_test_answers_only(testInstanceID: int = Query(...), student_id: int = Query(...), subject_id: int = Query(...)):
    answers, error = get_practice_test_answers_only(testInstanceID, student_id, subject_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return answers

class PracticeTestAnswers(BaseModel):
    student_id: int
    testInstanceID: int
    subject_test_id: int
    answers: dict
    
@app.post("/submit-practice-test-answers/")
def api_submit_practice_test_answers(answers_data: PracticeTestAnswers):
    result = submit_practice_test_answers(
        answers_data.student_id, 
        answers_data.testInstanceID, 
        answers_data.subject_test_id, 
        answers_data.answers
    )
    if result is None or isinstance(result, str):
        return {"error": result or "An error occurred"}
    return result

class SectionTestResultsInput(BaseModel):
    student_id: int
    test_instance_id: int
    subject_code: int

@app.post("/calculate-practice-test-results-subjectwise/")
async def calculate_section_test_results(input_data: SectionTestResultsInput):
    result, error = calculate_section_practice_test_results(
        input_data.student_id, input_data.test_instance_id, input_data.subject_code
    )
    if error:
        raise HTTPException(status_code=400, detail=error)
    return result


class TestResultsRequest(BaseModel):
    student_id: int
    test_instance_id: int

@app.post("/test-results")
async def get_test_results(request_data: TestResultsRequest):
    # Extract data from request body
    student_id = request_data.student_id
    test_instance_id = request_data.test_instance_id

    conn = create_pg_connection(pg_connection_pool)
    if conn is None:
        raise HTTPException(status_code=500, detail="Database connection failed")
    
    try:
        result = calculate_test_results(student_id, test_instance_id)
        if isinstance(result, tuple) and len(result) == 2:
            results, error = result
            if error:
                raise HTTPException(status_code=404, detail=error)
            return results
        else:
            # Handle unexpected return value
            raise HTTPException(status_code=500, detail="Unexpected error occurred")
    finally:
        # Release the connection back to the pool
        release_pg_connection(pg_connection_pool, conn)

class PracticeTestDetailsRequest(BaseModel):
    instance_id: int
    student_id: int

@app.post("/get-practice-test-details/")
async def api_get_practice_test_details(request: PracticeTestDetailsRequest) -> Dict:
    try:
        # Call the previously defined function with the values from the request
        details = get_practice_test_details(request.instance_id, request.student_id)
        
        # Return the details as JSON
        return {"details": details}
    except Exception as e:
        # If something goes wrong, return an HTTP error response
        raise HTTPException(status_code=500, detail=str(e))

######################################################################################################

@app.post("/generate-mock-test")
async def generate_mock_test_endpoint(student_data: StudentIdModel):
    """
    Endpoint to generate a mock test for a given student.
    """
    try:
        result = generate_mock_test(student_data.student_id)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))


class QuestionModel(BaseModel):
    questions: Dict[str, Dict[str, List[int]]]

@app.get("/get-mock-questions")
async def get_mock_questions_endpoint(testInstanceID: int = Query(...), student_id: int = Query(...)):
    try:
        questions = get_questions_id_for_mock_test(testInstanceID, student_id)
        return {"questions": questions}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

class MockTestRequest(BaseModel):
    test_instance_id: int
    student_id: int

@app.post("/get-mock-test-questions", response_model=Any)
async def get_mock_test_questions_endpoint(request: MockTestRequest):
    # Call the function with the provided input
    questions, error = get_mock_test_questions(request.test_instance_id, request.student_id)

    if error:
        raise HTTPException(status_code=500, detail=error)
    
    return questions

@app.get("/get-mock-test-answers")
def api_get_mock_test_answers(testInstanceID: int = Query(...), student_id: int = Query(...)):
    """
    Endpoint to retrieve answers for a mock test.

    - Path Parameters:
      - testInstanceID: The unique identifier of the test instance.
      - student_id: The unique identifier of the student.
    
    - Returns:
      On success: A JSON object containing a list of answers.
      On failure: An error message.
    """
    answers, error = get_mock_test_answers_only(testInstanceID, student_id)
    if error:
        return {"error": error}
    return {"answers": answers['answers']}

class MockTestAnswers(BaseModel):
    student_id: int
    testInstanceID: int
    data: dict

@app.post("/submit-mock-test-answers")
def api_submit_mock_test_answers(answers_data: MockTestAnswers):
    """
    Endpoint to submit answers for a mock test.

    - Path Parameters:
      - student_id: The unique identifier of the student.
      - testInstanceID: The unique identifier of the test instance.

    - Request Body:
      - data: A dictionary containing a key "answers" with a value that is another dictionary.
             The inner dictionary's keys are composites of subject ID, section, and question ID,
             and values are dictionaries containing the student's answer and the time taken.
    
    - Returns:
      On success: A JSON object indicating successful submission.
      On failure: An error message.
    """
    result, error = submit_mock_test_answers(
        answers_data.student_id, 
        answers_data.testInstanceID, 
        answers_data.data
    )
    if error:
        return {"error": error}
    return result

class CustomTestRequest(BaseModel):
    chapter_ids: List[int]
    total_questions: int

@app.post("/generate-custom-test/")
async def generate_custom_test_endpoint(request: CustomTestRequest):
    response, error = generate_custom_test(request.chapter_ids, request.total_questions)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return response

######################################################################################################

@app.post("/chat/")
async def chat_endpoint(new_question: str = Body(..., embed=True), past_history: list = Body(default=[], embed=True)):
    """
    FastAPI endpoint to interact with a NEET instructor via OpenAI's ChatGPT model.
    Expects a JSON body with a new question and optional past history.
    """
    try:
        response = prepare_and_chat_with_neet_instructor(new_question, past_history)
        return {"response": response}
    except Exception as e:
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/check-test-completion")
def api_get_test_completion(instanceId: int = Query(...), studentId: int = Query(...)):
    """
    Endpoint to check if a given test instance is completed or not.

    - Query Parameter:
      - instanceId: The unique identifier of the test instance.

    - Returns:
      On success: A JSON object containing the test ID, test type, and completion status.
      On failure: An error message.
    """
    completion_status, error = get_test_completion(instanceId, studentId)
    if error:
        return {"error": error}
    return {"completion_status": completion_status}


@app.get("/student-test-history")
def api_get_student_test_history(student_id: int = Query(...)):
    # This endpoint retrieves the test history of a specific student.
    # It returns a history of all the tests (practice, mock, etc.) taken by the student identified by 'student_id'.
    # If there's an error (e.g., student not found or database error), it raises an HTTP exception with a status code of 500.
    history, error = get_student_test_history(student_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return history

@app.get("/get-student-test-history-excel")
async def get_student_test_history_excel(student_id: int = Query(...)):
    # Assuming get_student_test_history_excel is defined as shown above
    excel_file = student_test_history_in_excel(student_id)
    if excel_file is None:
        return Response(content="Error generating Excel file", status_code=500)
    
    headers = {
        "Content-Disposition": "attachment; filename=test_history.xlsx"
    }
    return StreamingResponse(excel_file, media_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", headers=headers)

@app.get("/chapter-proficiency")
def api_get_chapter_proficiency(student_id: int = Query(...)):
    # This endpoint fetches the chapter-wise proficiency for a given student.
    # It calculates and returns the student's proficiency in each chapter, 
    # which could include metrics like correct and incorrect answers, percentage score, etc., for that chapter.
    # In case of an error, it raises an HTTP exception with a status code of 500.
    proficiency, error = get_chapter_proficiency(student_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return proficiency

@app.get("/subtopic-proficiency")
def api_get_subtopic_proficiency(student_id: int = Query(...)):
    # This endpoint is responsible for providing the subtopic-wise proficiency of a student.
    # It details the student's performance in various subtopics under different chapters,
    # potentially including metrics like accuracy, number of attempts, etc., per subtopic.
    # If an error occurs, it triggers an HTTP exception with a status code of 500.
    proficiency, error = get_subtopic_proficiency(student_id)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return proficiency


@app.get("/get-question")
async def api_get_question_details(question_id: int = Query(...)):
    # This endpoint retrieves the details of a specific question based on the provided question_id.
    # It returns a dictionary containing various elements of the question, like the question text, options, and related information.
    question_details, error = get_question_details(question_id)
    if error:
        # Raises an HTTPException if there's an error in fetching the question details.
        raise HTTPException(status_code=500, detail=error)
    return question_details

class IssueReport(BaseModel):
    user_id: int
    issue_description: str

@app.post("/report-issue", response_model=Any)
async def report_issue(issue: IssueReport):
    """
    Endpoint to report an app issue.
    """
    result = report_app_issue(issue.user_id, issue.issue_description)
    if "successfully" in result:
        return {"message": result}
    else:
        raise HTTPException(status_code=500, detail=result)

@app.get("/get-answer")
def api_get_answer(question_id: int = Query(...)):
    # This endpoint provides the correct answer for a given question identified by question_id.
    # It returns the answer, which could be in various formats depending on how the answer is stored (e.g., option A, B, C, D).
    result, error = get_answer(question_id)
    if error:
        # If there is an error in retrieving the answer, an HTTPException is raised.
        raise HTTPException(status_code=500, detail=error)
    return result

class QuestionIssue(BaseModel):
    question_id: int
    issue_comment: str

@app.post("/report-question-issue")
def report_question_issue(issue: QuestionIssue):
    result = add_question_issue(issue.question_id, issue.issue_comment)
    if "successfully" in result:
        return {"message": result}
    else:
        raise HTTPException(status_code=500, detail=result)

class TargetScoreRequest(BaseModel):
    student_id: int
    target_score: int

@app.post("/set-target-score/")
async def set_target_score(request: TargetScoreRequest):
    """
    Sets or updates the target score for a given student.
    """
    success = set_student_target_score(request.student_id, request.target_score)
    if not success:
        raise HTTPException(status_code=500, detail="Failed to set/update the student's target score")
    return {"message": "Student's target score updated successfully"}

@app.get("/get-chapter-names/")
async def api_get_chapter_names(subjectID: int = Query(...)):
    """
    Endpoint to retrieve chapter names based on the subject ID.
    """
    chapter_names, error = get_chapter_names(subjectID)
    if error:
        raise HTTPException(status_code=500, detail=error)
    return {"chapter_names": chapter_names}
    
@app.post("/clear-cache")
async def clear_cache(student_id: int = Query(...)):
    # This endpoint clears the cache for a specific student identified by student_id.
    # It is useful for ensuring that the student's latest data is fetched from the database rather than using outdated cached data.
    try:
        clear_student_cache(student_id)
        return {"message": f"Cache cleared for student {student_id}"}
    except Exception as e:
        # If any exception occurs during cache clearing, an HTTPException is raised.
        raise HTTPException(status_code=500, detail=str(e))

@app.post("/reset-database")
async def reset_database():
    # This endpoint resets the database for the entire application and clears the cache for a specific student.
    try:
        # First, clear the cache for the specific student
        clear_student_cache()
        # Then, reset the database by clearing all specified tables
        reset_result = delete_all_test_data()
        return {"message": f"Database reset successfully"}
    except Exception as e:
        # If any exception occurs, raise an HTTPException
        raise HTTPException(status_code=500, detail=str(e))

@app.get("/admin/host/ping")
async def ping():
    return {"message": "pong"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=5945)