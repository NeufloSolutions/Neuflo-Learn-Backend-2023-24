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
select * from subjects;

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
    PracticeTestID INT PRIMARY KEY,
    StudentID INT NOT NULL
);

--2. PracticeTestSubjects Table
--
--This table is designed to track each subject test within a practice test. It provides a link between the overall practice test and its individual subject components.
--
--PracticeTestSubjectID (SERIAL PRIMARY KEY): A unique identifier for each subject test within a practice test. It's an auto-incrementing integer.
--PracticeTestID (INT): References the overall practice test to which this subject test belongs. It is a foreign key that links to the PracticeTests table.
--SubjectName (VARCHAR(50)): Specifies the subject of the test. The value will be one of 'Biology', 'Chemistry', or 'Physics'.
--IsCompleted (BOOLEAN): Indicates whether the subject test has been completed. The default value is FALSE.
CREATE TABLE IF NOT EXISTS PracticeTestSubjects (
    PracticeTestSubjectID SERIAL PRIMARY KEY,
    PracticeTestID INT NOT NULL,
    SubjectName VARCHAR(50) NOT NULL,
    IsCompleted BOOLEAN DEFAULT FALSE,
    FOREIGN KEY (PracticeTestID) REFERENCES PracticeTests(PracticeTestID)
);

--3. PracticeTestQuestions Table
--This table associates questions with each subject test within a practice test, ensuring that the appropriate questions are included for each subject area.
--
--PracticeTestSubjectID (INT): References the specific subject test. It is a foreign key that links to the PracticeTestSubjects table.
--QuestionID (INT): Identifies the specific question from the Questions table.
--The combination of PracticeTestSubjectID and QuestionID serves as the primary key, ensuring that each question is uniquely associated with a specific subject test.
CREATE TABLE IF NOT EXISTS PracticeTestQuestions (
    PracticeTestSubjectID INT NOT NULL,
    QuestionID INT NOT NULL,
    PRIMARY KEY (PracticeTestSubjectID, QuestionID),
    FOREIGN KEY (PracticeTestSubjectID) REFERENCES PracticeTestSubjects(PracticeTestSubjectID),
    FOREIGN KEY (QuestionID) REFERENCES Questions(QuestionID)
);

--4. PracticeTestCompletion Table
--This table is intended to track the overall completion status of each practice test by a student. It helps in monitoring whether a student has completed all subject tests within a given practice test.
--
--PracticeTestID (INT): References the practice test. It is a foreign key that links to the PracticeTests table.
--StudentID (INT): Identifies the student who is taking the test.
--IsCompleted (BOOLEAN): Indicates whether the student has completed the entire practice test (all subject tests). The default value is FALSE.
--CompletionDate (TIMESTAMP): Records the date and time when the practice test was completed.
--The combination of PracticeTestID and StudentID is the primary key for this table, ensuring a unique record for each student's attempt at a practice test.                
CREATE TABLE IF NOT EXISTS PracticeTestCompletion (
    PracticeTestID INT NOT NULL,
    StudentID INT NOT NULL,
    IsCompleted BOOLEAN DEFAULT FALSE,
    CompletionDate TIMESTAMP,
    PRIMARY KEY (PracticeTestID, StudentID),
    FOREIGN KEY (PracticeTestID) REFERENCES PracticeTests(PracticeTestID)
);

-- 5. NEETMockTests Table 
-- Creates a table for storing NEET mock test instances for each student.
-- 'MockTestID' is a unique identifier for each NEET mock test instance.
-- 'StudentID' refers to the ID of the student taking the test (from an external database).
CREATE TABLE IF NOT EXISTS NEETMockTests (
    MockTestID INT PRIMARY KEY,
    StudentID INT NOT NULL
);

--6. NEETMockTestQuestions Table
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

ALTER TABLE NEETMockTestQuestions
ADD COLUMN Section VARCHAR(10);

-- 7. MockTestChapterWeightage Table
-- This table stores the weightage for each chapter in the NEET Mock Test.
-- The weightage helps in determining the probability of selecting questions from a specific chapter.
CREATE TABLE IF NOT EXISTS MockTestChapterWeightage (
    MockTestWeightageID SERIAL PRIMARY KEY, -- Unique identifier for each weightage entry.
    ChapterID INT NOT NULL,                 -- ID of the chapter.
    SubjectID INT NOT NULL,                 -- ID of the subject to which the chapter belongs.
    Weightage NUMERIC NOT NULL,             -- Weightage of the chapter in question selection.
    FOREIGN KEY (ChapterID) REFERENCES Chapters(ChapterID),
    FOREIGN KEY (SubjectID) REFERENCES Subjects(SubjectID)
);

ALTER TABLE MockTestChapterWeightage
ADD CONSTRAINT unique_chapter_subject UNIQUE (ChapterID, SubjectID);

-- Query to update weights in the MockTestChapterWeightage table
DO $$
DECLARE
    rec record;
BEGIN
    -- Iterating through each chapter and its corresponding subject
    FOR rec IN SELECT c.ChapterID, c.SubjectID, 
                      COUNT(q.QuestionID) AS TotalQuestionsPerChapter,
                      (SELECT COUNT(QuestionID) FROM Questions WHERE ChapterID IN 
                          (SELECT ChapterID FROM Chapters WHERE SubjectID = c.SubjectID)
                      ) AS TotalQuestionsPerSubject
               FROM Chapters c
               JOIN Questions q ON c.ChapterID = q.ChapterID
               GROUP BY c.ChapterID, c.SubjectID
    LOOP
        -- Calculating and updating weightage for each chapter
        IF rec.TotalQuestionsPerSubject > 0 THEN
            INSERT INTO MockTestChapterWeightage (ChapterID, SubjectID, Weightage)
            VALUES (rec.ChapterID, rec.SubjectID, (rec.TotalQuestionsPerChapter::NUMERIC / rec.TotalQuestionsPerSubject) * 100)
            ON CONFLICT (ChapterID, SubjectID) DO UPDATE
            SET Weightage = EXCLUDED.Weightage;
        END IF;
    END LOOP;
END $$;

select * from MockTestChapterWeightage;

SELECT SubjectID, SUM(Weightage) AS TotalWeightage
FROM MockTestChapterWeightage
GROUP BY SubjectID;

-- 8. MockTestConfiguration Table
-- This table defines the structure of the mock test for each subject.
-- It includes the number of questions in Section A and Section B.
CREATE TABLE IF NOT EXISTS MockTestConfiguration (
    ConfigID SERIAL PRIMARY KEY,       -- Unique identifier for each configuration.
    SubjectID INT NOT NULL,            -- ID of the subject.
    SectionAQuestions INT NOT NULL,    -- Number of questions in Section A.
    SectionBQuestions INT NOT NULL,    -- Number of questions in Section B.
    FOREIGN KEY (SubjectID) REFERENCES Subjects(SubjectID)
);

-- Pre-populating MockTestConfiguration with fixed values for each subject.
-- Assuming Subject IDs for Physics, Chemistry, Botany, and Zoology are 1, 2, 3, and 4 respectively.
INSERT INTO MockTestConfiguration (SubjectID, SectionAQuestions, SectionBQuestions)
VALUES
(1, 35, 15), -- Physics
(2, 35, 15), -- Chemistry
(3, 35, 15), -- Botany
(4, 35, 15); -- Zoology

-- 9. StudentMockTestHistory Table
-- This table stores the history of questions given to a student in mock tests.
-- It helps to ensure that questions are not repeated in subsequent tests for the same student.
CREATE TABLE IF NOT EXISTS StudentMockTestHistory (
    HistoryID SERIAL PRIMARY KEY,    -- Unique identifier for each history record.
    StudentID INT NOT NULL,          -- ID of the student.
    QuestionID INT NOT NULL,         -- ID of the question given to the student.
    FOREIGN KEY (QuestionID) REFERENCES Questions(QuestionID)
);

--7. TestInstances Table
-- This table stores each unique instance of a test created for a student.
CREATE TABLE IF NOT EXISTS TestInstances (
    TestInstanceID INT PRIMARY KEY,    -- Unique identifier for each test instance.
    StudentID INT NOT NULL,               -- ID of the student taking the test.
    TestID INT NOT NULL,                  -- ID of the specific mock or practice test.
    TestType VARCHAR(50) NOT NULL,        -- Type of the test (e.g., 'Practice', 'Mock').
    TestDateTime TIMESTAMP DEFAULT CURRENT_TIMESTAMP  -- Date and time when the test was generated.
);

------------------------------------------------------------------------------------------------------------------------------

--1. StudentResponses Table
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

--2. TestHistory Table
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
    LastTestAttempt TIMESTAMP DEFAULT CURRENT_TIMESTAMP, -- Date of last test attempt
    FOREIGN KEY (TestInstanceID) REFERENCES TestInstances(TestInstanceID)  -- Link to TestInstances table.
);

ALTER TABLE TestHistory
ADD UNIQUE (TestInstanceID, StudentID);

--3. ChapterProficiency Table
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

--4. SubtopicProficiency Table
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


--5. StudentTestTargets Table
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

--6. PracticeTestProficiency Table
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
    TotalTestsTaken INT, -- Total number of practice tests taken
    LastResponseDate TIMESTAMP,
    PRIMARY KEY (StudentID)
);

--7. MockTestProficiency Table
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
    TotalTestsTaken INT, -- Total number of mock tests taken
    LastResponseDate TIMESTAMP,
    PRIMARY KEY (StudentID)
);

--------------------------------------------------------------------------------------------------------------------------------------------


select * from PracticeTests;
select * from PracticeTestSubjects;
select * from PracticeTestCompletion;
select * from PracticeTestQuestions; 


select * from NEETMockTests;
select * from NEETMockTestQuestions;


select * from TestInstances;


select * from StudentResponses;

select * from TestHistory;
select * from ChapterProficiency;
select * from SubtopicProficiency;

select * from StudentTestTargets;

select * from PracticeTestProficiency;
select * from MockTestProficiency;



