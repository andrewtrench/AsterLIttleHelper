#!/usr/bin/env python3
import os
import argparse
import sys


def create_directory(path):
    """Create directory if it doesn't exist."""
    if not os.path.exists(path):
        os.makedirs(path)
        print(f"Created directory: {path}")
    else:
        print(f"Directory already exists: {path}")


def create_file(path, content=""):
    """Create file with optional content."""
    with open(path, 'w') as f:
        f.write(content)
    print(f"Created file: {path}")


def setup_project_structure(base_path):
    """Set up the project structure for the Flask Task Scheduler."""

    # Create main directory structure
    create_directory(base_path)
    create_directory(os.path.join(base_path, "templates"))
    create_directory(os.path.join(base_path, "static"))
    create_directory(os.path.join(base_path, "static", "css"))
    create_directory(os.path.join(base_path, "static", "js"))

    # Create schema.sql with the database schema
    schema_sql = """CREATE TABLE tasks (
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
"""
    create_file(os.path.join(base_path, "schema.sql"), schema_sql)

    # Create requirements.txt
    requirements = """Flask==2.0.1
WeasyPrint==52.5
icalendar==4.0.7
python-dateutil==2.8.2
Werkzeug==2.0.1
click==8.0.1
xhtml2pdf==0.2.8
"""
    create_file(os.path.join(base_path, "requirements.txt"), requirements)

    # Create empty app.py file (we'll fill this later)
    create_file(os.path.join(base_path, "app.py"), "# Flask Task Scheduler Application\n")

    # Create empty template files
    templates = [
        "base.html",
        "index.html",
        "task_form.html",
        "schedule.html",
        "error.html"
    ]
    for template in templates:
        create_file(os.path.join(base_path, "templates", template), "")

    # Create empty CSS file
    create_file(os.path.join(base_path, "static", "css", "custom.css"), "/* Custom styles */\n")

    # Create empty JS file
    create_file(os.path.join(base_path, "static", "js", "main.js"), "// Custom JavaScript\n")

    print("\nProject structure created successfully!")
    print(f"To start developing, navigate to {base_path} and run:")
    print("pip install -r requirements.txt")
    print("flask run")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Set up Flask Task Scheduler project structure")
    parser.add_argument("--path", default="flask_task_scheduler", help="Base directory path for the project")
    args = parser.parse_args()

    try:
        setup_project_structure(args.path)
    except Exception as e:
        print(f"Error setting up project structure: {e}", file=sys.stderr)
        sys.exit(1)