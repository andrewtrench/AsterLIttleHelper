#!/usr/bin/env python3
import os
import sqlite3
from datetime import datetime, timedelta, date
import math
from flask import (
    Flask, render_template, request, redirect, url_for, flash,
    g, send_file, make_response, jsonify, abort, after_this_request
)
from werkzeug.exceptions import HTTPException
from icalendar import Calendar, Event
from dateutil import rrule
import tempfile
from weasyprint import HTML, CSS
from flask import render_template

# Initialize Flask application
app = Flask(__name__)
app.config.from_mapping(
    SECRET_KEY='dev',
    DATABASE=os.path.join(app.instance_path, 'database.db'),
)

# Ensure the instance folder exists
try:
    os.makedirs(app.instance_path)
except OSError:
    pass


# Database helper functions
def get_db():
    """Connect to the database."""
    if 'db' not in g:
        g.db = sqlite3.connect(
            app.config['DATABASE'],
            detect_types=sqlite3.PARSE_DECLTYPES | sqlite3.PARSE_COLNAMES
        )
        g.db.row_factory = sqlite3.Row
    return g.db


def close_db(e=None):
    """Close the database connection."""
    db = g.pop('db', None)
    if db is not None:
        db.close()


def init_db():
    """Initialize the database with schema."""
    db = get_db()
    with app.open_resource('schema.sql') as f:
        db.executescript(f.read().decode('utf8'))
    db.commit()


@app.cli.command('init-db')
def init_db_command():
    """Clear the existing data and create new tables."""
    init_db()
    click.echo('Initialized the database.')


# Automatically check if database exists, if not create it
def init_app(app):
    app.teardown_appcontext(close_db)
    app.cli.add_command(init_db_command)

    # Check if database exists, initialize if not
    if not os.path.exists(app.config['DATABASE']):
        with app.app_context():
            init_db()
            print("Database initialized.")


# Register the init_app function
init_app(app)


# Helper functions for scheduling algorithm
def get_all_tasks():
    """Get all tasks from the database."""
    db = get_db()
    tasks = db.execute('SELECT * FROM tasks ORDER BY due_date').fetchall()
    return tasks


def get_task(task_id):
    """Get a specific task by ID."""
    db = get_db()
    task = db.execute('SELECT * FROM tasks WHERE id = ?', (task_id,)).fetchone()
    return task


def get_logs_for_task(task_id):
    """Get all logs for a specific task."""
    db = get_db()
    logs = db.execute(
        'SELECT * FROM task_logs WHERE task_id = ? ORDER BY log_date DESC',
        (task_id,)
    ).fetchall()
    return logs


def calculate_work_schedule(days_ahead=14):
    """
    Calculate a work schedule for the next X days.
    Returns a dictionary mapping dates to tasks and suggested hours.
    """
    tasks = get_all_tasks()
    schedule = {}

    # Initialize schedule with empty lists for each day
    today = datetime.now().date()
    for i in range(days_ahead):
        current_date = today + timedelta(days=i)
        schedule[current_date] = []

    # For each task, calculate remaining work and distribute across days
    for task in tasks:
        # Skip completed tasks
        if task['status'] == 'completed':
            continue

        # Calculate remaining hours
        remaining_hours = task['estimated_hours'] - task['hours_completed']
        if remaining_hours <= 0:
            continue

        # Calculate days until due date
        # Handle due_date correctly whether it's a string or a date object
        if isinstance(task['due_date'], str):
            due_date = datetime.strptime(task['due_date'], '%Y-%m-%d').date()
        else:
            due_date = task['due_date']

        days_until_due = (due_date - today).days + 1  # Include today

        # If due date has passed or is today, schedule all remaining work today
        if days_until_due <= 0:
            if today in schedule:
                schedule[today].append({
                    'task_id': task['id'],
                    'title': task['title'],
                    'hours': round(remaining_hours * 2) / 2  # Round to nearest 0.5
                })
            continue

        # If due date is within our planning horizon
        if days_until_due <= days_ahead:
            # Distribute hours evenly
            daily_hours = remaining_hours / days_until_due

            # Round to nearest 0.5 hour, minimum 0.5 hour
            daily_hours = max(0.5, round(daily_hours * 2) / 2)

            # Ensure we don't allocate more hours than remaining
            total_allocated = 0

            for i in range(days_until_due):
                current_date = today + timedelta(days=i)

                # Skip if we've already allocated all hours
                if total_allocated >= remaining_hours:
                    break

                # Adjust for weekends (reduce weekend work by 20% if possible)
                adjusted_hours = daily_hours
                if current_date.weekday() >= 5:  # Saturday (5) or Sunday (6)
                    adjusted_hours = max(0.5, round(daily_hours * 0.8 * 2) / 2)

                # Don't exceed remaining hours
                hours_today = min(adjusted_hours, remaining_hours - total_allocated)

                # Round to nearest 0.5 hour
                hours_today = round(hours_today * 2) / 2

                # Add to schedule
                if hours_today > 0 and current_date in schedule:
                    schedule[current_date].append({
                        'task_id': task['id'],
                        'title': task['title'],
                        'hours': hours_today
                    })
                    total_allocated += hours_today

    # Calculate total hours per day
    for date, tasks in schedule.items():
        total_hours = sum(task['hours'] for task in tasks)

        # If a day has more than 5 hours, redistribute
        if total_hours > 5:
            # Sort tasks by due date (priority)
            tasks_sorted = sorted(tasks, key=lambda x: get_task(x['task_id'])['due_date'])

            # Reset hours allocation
            total_allocated = 0
            for task in tasks_sorted:
                # Allocate at most 5 hours per day, prioritizing tasks with earlier due dates
                remaining = 5 - total_allocated
                if remaining <= 0:
                    task['hours'] = 0
                else:
                    task['hours'] = min(task['hours'], remaining)
                    task['hours'] = round(task['hours'] * 2) / 2  # Round to nearest 0.5
                    total_allocated += task['hours']

    return schedule


# Routes
@app.route('/')
def index():
    """Show dashboard with tasks and today's schedule."""
    tasks = get_all_tasks()

    # Get today's schedule
    today = datetime.now().date()
    schedule = calculate_work_schedule(days_ahead=7)
    today_schedule = schedule.get(today, [])

    return render_template(
        'index.html',
        tasks=tasks,
        today_schedule=today_schedule,
        today=today
    )


@app.route('/tasks/new', methods=('GET', 'POST'))
def create_task():
    """Create a new task."""
    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        due_date = request.form['due_date']
        estimated_hours = float(request.form['estimated_hours'])

        error = None
        if not title:
            error = 'Title is required.'
        elif not due_date:
            error = 'Due date is required.'
        elif estimated_hours <= 0:
            error = 'Estimated hours must be greater than 0.'

        if error is None:
            db = get_db()
            db.execute(
                'INSERT INTO tasks (title, description, due_date, estimated_hours) '
                'VALUES (?, ?, ?, ?)',
                (title, description, due_date, estimated_hours)
            )
            db.commit()
            flash('Task created successfully!', 'success')
            return redirect(url_for('index'))

        flash(error, 'error')

    return render_template('task_form.html', task=None)


@app.route('/tasks/<int:task_id>/edit', methods=('GET', 'POST'))
def edit_task(task_id):
    """Edit an existing task."""
    task = get_task(task_id)
    if task is None:
        abort(404)

    if request.method == 'POST':
        title = request.form['title']
        description = request.form.get('description', '')
        due_date = request.form['due_date']
        estimated_hours = float(request.form['estimated_hours'])
        status = request.form.get('status', 'pending')

        error = None
        if not title:
            error = 'Title is required.'
        elif not due_date:
            error = 'Due date is required.'
        elif estimated_hours <= 0:
            error = 'Estimated hours must be greater than 0.'

        if error is None:
            db = get_db()
            db.execute(
                'UPDATE tasks SET title = ?, description = ?, due_date = ?, '
                'estimated_hours = ?, status = ? WHERE id = ?',
                (title, description, due_date, estimated_hours, status, task_id)
            )
            db.commit()
            flash('Task updated successfully!', 'success')
            return redirect(url_for('index'))

        flash(error, 'error')

    return render_template('task_form.html', task=task)


@app.route('/tasks/<int:task_id>/delete', methods=('POST',))
def delete_task(task_id):
    """Delete a task."""
    db = get_db()

    # First delete associated logs
    db.execute('DELETE FROM task_logs WHERE task_id = ?', (task_id,))

    # Then delete the task
    db.execute('DELETE FROM tasks WHERE id = ?', (task_id,))
    db.commit()

    flash('Task deleted successfully!', 'success')
    return redirect(url_for('index'))


@app.route('/tasks/<int:task_id>/log', methods=('GET', 'POST'))
def log_progress(task_id):
    """Log progress for a task."""
    task = get_task(task_id)
    if task is None:
        abort(404)

    logs = get_logs_for_task(task_id)

    if request.method == 'POST':
        log_date = request.form.get('log_date', datetime.now().strftime('%Y-%m-%d'))
        hours = float(request.form['hours'])

        error = None
        if hours <= 0:
            error = 'Hours must be greater than 0.'
        elif hours % 0.5 != 0:
            error = 'Hours must be in increments of 0.5.'

        if error is None:
            db = get_db()

            # Add a new log entry
            db.execute(
                'INSERT INTO task_logs (task_id, log_date, hours) VALUES (?, ?, ?)',
                (task_id, log_date, hours)
            )

            # Update total hours completed
            total_hours = sum(log['hours'] for log in logs) + hours
            db.execute(
                'UPDATE tasks SET hours_completed = ? WHERE id = ?',
                (total_hours, task_id)
            )

            # Check if task is complete
            if total_hours >= task['estimated_hours']:
                db.execute(
                    'UPDATE tasks SET status = ? WHERE id = ?',
                    ('completed', task_id)
                )

            db.commit()
            flash('Progress logged successfully!', 'success')
            return redirect(url_for('index'))

        flash(error, 'error')

    return render_template('log_form.html', task=task, logs=logs)


@app.route('/schedule')
def schedule():
    """Show the study schedule."""
    days_ahead = int(request.args.get('days', 7))
    schedule = calculate_work_schedule(days_ahead)

    # Get task details for reference
    tasks = {task['id']: task for task in get_all_tasks()}

    # Get dates in order
    today = datetime.now().date()
    dates = [today + timedelta(days=i) for i in range(days_ahead)]

    return render_template(
        'schedule.html',
        schedule=schedule,
        dates=dates,
        tasks=tasks
    )


@app.route('/calendar.ics')
def calendar_export():
    """Generate an iCalendar file for tasks and study sessions."""
    cal = Calendar()
    cal.add('prodid', '-//Flask Task Scheduler//example.com//')
    cal.add('version', '2.0')

    # Add tasks as events
    tasks = get_all_tasks()
    for task in tasks:
        event = Event()
        event.add('summary', f"[DUE] {task['title']}")

        # Due date as an all-day event
        if isinstance(task['due_date'], str):
            due_date = datetime.strptime(task['due_date'], '%Y-%m-%d').date()
        else:
            due_date = task['due_date']

        event.add('dtstart', due_date)
        event.add('dtend', due_date + timedelta(days=1))

        event.add('description', task['description'])
        event.add('priority', 5)

        # Add a reminder
        from icalendar import Alarm
        alarm = Alarm()
        alarm.add('action', 'DISPLAY')
        alarm.add('description', f"Reminder: {task['title']} is due tomorrow!")
        alarm.add('trigger', timedelta(days=-1))
        event.add_component(alarm)

        cal.add_component(event)

    # Add study sessions as events
    schedule = calculate_work_schedule(days_ahead=14)
    for date, day_tasks in schedule.items():
        for task_info in day_tasks:
            event = Event()
            task_title = task_info['title']
            hours = task_info['hours']

            event.add('summary', f"[STUDY] {task_title} ({hours} hours)")

            # Study session from 9 AM to 9 AM + hours
            start_time = datetime.combine(date, datetime.min.time()) + timedelta(hours=9)
            end_time = start_time + timedelta(hours=hours)

            event.add('dtstart', start_time)
            event.add('dtend', end_time)

            cal.add_component(event)

    # Create response with calendar data
    response = make_response(cal.to_ical())
    response.headers['Content-Type'] = 'text/calendar'
    response.headers['Content-Disposition'] = 'attachment; filename=task_schedule.ics'

    return response


@app.route('/export/pdf')
def export_pdf():
    """Export the schedule as PDF using xhtml2pdf as an alternative."""
    try:
        # Import xhtml2pdf
        from xhtml2pdf import pisa

        days_ahead = int(request.args.get('days', 7))
        schedule = calculate_work_schedule(days_ahead)

        # Get task details for reference
        tasks = {task['id']: task for task in get_all_tasks()}

        # Get dates in order
        today = datetime.now().date()
        dates = [today + timedelta(days=i) for i in range(days_ahead)]

        # Create HTML content
        html_content = f"""
        <!DOCTYPE html>
        <html>
        <head>
            <meta charset="UTF-8">
            <title>Study Schedule</title>
            <style>
                @page {{ size: letter; margin: 1cm; }}
                body {{ font-family: Helvetica, Arial, sans-serif; margin: 20px; font-size: 12px; }}
                h1 {{ color: #0d6efd; text-align: center; font-size: 24px; }}
                h2 {{ color: #0d6efd; margin-top: 20px; font-size: 18px; }}
                h3 {{ font-size: 16px; margin: 0; }}
                .day {{ 
                    border: 1px solid #ddd; 
                    margin-bottom: 15px; 
                    padding: 10px;
                }}
                .day-header {{ 
                    background-color: #f0f0f0; 
                    padding: 5px 10px;
                    margin: -10px -10px 10px -10px;
                }}
                .today {{ background-color: #0d6efd; color: white; }}
                .task {{ margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px dashed #eee; }}
                .total {{ margin-top: 10px; font-weight: bold; }}
                table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                th {{ background-color: #f0f0f0; }}
                .footer {{ text-align: center; font-size: 10px; color: #777; margin-top: 30px; }}
            </style>
        </head>
        <body>
            <h1>Study Schedule</h1>
            <p style="text-align: center;">Generated on {today.strftime('%A, %B %d, %Y')}</p>
        """

        # Add each day's schedule
        html_content += "<h2>Daily Schedule</h2>"

        for date in dates:
            day_name = date.strftime('%A')
            day_tasks = schedule[date]
            is_today = date == today
            is_weekend = day_name in ['Saturday', 'Sunday']

            html_content += f"""
            <div class="day">
                <div class="day-header {'today' if is_today else ''}">
                    <h3>{'Today - ' if is_today else ''}{date.strftime('%A, %B %d, %Y')}</h3>
                </div>
                <div class="day-body">
            """

            if day_tasks:
                for task_info in day_tasks:
                    if task_info['hours'] > 0:
                        html_content += f"""
                        <div class="task">
                            <div><strong>{task_info['title']}</strong></div>
                            <div>{task_info['hours']} hours</div>
                        </div>
                        """

                total_hours = sum(task['hours'] for task in day_tasks)
                html_content += f"""
                <div class="total">
                    Total: {total_hours} hours
                    {'<span style="color: #d9534f;"> (Heavy workload)</span>' if total_hours > 4 else ''}
                </div>
                """
            else:
                html_content += "<p>No tasks scheduled for this day.</p>"

            html_content += """
                </div>
            </div>
            """

        # Add task table
        html_content += """
        <h2>Task Overview</h2>
        <table>
            <thead>
                <tr>
                    <th>Task</th>
                    <th>Due Date</th>
                    <th>Hours Completed</th>
                    <th>Total Hours</th>
                </tr>
            </thead>
            <tbody>
        """

        for task_id, task in tasks.items():
            due_date = task['due_date']
            if isinstance(due_date, datetime):
                due_date = due_date.strftime('%Y-%m-%d')
            elif isinstance(due_date, date):
                due_date = due_date.strftime('%Y-%m-%d')
            html_content += f"""
            <tr>
                <td>{task['title']}</td>
                <td>{due_date}</td>
                <td>{task['hours_completed']} hours</td>
                <td>{task['estimated_hours']} hours</td>
            </tr>
            """

        html_content += """
            </tbody>
        </table>

        <div class="footer">
            <p>TaskScheduler - Keep Your Studies on Track</p>
        </div>
        </body>
        </html>
        """

        # Create a temporary file for the output PDF
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
        temp_filename = temp_file.name
        temp_file.close()

        # Convert HTML to PDF
        with open(temp_filename, "wb") as pdf_file:
            pisa_status = pisa.CreatePDF(html_content, dest=pdf_file)

        # Check if conversion was successful
        if pisa_status.err:
            # If PDF conversion fails, provide HTML instead
            response = make_response(html_content)
            response.headers["Content-Type"] = "text/html"
            response.headers["Content-Disposition"] = "attachment; filename=study_schedule.html"
            return response

        # Send the PDF file
        response = send_file(
            temp_filename,
            as_attachment=True,
            download_name='study_schedule.pdf',
            mimetype='application/pdf'
        )

        # Clean up the temporary file after sending
        @after_this_request
        def cleanup(response):
            try:
                os.unlink(temp_filename)
            except:
                pass
            return response

        return response

    except ImportError:
        # If xhtml2pdf is not installed, try WeasyPrint
        try:
            from weasyprint import HTML

            days_ahead = int(request.args.get('days', 7))
            schedule = calculate_work_schedule(days_ahead)

            # Get task details for reference
            tasks = {task['id']: task for task in get_all_tasks()}

            # Get dates in order
            today = datetime.now().date()
            dates = [today + timedelta(days=i) for i in range(days_ahead)]

            # Create a simple HTML structure directly
            html_content = f"""
            <!DOCTYPE html>
            <html>
            <head>
                <meta charset="UTF-8">
                <title>Study Schedule</title>
                <style>
                    body {{ font-family: Arial, sans-serif; margin: 20px; }}
                    h1 {{ color: #0d6efd; text-align: center; }}
                    h2 {{ color: #0d6efd; margin-top: 20px; }}
                    .day {{ 
                        border: 1px solid #ddd; 
                        margin-bottom: 15px; 
                        padding: 10px;
                        border-radius: 5px;
                    }}
                    .day-header {{ 
                        background-color: #f0f0f0; 
                        padding: 5px 10px;
                        margin: -10px -10px 10px -10px;
                        border-radius: 5px 5px 0 0;
                    }}
                    .today {{ background-color: #0d6efd; color: white; }}
                    .task {{ margin-bottom: 8px; padding-bottom: 8px; border-bottom: 1px dashed #eee; }}
                    .total {{ margin-top: 10px; font-weight: bold; }}
                    table {{ width: 100%; border-collapse: collapse; margin: 20px 0; }}
                    th, td {{ border: 1px solid #ddd; padding: 8px; text-align: left; }}
                    th {{ background-color: #f0f0f0; }}
                </style>
            </head>
            <body>
                <h1>Study Schedule</h1>
                <p style="text-align: center;">Generated on {today.strftime('%A, %B %d, %Y')}</p>
            """

            # Add each day's schedule
            for date in dates:
                day_name = date.strftime('%A')
                day_tasks = schedule[date]
                is_today = date == today

                html_content += f"""
                <div class="day">
                    <div class="day-header {'today' if is_today else ''}">
                        <h3>{'Today - ' if is_today else ''}{date.strftime('%A, %B %d, %Y')}</h3>
                    </div>
                    <div class="day-body">
                """

                if day_tasks:
                    for task_info in day_tasks:
                        if task_info['hours'] > 0:
                            html_content += f"""
                            <div class="task">
                                <div><strong>{task_info['title']}</strong></div>
                                <div>{task_info['hours']} hours</div>
                            </div>
                            """

                    total_hours = sum(task['hours'] for task in day_tasks)
                    html_content += f"""
                    <div class="total">
                        Total: {total_hours} hours
                        {'<span style="color: #d9534f;"> (Heavy workload)</span>' if total_hours > 4 else ''}
                    </div>
                    """
                else:
                    html_content += "<p>No tasks scheduled for this day.</p>"

                html_content += """
                    </div>
                </div>
                """

            html_content += """
            </body>
            </html>
            """

            # Create a temporary file
            temp_file = tempfile.NamedTemporaryFile(delete=False, suffix='.pdf')
            temp_filename = temp_file.name
            temp_file.close()

            # Generate PDF
            HTML(string=html_content).write_pdf(temp_filename)

            # Send the file as response
            response = send_file(
                temp_filename,
                as_attachment=True,
                download_name='study_schedule.pdf',
                mimetype='application/pdf'
            )

            # Clean up the temporary file after sending
            @after_this_request
            def cleanup(response):
                try:
                    os.unlink(temp_filename)
                except:
                    pass
                return response

            return response

        except Exception as e:
            print(f"PDF generation error: {e}")

            # If both PDF methods fail, return HTML directly
            days_ahead = int(request.args.get('days', 7))
            schedule = calculate_work_schedule(days_ahead)

            # Get task details for reference
            tasks = {task['id']: task for task in get_all_tasks()}

            # Get dates in order
            today = datetime.now().date()
            dates = [today + timedelta(days=i) for i in range(days_ahead)]

            # Render template to HTML
            html_content = render_template(
                'schedule_pdf.html',
                schedule=schedule,
                dates=dates,
                tasks=tasks
            )

            response = make_response(html_content)
            response.headers["Content-Type"] = "text/html"
            response.headers["Content-Disposition"] = "attachment; filename=study_schedule.html"
            return response


# Error handling
@app.errorhandler(HTTPException)
def handle_exception(e):
    """Handle HTTP exceptions."""
    return render_template('error.html', error=e), e.code


# Function to check and initialize the database on startup
def check_db_initialized():
    if not os.path.exists(app.config['DATABASE']):
        print("Database not found, initializing now...")
        try:
            init_db()
            print("Database initialized successfully.")
        except Exception as e:
            print(f"Error initializing database: {e}")
    else:
        print("Database already exists, no initialization needed.")


# Run the application
if __name__ == '__main__':
    with app.app_context():
        check_db_initialized()
    app.run(debug=True)