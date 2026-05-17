-- База данных Timary. Создать базу вручную: CREATE DATABASE timary_db;
-- Таблицы также создаются автоматически при первом запуске python run.py.

CREATE TABLE IF NOT EXISTS teachers (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(160) NOT NULL,
    position VARCHAR(120) NOT NULL
);

CREATE TABLE IF NOT EXISTS school_classes (
    id SERIAL PRIMARY KEY,
    name VARCHAR(20) UNIQUE NOT NULL,
    teacher_id INTEGER REFERENCES teachers(id)
);

CREATE TABLE IF NOT EXISTS teacher_classes (
    id SERIAL PRIMARY KEY,
    teacher_id INTEGER NOT NULL REFERENCES teachers(id),
    class_id INTEGER NOT NULL REFERENCES school_classes(id),
    CONSTRAINT uq_teacher_class UNIQUE (teacher_id, class_id)
);

CREATE TABLE IF NOT EXISTS students (
    id SERIAL PRIMARY KEY,
    full_name VARCHAR(160) NOT NULL,
    class_id INTEGER NOT NULL REFERENCES school_classes(id)
);

CREATE TABLE IF NOT EXISTS users (
    id SERIAL PRIMARY KEY,
    login VARCHAR(120) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL,
    full_name VARCHAR(160) NOT NULL,
    role VARCHAR(20) NOT NULL,
    position VARCHAR(120),
    student_id INTEGER REFERENCES students(id)
);

CREATE TABLE IF NOT EXISTS parent_children (
    id SERIAL PRIMARY KEY,
    parent_user_id INTEGER NOT NULL REFERENCES users(id),
    student_id INTEGER NOT NULL REFERENCES students(id)
);

CREATE TABLE IF NOT EXISTS subjects (
    id SERIAL PRIMARY KEY,
    name VARCHAR(100) UNIQUE NOT NULL
);

CREATE TABLE IF NOT EXISTS schedule (
    id SERIAL PRIMARY KEY,
    class_id INTEGER NOT NULL REFERENCES school_classes(id),
    week_no INTEGER NOT NULL DEFAULT 1,
    weekday VARCHAR(20) NOT NULL,
    time_start VARCHAR(5) NOT NULL,
    subject_id INTEGER NOT NULL REFERENCES subjects(id),
    teacher_id INTEGER NOT NULL REFERENCES teachers(id),
    room VARCHAR(20) NOT NULL
);

CREATE TABLE IF NOT EXISTS homework (
    id SERIAL PRIMARY KEY,
    class_id INTEGER NOT NULL REFERENCES school_classes(id),
    teacher_id INTEGER NOT NULL REFERENCES teachers(id),
    subject_id INTEGER NOT NULL REFERENCES subjects(id),
    title VARCHAR(160) NOT NULL,
    text TEXT NOT NULL,
    date_issued DATE NOT NULL DEFAULT CURRENT_DATE,
    due_date DATE NOT NULL
);

CREATE TABLE IF NOT EXISTS homework_submissions (
    id SERIAL PRIMARY KEY,
    homework_id INTEGER NOT NULL REFERENCES homework(id),
    student_id INTEGER NOT NULL REFERENCES students(id),
    file_name VARCHAR(255) NOT NULL,
    stored_name VARCHAR(255) NOT NULL,
    comment TEXT,
    teacher_comment TEXT,
    status VARCHAR(30) NOT NULL DEFAULT 'Сдано',
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS grades (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id),
    subject_id INTEGER NOT NULL REFERENCES subjects(id),
    teacher_id INTEGER NOT NULL REFERENCES teachers(id),
    grade_date DATE NOT NULL DEFAULT CURRENT_DATE,
    value INTEGER NOT NULL CHECK (value BETWEEN 2 AND 5),
    comment VARCHAR(255)
);

CREATE TABLE IF NOT EXISTS attendance (
    id SERIAL PRIMARY KEY,
    student_id INTEGER NOT NULL REFERENCES students(id),
    subject_id INTEGER NOT NULL REFERENCES subjects(id),
    attendance_date DATE NOT NULL DEFAULT CURRENT_DATE,
    status VARCHAR(30) NOT NULL
);

CREATE TABLE IF NOT EXISTS news (
    id SERIAL PRIMARY KEY,
    title VARCHAR(160) NOT NULL,
    description VARCHAR(255),
    text TEXT NOT NULL,
    tag VARCHAR(60),
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS audit_logs (
    id SERIAL PRIMARY KEY,
    user_id INTEGER REFERENCES users(id),
    action VARCHAR(120) NOT NULL,
    details TEXT,
    created_at TIMESTAMP NOT NULL DEFAULT CURRENT_TIMESTAMP
);
