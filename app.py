from flask import Flask, render_template, request, g, session, redirect, url_for, flash, jsonify
from flask_session import Session
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash
from datetime import date

app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py')
app.config['DATABASE'] = './database.db'
app.config["SESSION_PERMANENT"] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config["SESSION_TYPE"] = "filesystem"
app.config['SECRET_KEY'] = app.config['SECRET_KEY']
Session(app)

def create_tables():
    with sqlite3.connect(app.config['DATABASE']) as connection:
        cursor = connection.cursor()
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                hash TEXT NOT NULL,
                points INTEGER DEFAULT 0
            )
        ''')
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS projects (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                name TEXT, 
                user_id INTEGER, 
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS categories (
                id INTEGER PRIMARY KEY AUTOINCREMENT, 
                name TEXT, 
                user_id INTEGER, 
                FOREIGN KEY (user_id) REFERENCES users(id)
            )
        ''')

        cursor.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                title TEXT NOT NULL,
                desc TEXT,  
                due_date DATE,
                status TEXT DEFAULT 'pending',
                priority TEXT DEFAULT 'low',
                category TEXT,
                labels TEXT,
                project_id INTEGER, 
                user_id INTEGER,
                FOREIGN KEY (user_id) REFERENCES users(id),
                FOREIGN KEY (project_id) REFERENCES projects(id)
            )            
        ''')

def get_db():
    if 'db' not in g:
        g.db = sqlite3.connect(app.config['DATABASE'])
        g.db.execute("PRAGMA foreign_keys = ON")
    return g.db

@app.teardown_appcontext
def close_db(error):
    db = g.pop('db', None)
    if db is not None:
        db.close()

@app.after_request
def after_request(response):
    response.headers["Cache-Control"] = "no-cache, no-store, must-revalidate"
    response.headers["Expires"] = 0
    response.headers["Pragma"] = "no-cache"
    return response

@app.route('/', methods=['GET', 'POST'])
@app.route('/home', methods=['GET', 'POST'])
@app.route('/project/<int:project_id>', methods=['GET', 'POST'])
def index(project_id=None):
    if 'user_id' in session:
        user_id = session['user_id']
        db = get_db()
        cursor = db.cursor()
        user_data = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

        if user_data:
            username = user_data[1]
            projects = cursor.execute("SELECT * FROM projects WHERE user_id = ?", (user_id,)).fetchall()
            current = cursor.execute("SELECT name FROM projects WHERE id = ?", (project_id,)).fetchone()
            points = cursor.execute("SELECT points FROM users WHERE id = ?", (user_id,)).fetchone()
            categories = cursor.execute("SELECT name FROM categories WHERE user_id = ?", (user_id,)).fetchall()

            sort_by = request.args.get('sort_by', 'priority')
            if sort_by == 'priority':
                tasks = get_tasks_sorted_by_priority(user_id, project_id)
            elif sort_by == 'due_date':
                tasks = get_tasks_sorted_by_due_date(user_id, project_id)
            elif sort_by == 'title':
                tasks = get_tasks_sorted_by_title(user_id, project_id)
            else:
                tasks = cursor.execute("SELECT * FROM tasks WHERE user_id = ? AND project_id = ? AND status=?", (user_id, project_id, 'pending')).fetchall()

            return render_template('index.html', username=username, projects=projects, tasks=tasks, project_id=project_id, current=current, points=points, categories=categories)

    return render_template('register.html')



@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm = request.form.get('confirm')

        if len(username) < 8:
            return render_template('register.html', error="Username should have at least 8 characters")

        if not username or not password or not confirm or password != confirm:
            return render_template('register.html', error="Invalid registration details.")

        db = get_db()
        cursor = db.cursor()
        if cursor.execute("SELECT username FROM users WHERE username = ?", (username,)).fetchone():
            return render_template('register.html', error="Username already exists.")

        hash = generate_password_hash(password)
        cursor.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (username, hash))
        db.commit()

        user_data = cursor.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        session['user_id'] = user_data[0]

        return redirect(url_for('index'))

    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')

        if not username or not password:
            return render_template('login.html', error="Invalid login details.")

        db = get_db()
        cursor = db.cursor()
        user_data = cursor.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()

        if user_data and check_password_hash(user_data[2], password):
            session['user_id'] = user_data[0]
            return redirect(url_for('index'))

        return render_template('login.html', error="Invalid login details.")

    return render_template('login.html')

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/index/<int:project_id>', methods=['POST'])
def task(project_id):
    if 'user_id' in session:
        user_id = session['user_id']
        title = request.form.get('title')
        due_date = request.form.get('due_date')
        priority = request.form.get('priority')
        description = request.form.get('description')
        category = request.form.get('category')

        if not title:
            db = get_db()
            projects = db.execute("SELECT * FROM projects WHERE user_id = ?", (user_id,)).fetchall()
            return render_template('index.html', error="No Subject Added", projects=projects)

        db = get_db()
        cursor = db.cursor()
        cursor.execute("""
            INSERT INTO tasks (title, user_id, due_date, priority, desc, category, project_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)
        """, (title, user_id, due_date, priority, description, category, project_id))
        db.commit()

    return redirect(url_for('index', project_id=project_id))

@app.route('/create_project', methods=['POST'])
def create_project():
    project = request.form.get('project')
    user_id = session.get('user_id')

    if user_id and project:
        db = get_db()
        cursor = db.cursor()
        if not cursor.execute("SELECT name FROM projects WHERE user_id = ? AND name = ?", (user_id, project)).fetchone():
            cursor.execute("INSERT INTO projects (name, user_id) VALUES (?, ?)", (project, user_id))
            db.commit()
        else:
            return render_template('404.html', error="Project Already Exists")

    return redirect(url_for('index'))

@app.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    if 'user_id' in session:
        user_id = session['user_id']
        db = get_db()
        cursor = db.cursor()
        project_id = cursor.execute("SELECT project_id FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)).fetchone()[0]
        cursor.execute("DELETE FROM tasks WHERE id = ? AND project_id = ? AND user_id = ?", (task_id, project_id, user_id))
        db.commit()

        return redirect(url_for('index', project_id=project_id))

    return redirect(url_for('login'))

@app.route('/search_tasks/<int:project_id>', methods=['GET'])
def search_tasks(project_id):
    if 'user_id' in session:
        user_id = session['user_id']
        search_title = request.args.get('search_title', '')
        cancel_search = request.args.get('cancel_search', '')

        db = get_db()
        cursor = db.cursor()
        projects = cursor.execute("SELECT * FROM projects WHERE user_id = ?", (user_id,)).fetchall()
        current = cursor.execute("SELECT name FROM projects WHERE id = ?", (project_id,)).fetchone()
        points = cursor.execute("SELECT points FROM users WHERE id = ?", (user_id,)).fetchone()
        tasks = cursor.execute("SELECT * FROM tasks WHERE user_id = ? AND project_id = ? AND status = ?", (user_id, project_id, "pending")).fetchall() if project_id else []
        categories = cursor.execute("SELECT name FROM categories WHERE user_id = ?", (user_id,)).fetchall()

        if cancel_search:
            tasks = cursor.execute("SELECT * FROM tasks WHERE user_id = ? AND project_id = ? AND status = ?", (user_id, project_id, "pending")).fetchall()
        else:
            tasks = cursor.execute("SELECT * FROM tasks WHERE user_id = ? AND title LIKE ? AND project_id = ? AND status = ?", (user_id, f'%{search_title}%', project_id, "pending")).fetchall()

        return render_template('index.html', projects=projects, tasks=tasks, project_id=project_id, current=current, points=points, categories=categories)

    return render_template('login.html')

@app.route('/complete_task/<int:task_id>', methods=['POST'])
def complete_task(task_id):
    if 'user_id' in session:
        user_id = session['user_id']
        db = get_db()
        cursor = db.cursor()
        project_id = cursor.execute("SELECT project_id FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)).fetchone()[0]
        task_data = cursor.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ? AND status != 'completed'", (task_id, user_id)).fetchone()

        if not task_data:
            flash("Task not found, does not belong to the user, or is already completed.")
            return redirect(url_for('index'))

        cursor.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (task_id,))
        cursor.execute("UPDATE users SET points = points + 10 WHERE id = ?", (user_id,))
        db.commit()
        flash("Congratulations! You have completed a task!")

        return redirect(url_for('index', project_id=project_id))

    return redirect(url_for('login'))

@app.route('/edit_task/<int:task_id>', methods=['POST'])
def edit_task(task_id):
    if 'user_id' in session:
        user_id = session['user_id']
        db = get_db()
        cursor = db.cursor()

        title = request.form.get('title')
        due_date = request.form.get('due_date')
        priority = request.form.get('priority')
        description = request.form.get('description')
        category = request.form.get('category')

        project_id = cursor.execute("SELECT project_id FROM tasks WHERE id = ? AND user_id = ?", (task_id, user_id)).fetchone()[0]
        cursor.execute("""
            UPDATE tasks
            SET title = ?, due_date = ?, priority = ?, desc = ?, category = ?
            WHERE id = ? AND user_id = ?
        """, (title, due_date, priority, description, category, task_id, user_id))
        db.commit()

        return redirect(url_for('index', project_id=project_id))

    return redirect(url_for('login'))

@app.route('/calendar_events')
def calendar_events():
    try:
        if 'user_id' in session:
            user_id = session['user_id']
            db = get_db()
            cursor = db.cursor()
            events = cursor.execute("SELECT title, due_date, project_id FROM tasks WHERE user_id = ? AND due_date IS NOT NULL AND status=?", (user_id, "pending")).fetchall()

            events_list = [{'title': event[0], 'start': event[1], 'description': event[2]} for event in events]

            db.close()

            # Return JSON response with events list
            return jsonify(events_list)

        return jsonify({'error': 'User session not found or expired'}), 403
    except Exception as e:
        return jsonify({'error': str(e)}), 500


@app.route('/progress', methods=['GET'])
def progress():
    if 'user_id' in session:
        user_id = session['user_id']
        db = get_db()
        cursor = db.cursor()
        prog_list = []

        pending = cursor.execute("SELECT count(*) FROM tasks WHERE user_id = ? AND status = ?", (user_id, "pending"))
        for i in cursor:
            prog_list.append(i)
        total = cursor.execute("SELECT count(*) FROM tasks WHERE user_id = ?", (user_id, ))
        for i in cursor:
            prog_list.append(i)
        
        return jsonify(prog_list)

@app.route('/categories', methods=['POST'])
def categories():
     if 'user_id' in session:
        user_id = session['user_id']
        db = get_db()
        cursor = db.cursor()
        name = request.form.get('category')
        project_id = 1

        cursor.execute("INSERT INTO categories (name, user_id) VALUES (?, ?)",(name , user_id))
        db.commit()
        db.close()

        return redirect(url_for('index'))
    #  keep offcanvas open after adding. No reload


@app.route('/notification', methods=['GET'])
def notifications():
     if 'user_id' in session:
        user_id = session['user_id']
        db = get_db()
        cursor = db.cursor()
        today = date.today().strftime("%Y %m %d")
        dates=[today]

        cursor.execute("SELECT due_date FROM tasks WHERE user_id=? AND status =?", (user_id, 'pending'))
        for i in cursor: 
            dates.append(i)
        
        return jsonify(dates)

@app.route('/delete_category/<name>', methods=['GET'])
def delete_category(name):
    if 'user_id' in session:
        user_id = session['user_id']
        db = get_db()
        cursor = db.cursor()

        cursor.execute("DELETE FROM categories WHERE user_id = ? AND name = ?", (user_id, name))
        db.commit()

        return redirect(url_for('index'))

    return redirect(url_for('login'))


def get_tasks_sorted_by_priority(user_id, project_id):
    db = get_db()
    cursor = db.cursor()
    tasks = cursor.execute("""
        SELECT * FROM tasks WHERE user_id = ? AND project_id = ?  AND status=? ORDER BY 
        CASE
            WHEN priority = 'high' THEN 1
            WHEN priority = 'medium' THEN 2
            WHEN priority = 'low' THEN 3
            ELSE 4
        END
    """, (user_id, project_id, 'pending')).fetchall()
    return tasks

def get_tasks_sorted_by_due_date(user_id, project_id):
    db = get_db()
    cursor = db.cursor()
    tasks = cursor.execute("""
        SELECT * FROM tasks WHERE user_id = ? AND project_id = ? AND status=? ORDER BY due_date ASC
    """, (user_id, project_id, 'pending')).fetchall()
    return tasks

def get_tasks_sorted_by_title(user_id, project_id):
    db = get_db()
    cursor = db.cursor()
    tasks = cursor.execute("""
        SELECT * FROM tasks WHERE user_id = ? AND project_id = ? AND status=? ORDER BY title ASC
    """, (user_id, project_id, 'pending')).fetchall()
    return tasks




if __name__ == '__main__':
    create_tables()
    app.run(debug=True)
