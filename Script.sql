--1. Subjects Table
-- This table stores information about the various subjects in the NEET syllabus.
-- Each subject has a unique SubjectID and a name (SubjectName).
CREATE TABLE IF NOT EXISTS Subjects (
    SubjectID SERIAL PRIMARY KEY,       -- A unique identifier for each subject.
    SubjectName TEXT NOT NULL );          -- The name of the subject (e.g., Physics, Chemistry).
-- Example data:
-- 1    Physics
-- 2    Chemistry
-- 3    Botany
-- 4    Zoology


--2. Chapters Table
-- This table lists the chapters for each subject, along with their titles and numbers.
-- Each chapter is linked to a subject through the SubjectID.
CREATE TABLE IF NOT EXISTS Chapters (
    ChapterID SERIAL PRIMARY KEY,       -- A unique identifier for each chapter.
    SubjectID INT NOT NULL,             -- The ID of the subject to which the chapter belongs.
    ChapterTitle TEXT NOT NULL,         -- The title of the chapter (e.g., Physical World, Units and Measurements).
    ChapterNumber INT NOT NULL,         -- The number of the chapter within its subject.
    FOREIGN KEY (SubjectID) REFERENCES Subjects(SubjectID));  -- A foreign key linking to the Subjects table.
-- Example data:
-- 1    1    Physical World, Units and Measurements   1
-- 2    1    Motion in a Straight Line                2

select count(*)from chapters;

--3. Subtopics Table
-- Contains subtopics for each chapter.
-- Each subtopic is linked to a chapter through the ChapterID.
CREATE TABLE IF NOT EXISTS Subtopics (
    SubtopicID SERIAL PRIMARY KEY,      -- A unique identifier for each subtopic.
    ChapterID INT NOT NULL,             -- The ID of the chapter to which the subtopic belongs.
    SubtopicName TEXT NOT NULL,         -- The name of the subtopic.
    FOREIGN KEY (ChapterID) REFERENCES Chapters(ChapterID));  -- A foreign key linking to the Chapters table.
-- Example data:
-- 1    1    Units of Physical Quantities
-- 2    1    Dimensions of Physical Quantities


--4. Questions Table
-- This table stores individual questions, their options, and answers.
-- Each question is linked to a chapter and optionally a subtopic.
CREATE TABLE IF NOT EXISTS Questions (
    QuestionID SERIAL PRIMARY KEY,      -- Unique identifier for each question.
    ChapterID INT NOT NULL,             -- ID of the chapter to which the question belongs.
    SubtopicID INT,                     -- ID of the subtopic to which the question belongs (optional).
    QuestionNo INT NOT NULL,            -- Question number.
    Question TEXT NOT NULL,             -- Text of the question.
    OptionA TEXT,                       -- Text for option A.
    OptionB TEXT,                       -- Text for option B.
    OptionC TEXT,                       -- Text for option C.
    OptionD TEXT,                       -- Text for option D.
    Year TEXT,                          -- Year the question appeared (to be converted to a date format).
    Answer TEXT,                        -- Correct answer(s) to the question. Values: 'a', 'b', 'c', 'd', 'na'.
    Explanation TEXT,                   -- Explanation of the answer.
    HasImage BOOLEAN DEFAULT FALSE,     -- Indicates if the question includes an image.
    FOREIGN KEY (ChapterID) REFERENCES Chapters(ChapterID),
    FOREIGN KEY (SubtopicID) REFERENCES Subtopics(SubtopicID));
-- Altering the 'Year' column from TEXT to DATE for more accurate date handling.
-- The 'to_date' function is used to convert the text to a date format (YYYY).
-- This change is important for improved sorting and filtering of questions by year.
ALTER TABLE Questions
ALTER COLUMN Year TYPE DATE USING to_date(Year, 'YYYY');



--5. Images Table
-- Stores URLs of images associated with questions.
-- Each image is linked to a question through the QuestionID.
CREATE TABLE IF NOT EXISTS Images (
    ImageID SERIAL PRIMARY KEY,         -- A unique identifier for each image.
    QuestionID INT NOT NULL,            -- The ID of the question with which the image is associated.
    ImageURL TEXT NOT NULL,             -- The URL of the image.
    ContentType TEXT NOT NULL,          -- Describes the type of content (e.g., 'Question', 'OptionA', 'OptionB', 'OptionC', 'OptionD', 'Explanation').Values:  'QUE', 'EXP', 'OptionA', 'OptionB', 'OptionC', 'OptionD'
    FOREIGN KEY (QuestionID) REFERENCES Questions(QuestionID)  -- A foreign key linking to the Questions table.
);
-- Example data:
-- 1    495    "https://neuflolearndb.blob.core.windows.net/neetimages/Physics/PHYS_10_10_EXP.jpg"    EXP
-- 2    497    "https://neuflolearndb.blob.core.windows.net/neetimages/Physics/PHYS_10_12_QUE.jpg"    QUE
-- ...


---------------------------------------------------------------------------------------------------------------------------------------------------------

--1. PracticeTests Table
-- Creates a table for storing practice test instances for each student.
-- 'PracticeTestID' is a unique identifier for each practice test instance.
-- 'StudentID' refers to the ID of the student taking the test (from an external database).
CREATE TABLE IF NOT EXISTS PracticeTests (
    PracticeTestID SERIAL PRIMARY KEY,
    StudentID INT NOT NULL
);
select * from PracticeTests;
DELETE FROM PracticeTests;
DROP TABLE IF EXISTS PracticeTests CASCADE;



--2. PracticeTestQuestions Table
-- Creates a table for associating questions with practice tests.
-- 'PracticeTestID' refers to the practice test instance.
-- 'QuestionID' refers to the specific question from the Questions table.
CREATE TABLE IF NOT EXISTS PracticeTestQuestions (
    PracticeTestID INT NOT NULL,
    QuestionID INT NOT NULL,
    PRIMARY KEY (PracticeTestID, QuestionID),
    FOREIGN KEY (PracticeTestID) REFERENCES PracticeTests(PracticeTestID),
    FOREIGN KEY (QuestionID) REFERENCES Questions(QuestionID)
);
select * from PracticeTestQuestions;
DELETE FROM PracticeTestQuestions;
DROP TABLE IF EXISTS PracticeTestQuestions CASCADE;




-- 3. NEETMockTests Table 
-- Creates a table for storing NEET mock test instances for each student.
-- 'MockTestID' is a unique identifier for each NEET mock test instance.
-- 'StudentID' refers to the ID of the student taking the test (from an external database).
CREATE TABLE IF NOT EXISTS NEETMockTests (
    MockTestID SERIAL PRIMARY KEY,
    StudentID INT NOT NULL
);
select * from NEETMockTests;
DELETE FROM NEETMockTests;
DROP TABLE IF EXISTS NEETMockTests CASCADE;



--4. NEETMockTestQuestions Table
-- Creates a table for associating questions with NEET mock tests.
-- 'MockTestID' refers to the mock test instance.
-- 'QuestionID' refers to the specific question from the Questions table.
CREATE TABLE IF NOT EXISTS NEETMockTestQuestions (
    MockTestID INT NOT NULL,
    QuestionID INT NOT NULL,
    PRIMARY KEY (MockTestID, QuestionID),
    FOREIGN KEY (MockTestID) REFERENCES NEETMockTests(MockTestID),
    FOREIGN KEY (QuestionID) REFERENCES Questions(QuestionID)
);
select * from NEETMockTestQuestions;
DELETE FROM NEETMockTestQuestions;
DROP TABLE IF EXISTS NEETMockTestQuestions CASCADE;


--5. TestInstances Table
-- This table stores each unique instance of a test taken by a student.
CREATE TABLE IF NOT EXISTS TestInstances (
    TestInstanceID SERIAL PRIMARY KEY,    -- Unique identifier for each test instance.
    StudentID INT NOT NULL,               -- ID of the student taking the test.
    TestID INT NOT NULL,                  -- ID of the specific mock or practice test.
    TestType VARCHAR(50) NOT NULL,        -- Type of the test (e.g., 'Practice', 'Mock').
    TestDateTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Date and time when the test was taken.
);
select * from TestInstances;
DELETE FROM TestInstances;
DROP TABLE IF EXISTS TestInstances CASCADE;


------------------------------------------------------------------------------------------------------------------------------

--6. StudentResponses Table
-- Creates a table for storing student responses to individual test questions.
-- 'ResponseID' is a unique identifier for each response.
-- 'TestInstanceID' links to the specific test instance from TestInstances table.
-- 'StudentID' refers to the ID of the student (from an external database).
-- 'QuestionID' links to the specific question from the Questions table.
-- 'StudentResponse' stores the option chosen by the student (A, B, C, D, etc.).
-- 'AnsweringTimeInSeconds' records the time taken by the student to answer the question.
-- 'ResponseDate' captures the timestamp when the response was recorded.
CREATE TABLE IF NOT EXISTS StudentResponses (
    ResponseID SERIAL PRIMARY KEY,
    TestInstanceID INT NOT NULL,
    StudentID INT NOT NULL,
    QuestionID INT NOT NULL,
    StudentResponse TEXT,
    AnsweringTimeInSeconds INT,
    ResponseDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (TestInstanceID, StudentID, QuestionID), -- Add a unique constraint
    FOREIGN KEY (TestInstanceID) REFERENCES TestInstances(TestInstanceID),
    FOREIGN KEY (QuestionID) REFERENCES Questions(QuestionID)
);

select * from StudentResponses;
DELETE FROM StudentResponses;
DROP TABLE IF EXISTS StudentResponses CASCADE;

--7. TestHistory Table
-- Creates a table for storing the overall history of tests taken by students.
-- 'HistoryID' is a unique identifier for each entry in the test history.
-- 'TestInstanceID' links to the specific test instance from the TestInstances table.
-- 'StudentID' refers to the ID of the student (from an external database).
-- The table includes metrics like score, questions attempted, correct/incorrect answers,
-- and the average answering time per question.
CREATE TABLE IF NOT EXISTS TestHistory (
    HistoryID SERIAL PRIMARY KEY,               -- Unique identifier for each test history entry.
    TestInstanceID INT NOT NULL,                -- Reference to the specific test instance.
    StudentID INT NOT NULL,                     -- ID of the student taking the test.
    Score INT,                                  -- Total score achieved in the test.
    QuestionsAttempted INT,                     -- Total number of questions attempted by the student.
    CorrectAnswers INT,                         -- Number of correct answers.
    IncorrectAnswers INT,                       -- Number of incorrect answers.
    AverageAnsweringTimeInSeconds FLOAT,        -- Average time taken per question in seconds.
    FOREIGN KEY (TestInstanceID) REFERENCES TestInstances(TestInstanceID)  -- Link to TestInstances table.
);
select * from TestHistory;
DELETE FROM TestHistory;
DROP TABLE IF EXISTS TestHistory CASCADE;

--8. ChapterProficiency Table
-- Creates a table for tracking student proficiency at the chapter level.
-- 'StudentID' refers to the ID of the student (from an external database).
-- 'ChapterID' links to the specific chapter from the Chapters table.
-- 'CorrectAnswers' and 'IncorrectAnswers' store the number of correct and incorrect 
-- answers given by the student in this chapter.
CREATE TABLE IF NOT EXISTS ChapterProficiency (
    StudentID INT NOT NULL,
    ChapterID INT REFERENCES Chapters(ChapterID),
    CorrectAnswers INT DEFAULT 0,
    IncorrectAnswers INT DEFAULT 0,
    PRIMARY KEY (StudentID, ChapterID)
);

select * from ChapterProficiency;
DELETE FROM ChapterProficiency;
DROP TABLE IF EXISTS ChapterProficiency CASCADE;

--9. SubtopicProficiency Table
-- Creates a table for tracking student proficiency at the subtopic level.
-- 'StudentID' refers to the ID of the student (from an external database).
-- 'SubtopicID' links to the specific subtopic from the Subtopics table.
-- 'CorrectAnswers' and 'IncorrectAnswers' store the number of correct and incorrect 
-- answers given by the student in this subtopic.
CREATE TABLE IF NOT EXISTS SubtopicProficiency (
    StudentID INT NOT NULL,
    SubtopicID INT REFERENCES Subtopics(SubtopicID),
    CorrectAnswers INT DEFAULT 0,
    IncorrectAnswers INT DEFAULT 0,
    PRIMARY KEY (StudentID, SubtopicID)
);

select * from SubtopicProficiency;
DELETE FROM SubtopicProficiency;
DROP TABLE IF EXISTS SubtopicProficiency CASCADE;


--10. StudentTestTargets Table
-- Creates a table for storing students' target scores and their progress.
-- 'StudentID' refers to the ID of the student (from an external database).
-- 'TargetScore' is the score that the student aims to achieve.
-- 'FinishedFirstWeek' is a boolean indicating whether the student has completed the first week of tests.
-- 'SetDate' records the timestamp when the target or progress was updated.
-- The target score is constrained to be between 0 and 720.
CREATE TABLE IF NOT EXISTS StudentTestTargets (
    StudentID INT NOT NULL,
    TargetScore INT,
    FinishedFirstWeek BOOLEAN DEFAULT FALSE,
    SetDate TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    PRIMARY KEY (StudentID, SetDate),
    CHECK (TargetScore >= 0 AND TargetScore <= 720)
);
select * from StudentTestTargets;
DELETE FROM StudentTestTargets;
DROP TABLE IF EXISTS StudentTestTargets CASCADE;


--11. PracticeTestProficiency Table
-- Creates a table for tracking student proficiency specifically in practice tests.
-- 'StudentID' refers to the ID of the student (referenced from an external database).
-- Metrics include average correct/incorrect answers, average score, average answering time,
-- date of the last response, and total practice tests taken.
CREATE TABLE IF NOT EXISTS PracticeTestProficiency (
    StudentID INT NOT NULL, -- ID of the student
    AverageCorrectAnswers NUMERIC, -- Average correct answers per practice test
    AverageIncorrectAnswers NUMERIC, -- Average incorrect answers per practice test
    AverageScore NUMERIC, -- Average score per practice test
    AverageAnsweringTimeInSeconds NUMERIC, -- Average answering time per question in practice tests
    LastResponseDate TIMESTAMP, -- Last date when the student took a practice test
    TotalTestsTaken INT, -- Total number of practice tests taken
    PRIMARY KEY (StudentID)
);
select * from PracticeTestProficiency;
DELETE FROM PracticeTestProficiency;
DROP TABLE IF EXISTS PracticeTestProficiency CASCADE;


--12. MockTestProficiency Table
-- Creates a table for tracking student proficiency specifically in NEET mock tests.
-- 'StudentID' refers to the ID of the student (referenced from an external database).
-- Metrics include average correct/incorrect answers, average score, average answering time,
-- date of the last response, and total mock tests taken.
CREATE TABLE IF NOT EXISTS MockTestProficiency (
    StudentID INT NOT NULL, -- ID of the student
    AverageCorrectAnswers NUMERIC, -- Average correct answers per mock test
    AverageIncorrectAnswers NUMERIC, -- Average incorrect answers per mock test
    AverageScore NUMERIC, -- Average score per mock test
    AverageAnsweringTimeInSeconds NUMERIC, -- Average answering time per question in mock tests
    LastResponseDate TIMESTAMP, -- Last date when the student took a mock test
    TotalTestsTaken INT, -- Total number of mock tests taken
    PRIMARY KEY (StudentID)
);

select * from MockTestProficiency;
DELETE FROM MockTestProficiency;
DROP TABLE IF EXISTS MockTestProficiency CASCADE;

--------------------------------------------------------------------------------------------------------------------------------------------


select * from PracticeTests;
select * from PracticeTestQuestions where practicetestid =7;
select * from NEETMockTests;
select * from NEETMockTestQuestions;
select * from TestInstances;


select * from StudentResponses where testinstanceid =7 and studentid =1234;

select * from TestHistory;
select * from ChapterProficiency;
select * from SubtopicProficiency;

select * from StudentTestTargets;

select * from PracticeTestProficiency;
select * from MockTestProficiency;


select * from PracticeTestQuestions where practicetestid =7;
select * from StudentResponses where testinstanceid =7;

DELETE FROM TestHistory WHERE studentid = 1234 AND testinstanceid = 7;


select * from studentresponses s 
JOIN practicetestquestions p on p.questionid = s.questionid
where s.testinstanceid  =7 and p.practicetestid =7;

SELECT *
                FROM StudentResponses SR
                JOIN PracticeTestQuestions PTQ ON SR.TestInstanceID = PTQ.PracticeTestID
                JOIN Questions Q ON PTQ.QuestionID = Q.QuestionID
                WHERE SR.StudentID = 1234 AND SR.TestInstanceID = 7 and PTQ.practicetestid =7;


SELECT *
FROM StudentResponses SR
JOIN PracticeTestQuestions PTQ ON SR.QuestionID = PTQ.QuestionID AND SR.TestInstanceID = PTQ.PracticeTestID
JOIN Questions Q ON PTQ.QuestionID = Q.QuestionID
WHERE SR.StudentID = 1234 AND SR.TestInstanceID = 7;



---------------------------------------------------------------------------------------------------------------------------------------------------------

---update_test_proficiency_data Procedure---

CREATE OR REPLACE FUNCTION update_test_proficiency_data(student_id INT, test_instance_id INT)
RETURNS VOID AS $$
DECLARE
    test_type TEXT;
    test_record RECORD;
    total_weighted_correct_answers NUMERIC := 0;
    total_weighted_incorrect_answers NUMERIC := 0;
    total_weighted_score NUMERIC := 0;
    total_weighted_time_seconds NUMERIC := 0;
    total_weights NUMERIC := 0;
    weight NUMERIC;
    last_response TIMESTAMP;
BEGIN
    -- Determine the type of the test
    SELECT TestType INTO test_type FROM TestInstances WHERE TestInstanceID = test_instance_id;

    -- Get the last response date
    SELECT MAX(ResponseDate) INTO last_response FROM StudentResponses WHERE StudentID = student_id;

    -- Iterate over each test in reverse chronological order
    FOR test_record IN
        SELECT * FROM TestHistory
        WHERE StudentID = student_id AND TestInstanceID IN 
            (SELECT TestInstanceID FROM TestInstances WHERE TestType = test_type)
        ORDER BY TestInstanceID DESC
    LOOP
        -- Assign weight based on order (newer tests have higher weight)
        weight := row_number() OVER ();
        total_weights := total_weights + weight;

        -- Calculate weighted values
        total_weighted_correct_answers := total_weighted_correct_answers + (test_record.CorrectAnswers * weight);
        total_weighted_incorrect_answers := total_weighted_incorrect_answers + (test_record.IncorrectAnswers * weight);
        total_weighted_score := total_weighted_score + (test_record.Score * weight);
        total_weighted_time_seconds := total_weighted_time_seconds + (test_record.AverageAnsweringTimeInSeconds * test_record.QuestionsAttempted * weight);
    END LOOP;

    -- Calculate final weighted averages
    IF total_weights > 0 THEN
        -- Update or insert into the corresponding proficiency table
        IF test_type = 'Mock' THEN
            INSERT INTO MockTestProficiency (StudentID, AverageCorrectAnswers, AverageIncorrectAnswers, AverageScore, AverageAnsweringTimeInSeconds, LastResponseDate, TotalTestsTaken)
            VALUES (student_id, total_weighted_correct_answers / total_weights, total_weighted_incorrect_answers / total_weights, total_weighted_score / total_weights, total_weighted_time_seconds / total_weights, last_response, total_weights)
            ON CONFLICT (StudentID) DO
            UPDATE SET 
                AverageCorrectAnswers = EXCLUDED.AverageCorrectAnswers,
                AverageIncorrectAnswers = EXCLUDED.AverageIncorrectAnswers,
                AverageScore = EXCLUDED.AverageScore,
                AverageAnsweringTimeInSeconds = EXCLUDED.AverageAnsweringTimeInSeconds,
                LastResponseDate = EXCLUDED.LastResponseDate,
                TotalTestsTaken = EXCLUDED.TotalTestsTaken;
        ELSIF test_type = 'Practice' THEN
            INSERT INTO PracticeTestProficiency (StudentID, AverageCorrectAnswers, AverageIncorrectAnswers, AverageScore, AverageAnsweringTimeInSeconds, LastResponseDate, TotalTestsTaken)
            VALUES (student_id, total_weighted_correct_answers / total_weights, total_weighted_incorrect_answers / total_weights, total_weighted_score / total_weights, total_weighted_time_seconds / total_weights, last_response, total_weights)
            ON CONFLICT (StudentID) DO
            UPDATE SET 
                AverageCorrectAnswers = EXCLUDED.AverageCorrectAnswers,
                AverageIncorrectAnswers = EXCLUDED.AverageIncorrectAnswers,
                AverageScore = EXCLUDED.AverageScore,
                AverageAnsweringTimeInSeconds = EXCLUDED.AverageAnsweringTimeInSeconds,
                LastResponseDate = EXCLUDED.LastResponseDate,
                TotalTestsTaken = EXCLUDED.TotalTestsTaken;
        END IF;
    END IF;
END;
$$ LANGUAGE plpgsql;

---------------------------------------------------------------------------------------------------------------------------------------------------------

---update_student_performance_data Procedure---

CREATE OR REPLACE FUNCTION update_student_performance_data()
RETURNS TRIGGER AS $$
DECLARE
    question_record RECORD;
    is_correct BOOLEAN;
    total_correct_answers INT := 0;
    total_incorrect_answers INT := 0;
    total_time_seconds INT := 0;
    question_count INT := 0;
BEGIN
    -- Iterate over each response for the given TestInstanceID
    FOR question_record IN
        SELECT sr.QuestionID, sr.StudentResponse, sr.AnsweringTimeInSeconds, q.Answer, q.ChapterID, q.SubtopicID
        FROM StudentResponses sr
        JOIN Questions q ON sr.QuestionID = q.QuestionID
        WHERE sr.TestInstanceID = NEW.TestInstanceID
    LOOP
        -- Determine if the response is correct
        is_correct := (question_record.StudentResponse IS NOT NULL AND question_record.StudentResponse = question_record.Answer);

        -- Update counters
        IF question_record.StudentResponse IS NOT NULL THEN
            question_count := question_count + 1;
            total_time_seconds := total_time_seconds + question_record.AnsweringTimeInSeconds;
            IF is_correct THEN
                total_correct_answers := total_correct_answers + 1;
            ELSE
                total_incorrect_answers := total_incorrect_answers + 1;
            END IF;
        END IF;

        -- Update ChapterProficiency
        IF EXISTS (SELECT 1 FROM ChapterProficiency WHERE StudentID = NEW.StudentID AND ChapterID = question_record.ChapterID) THEN
            UPDATE ChapterProficiency
            SET CorrectAnswers = CorrectAnswers + (CASE WHEN is_correct THEN 1 ELSE 0 END),
                IncorrectAnswers = IncorrectAnswers + (CASE WHEN is_correct THEN 0 ELSE 1 END)
            WHERE StudentID = NEW.StudentID AND ChapterID = question_record.ChapterID;
        ELSE
            INSERT INTO ChapterProficiency (StudentID, ChapterID, CorrectAnswers, IncorrectAnswers)
            VALUES (NEW.StudentID, question_record.ChapterID, (CASE WHEN is_correct THEN 1 ELSE 0 END), (CASE WHEN is_correct THEN 0 ELSE 1 END));
        END IF;

        -- Update SubtopicProficiency
        IF question_record.SubtopicID IS NOT NULL THEN
            IF EXISTS (SELECT 1 FROM SubtopicProficiency WHERE StudentID = NEW.StudentID AND SubtopicID = question_record.SubtopicID) THEN
                UPDATE SubtopicProficiency
                SET CorrectAnswers = CorrectAnswers + (CASE WHEN is_correct THEN 1 ELSE 0 END),
                    IncorrectAnswers = IncorrectAnswers + (CASE WHEN is_correct THEN 0 ELSE 1 END)
                WHERE StudentID = NEW.StudentID AND SubtopicID = question_record.SubtopicID;
            ELSE
                INSERT INTO SubtopicProficiency (StudentID, SubtopicID, CorrectAnswers, IncorrectAnswers)
                VALUES (NEW.StudentID, question_record.SubtopicID, (CASE WHEN is_correct THEN 1 ELSE 0 END), (CASE WHEN is_correct THEN 0 ELSE 1 END));
            END IF;
        END IF;
    END LOOP;

    -- Update TestHistory
    IF question_count > 0 THEN
        INSERT INTO TestHistory (TestInstanceID, StudentID, Score, QuestionsAttempted, CorrectAnswers, IncorrectAnswers, AverageAnsweringTimeInSeconds)
        VALUES (NEW.TestInstanceID, NEW.StudentID, (4 * total_correct_answers) - total_incorrect_answers, question_count, total_correct_answers, total_incorrect_answers, total_time_seconds::FLOAT / question_count);
    END IF;
   
    -- Call the new procedure to update test proficiency data
    PERFORM update_test_proficiency_data(NEW.StudentID, NEW.TestInstanceID);

    RETURN NEW;
END;
$$ LANGUAGE plpgsql;


---TestHistory Trigger---
CREATE TRIGGER trigger_update_student_performance
AFTER INSERT ON StudentResponses
FOR EACH ROW
EXECUTE FUNCTION update_student_performance_data();



---------------------------------------------------------------------------------------------------------------------------------------------------------


DROP TRIGGER trigger_update_student_performance ON StudentResponses;

