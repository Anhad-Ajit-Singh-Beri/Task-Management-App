from flask import Flask, render_template, request, g, session, redirect, url_for, flash, abort
from flask_session import Session
import sqlite3
from werkzeug.security import check_password_hash, generate_password_hash

app = Flask(__name__, instance_relative_config=True)
app.config.from_pyfile('config.py')
app.config['DATABASE'] = './database.db'
app.config["SESSION_PERMANENT"] = True
app.config['SEND_FILE_MAX_AGE_DEFAULT'] = 0
app.config["SESSION_TYPE"] = "filesystem"
app.config['SECRET_KEY'] = app.config['SECRET_KEY']
Session(app)

def create_tables():
    connection = sqlite3.connect(app.config['DATABASE'])
    cursor = connection.cursor()

    # Create the 'users' table
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

    # Create the 'tasks' table
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
            FOREIGN KEY (user_id) REFERENCES users(id)
            FOREIGN KEY (project_id) REFERENCES projects(id)
        )
    ''')


    connection.commit()
    connection.close()

def get_db():
    db = getattr(g, '_database', None)
    if db is None:
        db = g._database = sqlite3.connect(app.config['DATABASE'])
        # Enable foreign key support (optional)
        db.execute("PRAGMA foreign_keys = ON")
    return db

@app.teardown_appcontext
def close_connection(exception):
    db = getattr(g, '_database', None)
    if db is not None:
        db.close()

@app.after_request
def after_request(response):
    """Ensure responses aren't cached"""
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

        # Fetch user details from the database using user_id
        user_data = cursor.execute("SELECT * FROM users WHERE id = ?", (user_id,)).fetchone()

        if user_data:
            username = user_data[1]

            # Fetch unique projects associated with user's tasks
            projects = cursor.execute("SELECT * FROM projects WHERE user_id = ?", (user_id,)).fetchall()
            current = cursor.execute("SELECT name FROM projects WHERE id =?", (project_id,)).fetchone()
            # Fetch tasks based on the selected project (if any)
            tasks = []
            if project_id:
                tasks = cursor.execute("SELECT * FROM tasks WHERE user_id = ? AND project_id = ? AND status = ?", (user_id, project_id, "pending")).fetchall()
            
            db.close()

            return render_template('index.html', username=username, projects=projects, tasks=tasks, project_id = project_id, current=current)

    return render_template('register.html')


@app.route('/register', methods=['GET', 'POST'])
def register(): 
    if request.method == 'GET':
        return render_template('register.html')
    
    elif request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        confirm = request.form.get('confirm')
        
        if len(username) < 8:
            return render_template('register.html', error="Username should have atleast 8 characters")

        if not username or not password or not confirm or password != confirm:
            return render_template('register.html', error="Invalid registration details.")
        
        db = get_db()
        names = db.execute("SELECT username FROM users").fetchall()
        if (username,) in names:
            return render_template('register.html', error="Username already exists.")
        
        hash = generate_password_hash(password)
        cursor = db.cursor()
        cursor.execute("INSERT INTO users (username, hash) VALUES (?, ?)", (username, hash))
        db.commit()

        # Log in the user after successful registration
        user_data = cursor.execute("SELECT * FROM users WHERE username = ?", (username,)).fetchone()
        session['user_id'] = user_data[0]

        return redirect(url_for('index'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'GET':
        return render_template("login.html")
    
    elif request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password: 
            return render_template('login.html', error="Invalid login details.")

        db = get_db()
        cursor = db.cursor()
        rows = cursor.execute("SELECT * FROM users WHERE username = ?", (username,))

        user_data = rows.fetchone()
        if user_data and check_password_hash(user_data[2], password):
            # Log in the user
            session['user_id'] = user_data[0]
            return redirect(url_for('index'))
        else: 
            return render_template('login.html', error="Invalid login details.")

@app.route('/logout', methods=['POST'])
def logout():
    session.pop('user_id', None)
    return redirect(url_for('login'))

@app.route('/index/<int:project_id>', methods=['POST'])
def task(project_id):
    if request.method == 'POST':
        title = request.form.get('title')
        due_date = request.form.get('due_date')
        priority = request.form.get('priority')
        description = request.form.get('description')
        category = request.form.get('category')        

        user_id = session.get('user_id')
        db = get_db()
        cursor = db.cursor()

        projects = cursor.execute("SELECT * FROM projects WHERE user_id = ?", (user_id,)).fetchall()

        if not title:
            return render_template('index.html', error="No Subject Added", projects=projects)

        cursor.execute("""
            INSERT INTO tasks (title, user_id, due_date, priority, desc, category, project_id)
            VALUES (?, ?, ?, ?, ?, ?, ?)""",
            (title, user_id, due_date, priority, description, category, project_id))        

        db.commit()
        db.close()

    return redirect(url_for('index', project_id=project_id))


@app.route('/create_project', methods=['POST'])
def create_project():
    project = request.form.get('project')
    user_id = session.get('user_id')

    db= get_db()
    cursor = db.cursor()
    names = db.execute("SELECT name FROM projects WHERE user_id = ?", (user_id,)).fetchall()

    if not (project,) in names:
        cursor.execute("INSERT INTO projects (name, user_id) VALUES (?, ?)", (project, user_id))
    else: 
        return render_template('404.html', error="Project Already Exists")
    
    db.commit()
    db.close()
    return redirect(url_for('index'))

@app.route('/delete_task/<int:task_id>', methods=['POST'])
def delete_task(task_id):
    db = get_db()
    cursor = db.cursor()
    project_id = cursor.execute("SELECT project_id FROM tasks WHERE id = ? AND user_id = ?", (task_id, session['user_id'])).fetchall()[0][0]
    cursor.execute("DELETE FROM tasks WHERE id = ? AND project_id = ? AND user_id = ?", (task_id, project_id, session['user_id']))
    db.commit()
    db.close()
    return redirect(url_for('index', project_id = project_id))


@app.route('/filter/<category>/<criteria>')
def filter_and_sort_tasks(category, criteria):
    if 'user_id' in session:
        user_id = session['user_id']
        db = get_db()
        cursor = db.cursor()

        # Fetch user's tasks based on category
        project_id = cursor.execute("SELECT project_id FROM tasks WHERE id = ? AND category = ?", (user_id, category)).fetchall()[0][0]
        tasks = cursor.execute("SELECT * FROM tasks WHERE user_id = ? AND category = ?", (user_id, category)).fetchall()

        # Sort the filtered tasks based on the specified criteria
        if criteria == 'title':
            tasks.sort(key=lambda x: x[1])  # Sort by title
        elif criteria == 'due_date':
            tasks.sort(key=lambda x: x[2] if x[2] else '9999-12-31')  # Sort by due date
        elif criteria == 'priority':
            tasks.sort(key=lambda x: x[3])  # Sort by priority

        db.close()

        return render_template('index.html', project_id = project_id, tasks=tasks, active_filter=category, active_sort=criteria)

    return render_template('login.html')


@app.route('/sort/<criteria>')
def sort_tasks(criteria):
    if 'user_id' in session:
        user_id = session['user_id']
        db = get_db()
        cursor = db.cursor()

        # Fetch user's tasks based on sorting criteria
        if criteria == 'title':
            tasks = cursor.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY title", (user_id,)).fetchall()
        elif criteria == 'due_date':
            tasks = cursor.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY due_date", (user_id,)).fetchall()
        elif criteria == 'priority':
            tasks = cursor.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY priority", (user_id,)).fetchall()
        else:
            tasks = cursor.execute("SELECT * FROM tasks WHERE user_id = ? ORDER BY id", (user_id,)).fetchall()

        db.close()

        return render_template('index.html',tasks=tasks, active_sort=criteria)

    return render_template('login.html')


@app.route('/search_tasks/<int:project_id>', methods=['GET'])
def search_tasks(project_id):
    if 'user_id' in session:
        user_id = session['user_id']
        search_title = request.args.get('search_title', '')
        cancel_search = request.args.get('cancel_search', '')

        db = get_db()
        cursor = db.cursor()

        projects = cursor.execute("SELECT * FROM projects WHERE user_id = ?", (user_id,)).fetchall()
        current = cursor.execute("SELECT name FROM projects WHERE id =?", (project_id,)).fetchone()

        # If cancel search is requested, fetch all tasks
        if cancel_search:
            tasks = cursor.execute("SELECT * FROM tasks WHERE user_id = ? AND project_id = ? AND status = ?", (user_id, project_id, "pending")).fetchall()
        else:
            # Fetch tasks based on the search title
            tasks = cursor.execute("SELECT * FROM tasks WHERE user_id = ? AND title LIKE ? AND project_id = ? AND status = ?", (user_id, f'%{search_title}%', project_id, "pending")).fetchall()

        db.close()

        return render_template('index.html', tasks=tasks, project_id=project_id, projects=projects, current=current)

    return render_template('login.html')



def get_user_points(user_id):
    db = get_db()
    cursor = db.cursor()
    points = cursor.execute("SELECT points FROM users WHERE id = ?", (user_id,)).fetchone()
    db.close()
    return points[0] if points else 0


# @app.route('/show/<int:project_id>', methods=['GET'])
# def show():
#     user_id = session['user_id']

#     db = get_db()
#     cursor = db.cursor()
#     tasks = cursor.execute("SELECT * FROM tasks WHERE user_id = ? AND project_id = ? AND status = ?", (user_id,project_id, "pending")).fetchall()


@app.route('/complete_task/<int:task_id>', methods=['POST'])
def complete_task(task_id):
    user_id = session['user_id']

    if not user_id:
        return redirect(url_for('login'))

    db = get_db()
    cursor = db.cursor()
    project_id = cursor.execute("SELECT project_id FROM tasks WHERE id = ? AND user_id = ?", (task_id, session['user_id'])).fetchall()[0][0]
    task_data = cursor.execute("SELECT * FROM tasks WHERE id = ? AND user_id = ? AND status != 'completed'", (task_id, user_id)).fetchall()

    if not task_data:
        flash("Task not found, does not belong to the user, or is already completed.")
        return redirect(url_for('index'))

    # Update task status to completed
    cursor.execute("UPDATE tasks SET status = 'completed' WHERE id = ?", (task_id,))

    # Earn points (you can adjust the points based on your criteria)
    earned_points = 10
    cursor.execute("UPDATE users SET points = points + ? WHERE id = ?", (earned_points, user_id))
    flash(f"Congratulations! You have completed a task!")

    db.commit()
    db.close()
    
    return redirect(url_for('index', project_id=project_id))

@app.route('/edit_task/<int:task_id>', methods=['POST'])
def edit_task(task_id):
    if 'user_id' not in session:
        return redirect(url_for('login'))

    user_id = session['user_id']
    db = get_db()
    cursor = db.cursor()

    # Update the task with the new data
    title = request.form.get('title')
    due_date = request.form.get('due_date')
    priority = request.form.get('priority')
    description = request.form.get('description')
    category = request.form.get('category')

    project_id = cursor.execute("SELECT project_id FROM tasks WHERE id = ? AND user_id = ?", (task_id, session['user_id'])).fetchall()[0][0]
    cursor.execute("""
        UPDATE tasks
        SET title = ?, due_date = ?, priority = ?, desc = ?, category = ?
        WHERE id = ? AND user_id = ?
    """, (title, due_date, priority, description, category, task_id, user_id))

    db.commit()
    db.close()

    return redirect(url_for('index', project_id=project_id ))


if __name__ == '__main__':
    create_tables()
    app.run(debug=False)
