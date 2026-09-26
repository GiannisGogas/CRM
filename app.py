from flask import Flask, request, render_template, redirect, url_for, flash, session
import os
import sqlite3
from werkzeug.security import generate_password_hash, check_password_hash
from datetime import datetime, timedelta
from calendar import monthrange
from functools import wraps

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

        conn.execute('''
        CREATE TABLE IF NOT EXISTS contracts (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT NOT NULL,
            title TEXT NOT NULL,
            client TEXT NOT NULL,
            manager TEXT NOT NULL,
            deadline TEXT NOT NULL,
            amount TEXT
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
    @wraps(f)
    def wrap(*args, **kwargs):
        if 'username' not in session:
            flash('Παρακαλώ συνδεθείτε πρώτα.', 'error')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
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
def calendar():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))
        
    # Παίρνουμε τον μήνα και το έτος από το URL (αν δεν υπάρχουν, βάζουμε τα τρέχοντα)
    now = datetime.now()
    month = request.args.get('month', type=int) or now.month
    year = request.args.get('year', type=int) or now.year
    
    # Υπολογισμός ημερών του μήνα
    days_in_month = monthrange(year, month)[1]
    
    with get_db() as conn:
        # Παίρνουμε τις εργασίες του χρήστη
        tasks = conn.execute('SELECT * FROM tasks WHERE username = ?', (username,)).fetchall()
        # Παίρνουμε και τις συμβάσεις του χρήστη
        contracts = conn.execute('SELECT * FROM contracts WHERE username = ?', (username,)).fetchall()
        
    # Δημιουργία λεξικού για τις εργασίες ανά ημερομηνία
    task_dict = {}
    for task in tasks:
        d = task['date'] # Υποθέτουμε ότι η ημερομηνία αποθηκεύεται ως 'YYYY-MM-DD'
        if d not in task_dict:
            task_dict[d] = []
        task_dict[d].append(task)
        
    return render_template('calendar.html', 
                           tasks=tasks, 
                           contracts=contracts, 
                           task_dict=task_dict, 
                           month=month, 
                           year=year, 
                           days_in_month=days_in_month, 
                           username=username)

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
def notes():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('note') # ή 'content' ανάλογα με το name στο HTML
        with get_db() as conn:
            conn.execute('INSERT INTO notes (username, title, content) VALUES (?, ?, ?)', 
                         (username, title, content))
            conn.commit()
        return redirect(url_for('notes'))
        
    with get_db() as conn:
        notes = conn.execute('SELECT * FROM notes WHERE username = ?', (username,)).fetchall()
        
    return render_template('notes.html', notes=notes, username=username)

@app.route('/edit_note/<int:note_id>', methods=['GET', 'POST'])
def edit_note(note_id):
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))
        
    with get_db() as conn:
        note = conn.execute('SELECT * FROM notes WHERE id = ? AND username = ?', (note_id, username)).fetchone()
        
    if not note:
        return redirect(url_for('notes'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        content = request.form.get('content') # Αν στο HTML το ονόμασες content
        
        with get_db() as conn:
            conn.execute('UPDATE notes SET title = ?, content = ? WHERE id = ? AND username = ?',
                         (title, content, note_id, username))
            conn.commit()
        return redirect(url_for('notes'))
        
    return render_template('edit_note.html', note=note, username=username)

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

@app.route('/contracts', methods=['GET', 'POST'])
def contracts():
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))
        
    if request.method == 'POST':
        title = request.form.get('title')
        client = request.form.get('client')
        manager = request.form.get('manager')
        deadline = request.form.get('deadline')
        amount = request.form.get('amount')
        
        with get_db() as conn:
            conn.execute('''
                INSERT INTO contracts (username, title, client, manager, deadline, amount)
                VALUES (?, ?, ?, ?, ?, ?)
            ''', (username, title, client, manager, deadline, amount))
            conn.commit()
        return redirect(url_for('contracts'))
        
    filter_type = request.args.get('filter', 'all')
    
    with get_db() as conn:
        contracts_list = conn.execute('SELECT * FROM contracts WHERE username = ?', (username,)).fetchall()
        
    # Φιλτράρισμα με βάση την προθεσμία (deadline)
    today = datetime.today().date()
    filtered_contracts = []
    
    for c in contracts_list:
        if not c['deadline']:
            continue
        try:
            d_date = datetime.strptime(c['deadline'], '%Y-%m-%d').date()
        except ValueError:
            continue
            
        diff_days = (d_date - today).days
        if diff_days < 0:
            continue # Έχει λήξει, το προσπερνάμε ή το βάζουμε παντού
            
        if filter_type == 'month' and diff_days <= 30:
            filtered_contracts.append(c)
        elif filter_type == 'quarter' and diff_days <= 90:
            filtered_contracts.append(c)
        elif filter_type == 'half' and diff_days <= 180:
            filtered_contracts.append(c)
        elif filter_type == 'year' and diff_days <= 365:
            filtered_contracts.append(c)
        elif filter_type == 'all':
            filtered_contracts.append(c)
            
    return render_template('contracts.html', contracts=filtered_contracts, username=username, current_filter=filter_type)

@app.route('/delete_contract/<int:contract_id>')
def delete_contract(contract_id):
    username = session.get('username')
    if not username:
        return redirect(url_for('login'))
        
    with get_db() as conn:
        conn.execute('DELETE FROM contracts WHERE id = ? AND username = ?', (contract_id, username))
        conn.commit()
    return redirect(url_for('contracts'))

if __name__ == '__main__':
    app.run(debug=True)