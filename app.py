from flask import Flask, request, render_template, redirect, url_for, flash, session
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime
from calendar import monthrange

app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'my-secret-key-123')  # Ασφαλές κλειδί για το cloud

DB_NAME = 'database.db'

def get_db():
    conn = sqlite3.connect(DB_NAME)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    with get_db() as conn:
        conn.execute('''
            CREATE TABLE IF NOT EXISTS users (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT UNIQUE NOT NULL,
                password TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS tasks (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                task TEXT NOT NULL,
                deadline TEXT NOT NULL,
                priority TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS contacts (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                name TEXT NOT NULL,
                phone TEXT NOT NULL
            )
        ''')
        conn.execute('''
            CREATE TABLE IF NOT EXISTS notes (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                username TEXT NOT NULL,
                title TEXT,
                content TEXT NOT NULL
            )
        ''')
        conn.commit()

init_db()

def load_user_db(username):
    with get_db() as conn:
        user = conn.execute('SELECT * FROM users WHERE username = ?', (username,)).fetchone()
        return user

def save_user_db(username, password_hash):
    with get_db() as conn:
        conn.execute('INSERT INTO users (username, password) VALUES (?, ?)', (username, password_hash))
        conn.commit()

def login_required(f):
    def wrap(*args, **kwargs):
        if 'username' not in session:
            flash('Παρακαλώ συνδεθείτε πρώτα.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    wrap.__name__ = f.__name__
    return wrap

@app.route('/')
@login_required
def index():
    username = session['username']
    filter_priority = request.args.get('filter_priority')
    
    with get_db() as conn:
        if filter_priority:
            cursor = conn.execute('SELECT id, task, deadline, priority FROM tasks WHERE username = ? AND priority = ?', (username, filter_priority))
        else:
            cursor = conn.execute('SELECT id, task, deadline, priority FROM tasks WHERE username = ?', (username,))
        tasks = cursor.fetchall()
        
    return render_template('index.html', tasks=tasks, username=username)

@app.route('/', methods=['POST'])
@login_required
def add_task():
    username = session['username']
    task = request.form['task']
    deadline = request.form['deadline']
    priority = request.form['priority']
    
    with get_db() as conn:
        conn.execute('INSERT INTO tasks (username, task, deadline, priority) VALUES (?, ?, ?, ?)', 
                     (username, task, deadline, priority))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/edit/<int:task_id>', methods=['GET', 'POST'])
@login_required
def edit_task(task_id):
    username = session['username']
    with get_db() as conn:
        if request.method == 'POST':
            task = request.form['task']
            deadline = request.form['deadline']
            priority = request.form['priority']
            conn.execute('UPDATE tasks SET task = ?, deadline = ?, priority = ? WHERE id = ? AND username = ?',
                         (task, deadline, priority, task_id, username))
            conn.commit()
            return redirect(url_for('index'))
        
        task_row = conn.execute('SELECT id, task, deadline, priority FROM tasks WHERE id = ? AND username = ?', (task_id, username)).fetchone()
    
    return render_template('edit.html', task=task_row, task_index=task_id, username=username)

@app.route('/delete/<int:task_id>')
@login_required
def delete_task(task_id):
    username = session['username']
    with get_db() as conn:
        conn.execute('DELETE FROM tasks WHERE id = ? AND username = ?', (task_id, username))
        conn.commit()
    return redirect(url_for('index'))

@app.route('/calendar')
@login_required
def calendar_view():
    username = session['username']
    month = int(request.args.get('month', datetime.now().month))
    year = int(request.args.get('year', datetime.now().year))
    _, days_in_month = monthrange(year, month)
    
    with get_db() as conn:
        tasks = conn.execute('SELECT id, task, deadline, priority FROM tasks WHERE username = ?', (username,)).fetchall()
        
    task_dict = {}
    for task in tasks:
        deadline = task['deadline']
        if deadline in task_dict:
            task_dict[deadline].append(task)
        else:
            task_dict[deadline] = [task]
            
    return render_template('calendar.html', month=month, year=year, days_in_month=days_in_month, task_dict=task_dict, username=username)

@app.route('/contacts', methods=['GET', 'POST'])
@login_required
def contacts():
    username = session['username']
    with get_db() as conn:
        if request.method == 'POST':
            name = request.form['name']
            phone = request.form['phone']
            conn.execute('INSERT INTO contacts (username, name, phone) VALUES (?, ?, ?)', (username, name, phone))
            conn.commit()
            return redirect(url_for('contacts'))
        
        contacts = conn.execute('SELECT id, name, phone FROM contacts WHERE username = ?', (username,)).fetchall()
        
    return render_template('contacts.html', contacts=contacts, username=username)

@app.route('/delete_contact/<int:contact_id>')
@login_required
def delete_contact(contact_id):
    username = session['username']
    with get_db() as conn:
        conn.execute('DELETE FROM contacts WHERE id = ? AND username = ?', (contact_id, username))
        conn.commit()
    return redirect(url_for('contacts'))

@app.route('/notes', methods=['GET', 'POST'])
@login_required
def notes():
    username = session['username']
    with get_db() as conn:
        if request.method == 'POST':
            title = request.form['title']
            content = request.form['note']
            conn.execute('INSERT INTO notes (username, title, content) VALUES (?, ?, ?)', (username, title, content))
            conn.commit()
            return redirect(url_for('notes'))
        
        notes = conn.execute('SELECT id, title, content FROM notes WHERE username = ?', (username,)).fetchall()
        
    return render_template('notes.html', notes=notes, username=username)

@app.route('/edit_note/<int:note_id>', methods=['GET', 'POST'])
@login_required
def edit_note(note_id):
    username = session['username']
    with get_db() as conn:
        if request.method == 'POST':
            title = request.form['title']
            content = request.form['note']
            conn.execute('UPDATE notes SET title = ?, content = ? WHERE id = ? AND username = ?', (title, content, note_id, username))
            conn.commit()
            return redirect(url_for('notes'))
        
        note = conn.execute('SELECT id, title, content FROM notes WHERE id = ? AND username = ?', (note_id, username)).fetchone()
        
    return render_template('edit_note.html', note=note, note_index=note_id, username=username)

@app.route('/delete_note/<int:note_id>')
@login_required
def delete_note(note_id):
    username = session['username']
    with get_db() as conn:
        conn.execute('DELETE FROM notes WHERE id = ? AND username = ?', (note_id, username))
        conn.commit()
    return redirect(url_for('notes'))

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = load_user_db(username)
        if user and check_password_hash(user['password'], password):
            session['username'] = username
            return redirect(url_for('index'))
        flash('Λάθος όνομα χρήστη ή κωδικός.', 'error')
    return render_template('login.html')

@app.route('/signup', methods=['GET', 'POST'])
def signup():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        user = load_user_db(username)
        if user:
            flash('Το όνομα χρήστη υπάρχει ήδη.', 'error')
        else:
            save_user_db(username, generate_password_hash(password))
            session['username'] = username
            flash('Επιτυχής εγγραφή!', 'success')
            return redirect(url_for('index'))
    return render_template('signup.html')

@app.route('/logout')
def logout():
    session.pop('username', None)
    return redirect(url_for('login'))

if __name__ == '__main__':
    app.run(debug=True)