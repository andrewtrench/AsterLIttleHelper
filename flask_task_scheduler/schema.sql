CREATE TABLE tasks (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    title TEXT NOT NULL,
    description TEXT,
    due_date DATE NOT NULL,
    estimated_hours REAL NOT NULL,
    hours_completed REAL DEFAULT 0,
    status TEXT DEFAULT 'pending'
);

CREATE TABLE task_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    task_id INTEGER NOT NULL,
    log_date DATE NOT NULL,
    hours REAL NOT NULL,
    FOREIGN KEY(task_id) REFERENCES tasks(id)
);
