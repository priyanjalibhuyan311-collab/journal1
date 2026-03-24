from flask import Flask, render_template, request, redirect, url_for, session, flash, jsonify
from functools import wraps
import os
from datetime import datetime
from dotenv import load_dotenv

try:
    from . import database
except ImportError:
    import database

BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
load_dotenv(os.path.join(BASE_DIR, '.env'))
app = Flask(
    __name__,
    template_folder=os.path.join(BASE_DIR, 'templates'),
    static_folder=os.path.join(BASE_DIR, 'static')
)
app.secret_key = os.getenv('SECRET_KEY', 'dev-secret-key-change-me')


@app.template_filter('format_dt')
def format_dt(value, fmt='%Y-%m-%d'):
    if value is None:
        return ''

    if isinstance(value, datetime):
        return value.strftime(fmt)

    text = str(value)
    if fmt == '%Y-%m-%d':
        return text[:10]
    if fmt == '%Y-%m-%d %H:%M':
        return text[:16]
    return text

# Initialize database on startup
database.init_db()

# Login required decorator
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash('Please log in to access this page.', 'warning')
            return redirect(url_for('login'))
        return f(*args, **kwargs)
    return decorated_function

# Routes
@app.route('/')
def index():
    if 'user_id' in session:
        return redirect(url_for('dashboard'))
    return render_template('index.html')

@app.route('/register', methods=['GET', 'POST'])
def register():
    if request.method == 'POST':
        username = request.form['username'].strip()
        email = request.form['email'].strip()
        password = request.form['password']
        confirm_password = request.form['confirm_password']
        
        # Validation
        if not username or not email or not password:
            flash('All fields are required.', 'error')
            return render_template('register.html')
        
        if password != confirm_password:
            flash('Passwords do not match.', 'error')
            return render_template('register.html')
        
        if len(password) < 6:
            flash('Password must be at least 6 characters.', 'error')
            return render_template('register.html')
        
        # Create user
        user_id = database.create_user(username, email, password)
        if user_id:
            session['user_id'] = user_id
            session['username'] = username
            flash('Registration successful! Welcome to your journal.', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Username or email already exists.', 'error')
    
    return render_template('register.html')

@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        username = request.form['username'].strip()
        password = request.form['password']
        
        user = database.get_user_by_username(username)
        if user and database.verify_password(user, password):
            session['user_id'] = user['id']
            session['username'] = user['username']
            flash('Welcome back!', 'success')
            return redirect(url_for('dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('login.html')

@app.route('/logout')
def logout():
    session.clear()
    flash('You have been logged out.', 'info')
    return redirect(url_for('index'))

@app.route('/dashboard')
@login_required
def dashboard():
    journals = database.get_journals_by_user(session['user_id'])
    stats = database.get_journal_stats(session['user_id'])
    return render_template('dashboard.html', journals=journals, stats=stats)

@app.route('/journal/new', methods=['GET', 'POST'])
@login_required
def create_journal():
    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        mood = request.form.get('mood', '')
        is_public = request.form.get('is_public') == 'on'
        
        if not title or not content:
            flash('Title and content are required.', 'error')
            return render_template('create_journal.html')
        
        journal_id = database.create_journal(
            session['user_id'], title, content, mood, is_public
        )
        flash('Journal entry created successfully!', 'success')
        return redirect(url_for('dashboard'))
    
    return render_template('create_journal.html')

@app.route('/journal/<int:journal_id>')
def view_journal(journal_id):
    journal = database.get_journal_by_id(journal_id)
    
    if not journal:
        flash('Journal not found.', 'error')
        return redirect(url_for('index'))
    
    # Check access permissions
    is_owner = 'user_id' in session and session['user_id'] == journal['user_id']
    
    if not journal['is_public'] and not is_owner:
        flash('This journal is private.', 'error')
        return redirect(url_for('index'))
    
    return render_template('view_journal.html', journal=journal, is_owner=is_owner)

@app.route('/journal/<int:journal_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_journal(journal_id):
    journal = database.get_journal_by_id(journal_id)
    
    if not journal:
        flash('Journal not found.', 'error')
        return redirect(url_for('dashboard'))
    
    if journal['user_id'] != session['user_id']:
        flash('You can only edit your own journals.', 'error')
        return redirect(url_for('dashboard'))
    
    if request.method == 'POST':
        title = request.form['title'].strip()
        content = request.form['content'].strip()
        mood = request.form.get('mood', '')
        is_public = request.form.get('is_public') == 'on'
        
        if not title or not content:
            flash('Title and content are required.', 'error')
            return render_template('edit_journal.html', journal=journal)
        
        database.update_journal(journal_id, title, content, mood, is_public)
        flash('Journal updated successfully!', 'success')
        return redirect(url_for('view_journal', journal_id=journal_id))
    
    return render_template('edit_journal.html', journal=journal)

@app.route('/journal/<int:journal_id>/delete', methods=['POST'])
@login_required
def delete_journal(journal_id):
    journal = database.get_journal_by_id(journal_id)
    
    if not journal:
        flash('Journal not found.', 'error')
        return redirect(url_for('dashboard'))
    
    if journal['user_id'] != session['user_id']:
        flash('You can only delete your own journals.', 'error')
        return redirect(url_for('dashboard'))
    
    database.delete_journal(journal_id)
    flash('Journal deleted successfully.', 'success')
    return redirect(url_for('dashboard'))

@app.route('/public')
def public_journals():
    journals = database.get_public_journals()
    return render_template('public_journals.html', journals=journals)

# API endpoints for AJAX operations
@app.route('/api/journal/<int:journal_id>/toggle-visibility', methods=['POST'])
@login_required
def toggle_visibility(journal_id):
    journal = database.get_journal_by_id(journal_id)
    
    if not journal or journal['user_id'] != session['user_id']:
        return jsonify({'error': 'Unauthorized'}), 403
    
    new_visibility = not journal['is_public']
    database.update_journal(
        journal_id, 
        journal['title'], 
        journal['content'], 
        journal['mood'], 
        new_visibility
    )
    
    return jsonify({'is_public': new_visibility})

if __name__ == '__main__':
    debug_mode = os.getenv('FLASK_DEBUG', 'true').lower() == 'true'
    port = int(os.getenv('PORT', '5000'))
    host = os.getenv('HOST', '127.0.0.1')
    app.run(debug=debug_mode, host=host, port=port)
