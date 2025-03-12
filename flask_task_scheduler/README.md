# Flask Task Scheduler

A Flask-based web application to help students manage tasks, deadlines, and study schedules.

## Features

- Task management (create, read, update, delete)
- Automatic scheduling of study time
- Google Calendar integration for reminders
- Progress tracking
- Seven-day scheduling
- Colorful and fun UI
- PDF export of schedules

## Installation

### Prerequisites

- Python 3.6 or higher
- pip (Python package installer)

### Setup

1. Clone this repository or download the source code.

2. Navigate to the project directory:
   ```
   cd flask_task_scheduler
   ```

3. Install the required dependencies:
   ```
   pip install -r requirements.txt
   ```

   Note: If you encounter issues with WeasyPrint installation, please refer to the 
   [WeasyPrint Installation Documentation](https://doc.courtbouillon.org/weasyprint/stable/first_steps.html#installation)
   for platform-specific instructions.

4. Run the application:
   ```
   python app.py
   ```
   
   or with Flask CLI:
   ```
   flask run
   ```

5. Open your browser and go to `http://127.0.0.1:5000/` to access the application.

## Usage

1. **Dashboard**: View all your tasks and today's schedule.
2. **Add New Task**: Create a new task with a title, description, due date, and estimated hours.
3. **Log Progress**: Record the time spent on each task.
4. **Schedule**: View your automated study schedule.
5. **Export Options**: Export your schedule as a PDF or to Google Calendar (.ics file).

## Troubleshooting

### Import Error with Werkzeug

If you encounter an error like:
```
ImportError: cannot import name 'url_quote' from 'werkzeug.urls'
```

Try the following solutions:

1. Make sure you're using the specified Werkzeug version:
   ```
   pip install Werkzeug==2.0.1
   ```

2. If that doesn't work, try uninstalling and reinstalling the packages:
   ```
   pip uninstall Flask WeasyPrint Werkzeug
   pip install -r requirements.txt
   ```

### Database Initialization Issues

If you encounter database-related errors:

1. Delete the existing database file (if any):
   ```
   rm instance/database.db
   ```

2. Run the application again to recreate the database:
   ```
   python app.py
   ```

### WeasyPrint Installation Issues

WeasyPrint has specific dependencies depending on your operating system:

- **Windows**: Requires GTK to be installed. See the WeasyPrint documentation for details.
- **macOS**: May require additional packages via Homebrew.
- **Linux**: May require additional packages via your package manager.

## License

This project is licensed under the MIT License - see the LICENSE file for details.

## Acknowledgments

- Flask and its extensions
- Bootstrap for the UI components
- WeasyPrint for PDF generation
- icalendar for Google Calendar integration