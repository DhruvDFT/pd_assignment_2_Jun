# app/blueprints/auth/__init__.py
from flask import Blueprint

auth_bp = Blueprint('auth', __name__)

from app.blueprints.auth import routes

# app/blueprints/auth/routes.py - Authentication Routes
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_user, logout_user, login_required, current_user
from app.blueprints.auth import auth_bp
from app.models.user import User
from app import db
import datetime

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login"""
    if current_user.is_authenticated:
        # Redirect based on role
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('engineer.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        
        if not username or not password:
            flash('Please provide both username and password.', 'error')
            return render_template('auth/login.html')
        
        # Find user
        user = User.query.filter_by(username=username).first()
        
        if user and user.check_password(password) and user.is_active:
            # Update last login
            user.last_login = datetime.datetime.utcnow()
            db.session.commit()
            
            # Login user
            login_user(user, remember=True)
            
            # Redirect based on role
            if user.is_admin():
                flash(f'Welcome back, Admin {user.username}!', 'success')
                return redirect(url_for('admin.dashboard'))
            else:
                flash(f'Welcome back, {user.username}!', 'success')
                return redirect(url_for('engineer.dashboard'))
        else:
            flash('Invalid username or password.', 'error')
    
    return render_template('auth/login.html')

@auth_bp.route('/logout')
@login_required
def logout():
    """User logout"""
    username = current_user.username
    logout_user()
    flash(f'Goodbye, {username}! You have been logged out successfully.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Engineer registration (Admin can also register engineers)"""
    # Only allow registration if current user is admin or no users exist
    if User.query.count() > 0 and (not current_user.is_authenticated or not current_user.is_admin()):
        flash('Registration is restricted. Please contact an administrator.', 'error')
        return redirect(url_for('auth.login'))
    
    if request.method == 'POST':
        data = request.form
        
        # Validate input
        username = data.get('username', '').strip()
        email = data.get('email', '').strip()
        password = data.get('password', '')
        confirm_password = data.get('confirm_password', '')
        engineer_id = data.get('engineer_id', '').strip()
        department = data.get('department', '').strip()
        role = data.get('role', 'engineer')
        
        errors = []
        
        if not username or len(username) < 3:
            errors.append('Username must be at least 3 characters long.')
        
        if User.query.filter_by(username=username).first():
            errors.append('Username already exists.')
        
        if not email or '@' not in email:
            errors.append('Valid email address is required.')
        
        if User.query.filter_by(email=email).first():
            errors.append('Email address already registered.')
        
        if not password or len(password) < 6:
            errors.append('Password must be at least 6 characters long.')
        
        if password != confirm_password:
            errors.append('Passwords do not match.')
        
        if role == 'engineer':
            if not engineer_id:
                errors.append('Engineer ID is required.')
            elif User.query.filter_by(engineer_id=engineer_id).first():
                errors.append('Engineer ID already exists.')
        
        if errors:
            for error in errors:
                flash(error, 'error')
            return render_template('auth/register.html')
        
        try:
            # Create user
            user = User(
                username=username,
                email=email,
                role=role,
                engineer_id=engineer_id if role == 'engineer' else None,
                department=department if role == 'engineer' else None
            )
            user.set_password(password)
            
            db.session.add(user)
            db.session.commit()
            
            flash(f'Registration successful! Welcome, {username}.', 'success')
            
            # Auto-login the new user if they're the first user (admin)
            if User.query.count() == 1:
                login_user(user)
                return redirect(url_for('admin.dashboard'))
            
            return redirect(url_for('auth.login'))
            
        except Exception as e:
            db.session.rollback()
            flash('Registration failed. Please try again.', 'error')
    
    return render_template('auth/register.html')

# app/blueprints/admin/__init__.py
from flask import Blueprint

admin_bp = Blueprint('admin', __name__)

from app.blueprints.admin import dashboard, submissions, assignments, users

# app/blueprints/admin/dashboard.py - Admin Dashboard
from flask import render_template, jsonify
from flask_login import login_required, current_user
from app.blueprints.admin import admin_bp
from app.models.user import User, UserRole
from app.models.assignment import Assignment, Submission
from app.auth.decorators import admin_required
from app import db
from datetime import datetime, timedelta

@admin_bp.route('/dashboard')
@login_required
@admin_required
def dashboard():
    """Admin dashboard with system overview"""
    
    # Calculate statistics
    total_engineers = User.query.filter_by(role=UserRole.ENGINEER, is_active=True).count()
    total_submissions = Submission.query.count()
    pending_grading = Submission.query.filter(
        Submission.admin_grade.is_(None)
    ).count()
    graded_submissions = Submission.query.filter(
        Submission.admin_grade.isnot(None),
        Submission.is_grade_released == True
    ).count()
    
    # Recent activity (last 7 days)
    recent_activities = []
    
    # Recent submissions
    recent_submissions = Submission.query.filter(
        Submission.submitted_date >= datetime.utcnow() - timedelta(days=7)
    ).order_by(Submission.submitted_date.desc()).limit(5).all()
    
    for submission in recent_submissions:
        recent_activities.append({
            'title': 'New Submission',
            'description': f'{submission.engineer.username} submitted {submission.assignment.title}',
            'timestamp': submission.submitted_date.strftime('%Y-%m-%d %H:%M')
        })
    
    # Recent registrations
    recent_users = User.query.filter(
        User.created_date >= datetime.utcnow() - timedelta(days=7),
        User.role == UserRole.ENGINEER
    ).order_by(User.created_date.desc()).limit(3).all()
    
    for user in recent_users:
        recent_activities.append({
            'title': 'New Engineer Registration',
            'description': f'{user.username} ({user.engineer_id}) joined the system',
            'timestamp': user.created_date.strftime('%Y-%m-%d %H:%M')
        })
    
    # Sort activities by timestamp
    recent_activities.sort(key=lambda x: x['timestamp'], reverse=True)
    
    return render_template('admin/dashboard.html',
                         total_engineers=total_engineers,
                         total_submissions=total_submissions,
                         pending_grading=pending_grading,
                         graded_submissions=graded_submissions,
                         recent_activities=recent_activities[:10])

@admin_bp.route('/api/dashboard-stats')
@login_required
@admin_required
def dashboard_stats_api():
    """API endpoint for live dashboard stats"""
    stats = {
        'total_engineers': User.query.filter_by(role=UserRole.ENGINEER, is_active=True).count(),
        'total_submissions': Submission.query.count(),
        'pending_grading': Submission.query.filter(Submission.admin_grade.is_(None)).count(),
        'graded_submissions': Submission.query.filter(
            Submission.admin_grade.isnot(None),
            Submission.is_grade_released == True
        ).count()
    }
    
    return jsonify({'success': True, 'stats': stats})

# app/blueprints/admin/assignments.py - Assignment Management
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.blueprints.admin import admin_bp
from app.models.assignment import Assignment
from app.models.user import User, UserRole
from app.services.notification_service import NotificationService
from app.auth.decorators import admin_required
from app import db
import datetime
import random

# Topic questions (same as your original TOPICS)
TOPICS = {
    "floorplanning": [
        "Design a floorplan for a 10mm x 10mm chip with 8 macro blocks. Discuss your placement strategy.",
        "Given a design with 3 power domains, explain how you would approach floorplanning to minimize power grid IR drop.",
        # ... (include all your original questions)
    ],
    "placement": [
        "Explain the impact of placement on timing for a design running at 1500 MHz. Discuss congestion vs timing trade-offs.",
        # ... (include all your original questions)
    ],
    "routing": [
        "Design has 2500 DRC violations after initial routing. Propose a systematic approach to resolve them.",
        # ... (include all your original questions)
    ]
}

@admin_bp.route('/create-assignment', methods=['GET', 'POST'])
@login_required
@admin_required
def create_assignment():
    """Admin creates assignments for engineers"""
    
    if request.method == 'POST':
        engineer_id = request.form.get('engineer_id')
        topic = request.form.get('topic')
        custom_title = request.form.get('custom_title', '').strip()
        due_date = request.form.get('due_date')
        points = request.form.get('points', 120, type=int)
        
        # Validation
        engineer = User.query.filter_by(id=engineer_id, role=UserRole.ENGINEER).first()
        if not engineer:
            flash('Invalid engineer selected.', 'error')
            return redirect(url_for('admin.create_assignment'))
        
        if topic not in TOPICS:
            flash('Invalid topic selected.', 'error')
            return redirect(url_for('admin.create_assignment'))
        
        try:
            due_date_obj = datetime.datetime.strptime(due_date, '%Y-%m-%d').date()
            if due_date_obj <= datetime.date.today():
                flash('Due date must be in the future.', 'error')
                return redirect(url_for('admin.create_assignment'))
        except ValueError:
            flash('Invalid due date format.', 'error')
            return redirect(url_for('admin.create_assignment'))
        
        # Check for existing active assignment for this engineer and topic
        existing = Assignment.query.filter_by(
            engineer_id=engineer_id,
            topic=topic,
            is_active=True
        ).first()
        
        if existing:
            flash(f'Engineer already has an active {topic} assignment.', 'error')
            return redirect(url_for('admin.create_assignment'))
        
        try:
            # Generate assignment ID
            timestamp = datetime.datetime.now().strftime("%Y%m%d_%H%M%S")
            assignment_id = f"PD_{topic.upper()}_{engineer.engineer_id}_{timestamp}"
            
            # Create assignment
            assignment = Assignment(
                id=assignment_id,
                title=custom_title or f"{topic.title()} Technical Assessment",
                topic=topic,
                engineer_id=engineer.id,
                questions=TOPICS[topic],
                due_date=due_date_obj,
                points=points,
                assigned_by_admin=current_user.id
            )
            
            db.session.add(assignment)
            db.session.commit()
            
            # Send notification to engineer
            notification_service = NotificationService()
            notification_service.send_assignment_notification(assignment)
            
            flash(f'Assignment created successfully for {engineer.username}!', 'success')
            return redirect(url_for('admin.view_assignments'))
            
        except Exception as e:
            db.session.rollback()
            flash('Failed to create assignment. Please try again.', 'error')
    
    # Get all active engineers
    engineers = User.query.filter_by(role=UserRole.ENGINEER, is_active=True).all()
    topics = list(TOPICS.keys())
    
    return render_template('admin/create_assignment.html', 
                         engineers=engineers, 
                         topics=topics)

@admin_bp.route('/assignments')
@login_required
@admin_required
def view_assignments():
    """Admin view of all assignments"""
    page = request.args.get('page', 1, type=int)
    per_page = 20
    
    # Filters
    engineer_id = request.args.get('engineer_id', 'all')
    topic = request.args.get('topic', 'all')
    status = request.args.get('status', 'all')  # active, completed, overdue
    
    # Build query
    query = Assignment.query.join(User)
    
    if engineer_id != 'all':
        query = query.filter(Assignment.engineer_id == engineer_id)
    if topic != 'all':
        query = query.filter(Assignment.topic == topic)
    
    # Status filtering
    if status == 'completed':
        query = query.join(Submission).filter(Submission.assignment_id == Assignment.id)
    elif status == 'overdue':
        query = query.filter(
            Assignment.due_date < datetime.date.today(),
            ~Assignment.submissions.any()
        )
    elif status == 'active':
        query = query.filter(Assignment.is_active == True)
    
    assignments = query.order_by(Assignment.created_date.desc()).paginate(
        page=page, per_page=per_page, error_out=False
    )
    
    # Get filter options
    engineers = User.query.filter_by(role=UserRole.ENGINEER).all()
    topics = list(TOPICS.keys())
    
    return render_template('admin/assignments.html',
                         assignments=assignments,
                         engineers=engineers,
                         topics=topics,
                         current_filters={
                             'engineer_id': engineer_id,
                             'topic': topic,
                             'status': status
                         })

# app/blueprints/engineer/__init__.py
from flask import Blueprint

engineer_bp = Blueprint('engineer', __name__)

from app.blueprints.engineer import dashboard, assignments, grades, notifications

# app/blueprints/engineer/assignments.py - Engineer Assignment Handling
from flask import render_template, request, redirect, url_for, flash, jsonify
from flask_login import login_required, current_user
from app.blueprints.engineer import engineer_bp
from app.models.assignment import Assignment, Submission
from app.services.evaluator_service import EvaluationService
from app.auth.decorators import engineer_required
from app import db, limiter

@engineer_bp.route('/assignment/<assignment_id>')
@login_required
@engineer_required
def view_assignment(assignment_id):
    """Engineer views their assignment"""
    assignment = Assignment.query.filter_by(
        id=assignment_id,
        engineer_id=current_user.id,
        is_active=True
    ).first_or_404()
    
    # Check if already submitted
    submission = Submission.query.filter_by(
        assignment_id=assignment_id,
        engineer_id=current_user.id
    ).first()
    
    # Check if overdue
    is_overdue = assignment.due_date < datetime.date.today() and not submission
    
    return render_template('engineer/assignment.html',
                         assignment=assignment,
                         submission=submission,
                         is_overdue=is_overdue)

@engineer_bp.route('/submit-assignment', methods=['POST'])
@login_required
@engineer_required
@limiter.limit("3 per hour")  # Prevent submission spam
def submit_assignment():
    """Engineer submits assignment"""
    data = request.get_json()
    assignment_id = data.get('assignment_id')
    answers = data.get('answers', [])
    
    # Verify ownership
    assignment = Assignment.query.filter_by(
        id=assignment_id,
        engineer_id=current_user.id,
        is_active=True
    ).first()
    
    if not assignment:
        return jsonify({'error': 'Assignment not found or access denied'}), 404
    
    # Check for existing submission
    existing = Submission.query.filter_by(
        assignment_id=assignment_id,
        engineer_id=current_user.id
    ).first()
    
    if existing:
        return jsonify({'error': 'Assignment already submitted'}), 409
    
    # Validate answers
    if len(answers) != len(assignment.questions):
        return jsonify({'error': 'All questions must be answered'}), 400
    
    # Check minimum answer length
    for i, answer in enumerate(answers):
        if not answer or len(answer.strip()) < 50:
            return jsonify({'error': f'Answer {i+1} is too short (minimum 50 characters)'}), 400
    
    try:
        # Create submission
        submission = Submission(
            assignment_id=assignment_id,
            engineer_id=current_user.id,
            answers=answers
        )
        
        db.session.add(submission)
        db.session.commit()
        
        # Trigger automatic evaluation
        try:
            evaluation_service = EvaluationService()
            evaluation_service.evaluate_submission(submission.id)
        except Exception as eval_error:
            # Log evaluation error but don't fail submission
            current_app.logger.error(f"Evaluation failed for submission {submission.id}: {str(eval_error)}")
        
        return jsonify({
            'success': True,
            'message': 'Assignment submitted successfully! Your submission is being evaluated and will be reviewed by the admin.',
            'submission_id': submission.id
        })
        
    except Exception as e:
        db.session.rollback()
        return jsonify({'error': 'Submission failed. Please try again.'}), 500

# app/services/init_service.py - Database Initialization
from app.models.user import User, UserRole
from app.models.assignment import Assignment, Submission
from app import db
import datetime

def init_demo_data():
    """Initialize demo data for testing"""
    
    # Create admin user
    admin = User.query.filter_by(username='admin').first()
    if not admin:
        admin = User(
            username='admin',
            email='admin@physicaldesign.com',
            role=UserRole.ADMIN
        )
        admin.set_password('admin123')
        db.session.add(admin)
    
    # Create demo engineers
    engineers_data = [
        {
            'username': 'engineer1',
            'email': 'eng1@company.com',
            'engineer_id': 'ENG_001',
            'department': 'Physical Design',
            'password': 'eng123'
        },
        {
            'username': 'engineer2', 
            'email': 'eng2@company.com',
            'engineer_id': 'ENG_002',
            'department': 'Implementation',
            'password': 'eng123'
        },
        {
            'username': 'engineer3',
            'email': 'eng3@company.com', 
            'engineer_id': 'ENG_003',
            'department': 'Verification',
            'password': 'eng123'
        }
    ]
    
    for eng_data in engineers_data:
        existing = User.query.filter_by(username=eng_data['username']).first()
        if not existing:
            engineer = User(
                username=eng_data['username'],
                email=eng_data['email'],
                engineer_id=eng_data['engineer_id'],
                department=eng_data['department'],
                role=UserRole.ENGINEER
            )
            engineer.set_password(eng_data['password'])
            db.session.add(engineer)
    
    db.session.commit()
    print("Demo data initialized successfully!")

# run.py - Updated Application Entry Point
import os
from app import create_app, db
from app.models.user import User
from app.models.assignment import Assignment, Submission
from app.services.init_service import init_demo_data

app = create_app(os.getenv('FLASK_ENV') or 'default')

@app.shell_context_processor
def make_shell_context():
    return {
        'db': db, 
        'User': User,
        'Assignment': Assignment, 
        'Submission': Submission
    }

@app.cli.command()
def init_db():
    """Initialize the database with tables and demo data"""
    db.create_all()
    init_demo_data()
    print('Database initialized with demo data!')

@app.cli.command()
def create_admin():
    """Create admin user"""
    username = input('Admin username: ')
    email = input('Admin email: ')
    password = input('Admin password: ')
    
    admin = User(
        username=username,
        email=email,
        role='admin'
    )
    admin.set_password(password)
    
    db.session.add(admin)
    db.session.commit()
    print(f'Admin user {username} created successfully!')

if __name__ == '__main__':
    with app.app_context():
        db.create_all()  # Ensure tables exist
    app.run(host='0.0.0.0', port=int(os.environ.get('PORT', 5000)), debug=True)

# app/blueprints/main/routes.py - Main Routes (Landing Page)
from flask import render_template, redirect, url_for
from flask_login import current_user
from app.blueprints.main import main_bp

@main_bp.route('/')
def index():
    """Landing page - redirect based on authentication status"""
    if current_user.is_authenticated:
        if current_user.is_admin():
            return redirect(url_for('admin.dashboard'))
        else:
            return redirect(url_for('engineer.dashboard'))
    
    return redirect(url_for('auth.login'))

@main_bp.route('/health')
def health_check():
    """System health check"""
    return {
        'status': 'healthy',
        'timestamp': datetime.datetime.utcnow().isoformat(),
        'system': 'Physical Design Assignment System',
        'version': '2.0.0'
    }

# app/blueprints/main/__init__.py
from flask import Blueprint

main_bp = Blueprint('main', __name__)

from app.blueprints.main import routes

# requirements.txt - Updated Dependencies
"""
Flask==2.3.3
Flask-SQLAlchemy==3.0.5
Flask-Login==0.6.3
Flask-WTF==1.2.1
Flask-Talisman==1.1.0
Flask-Limiter==3.5.0
Werkzeug==2.3.7
WTForms==3.1.0
python-dotenv==1.0.0
gunicorn==21.2.0
marshmallow==3.20.1
"""

# .env.example - Environment Variables Template
"""
# Flask Configuration
FLASK_ENV=development
SECRET_KEY=your-super-secret-key-here

# Database
DATABASE_URL=sqlite:///app.db

# Redis (for rate limiting and caching)
REDIS_URL=redis://localhost:6379/0

# Email (for notifications - optional)
MAIL_SERVER=smtp.gmail.com
MAIL_PORT=587
MAIL_USE_TLS=true
MAIL_USERNAME=your-email@gmail.com
MAIL_PASSWORD=your-app-password

# Security
WTF_CSRF_TIME_LIMIT=3600
"""

# Dockerfile - Production Deployment
"""
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    gcc \
    && rm -rf /var/lib/apt/lists/*

# Copy requirements and install Python dependencies
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy application code
COPY . .

# Create non-root user
RUN useradd -m -u 1000 appuser && chown -R appuser:appuser /app
USER appuser

# Create necessary directories
RUN mkdir -p logs instance

# Expose port
EXPOSE 8000

# Health check
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8000/health || exit 1

# Run application
CMD ["gunicorn", "--bind", "0.0.0.0:8000", "--workers", "4", "--timeout", "120", "run:app"]
"""

# docker-compose.yml - Development Setup
"""
version: '3.8'

services:
  web:
    build: .
    ports:
      - "5000:8000"
    environment:
      - FLASK_ENV=development
      - DATABASE_URL=postgresql://user:password@db:5432/physicaldesign
      - REDIS_URL=redis://redis:6379/0
    depends_on:
      - db
      - redis
    volumes:
      - ./logs:/app/logs

  db:
    image: postgres:15
    environment:
      - POSTGRES_DB=physicaldesign
      - POSTGRES_USER=user
      - POSTGRES_PASSWORD=password
    volumes:
      - postgres_data:/var/lib/postgresql/data
    ports:
      - "5432:5432"

  redis:
    image: redis:7-alpine
    ports:
      - "6379:6379"

volumes:
  postgres_data:
"""

# app/templates/admin/create_assignment.html - Assignment Creation Form
"""
<!DOCTYPE html>
<html>
<head>
    <title>Create Assignment - Admin</title>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <style>
        body {
            font-family: Arial, sans-serif;
            margin: 0;
            background: #f5f5f5;
        }
        .header {
            background: #2c3e50;
            color: white;
            padding: 15px 20px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        .container {
            max-width: 800px;
            margin: 20px auto;
            padding: 0 20px;
        }
        .form-container {
            background: white;
            padding: 40px;
            border-radius: 8px;
            box-shadow: 0 2px 10px rgba(0,0,0,0.1);
        }
        .form-group {
            margin-bottom: 25px;
        }
        .form-group label {
            display: block;
            margin-bottom: 8px;
            font-weight: bold;
            color: #2c3e50;
        }
        .form-group input,
        .form-group select,
        .form-group textarea {
            width: 100%;
            padding: 12px;
            border: 2px solid #ddd;
            border-radius: 5px;
            font-size: 16px;
            transition: border-color 0.3s;
        }
        .form-group input:focus,
        .form-group select:focus,
        .form-group textarea:focus {
            border-color: #3498db;
            outline: none;
        }
        .form-group small {
            color: #666;
            font-size: 14px;
            margin-top: 5px;
            display: block;
        }
        .btn {
            padding: 12px 25px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-size: 16px;
            transition: all 0.3s;
            text-decoration: none;
            display: inline-block;
        }
        .btn-primary {
            background: #3498db;
            color: white;
        }
        .btn-primary:hover {
            background: #2980b9;
        }
        .btn-secondary {
            background: #95a5a6;
            color: white;
            margin-right: 10px;
        }
        .btn-secondary:hover {
            background: #7f8c8d;
        }
        .topic-preview {
            background: #f8f9fa;
            padding: 20px;
            border-radius: 5px;
            margin-top: 15px;
            border-left: 4px solid #3498db;
        }
        .question-count {
            font-weight: bold;
            color: #2c3e50;
        }
        .alert {
            padding: 15px;
            margin-bottom: 20px;
            border-radius: 5px;
        }
        .alert-error {
            background: #f8d7da;
            color: #721c24;
            border: 1px solid #f5c6cb;
        }
        .alert-success {
            background: #d4edda;
            color: #155724;
            border: 1px solid #c3e6cb;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>➕ Create New Assignment</h1>
        <div>
            <a href="{{ url_for('admin.dashboard') }}" style="color: white; text-decoration: none;">← Back to Dashboard</a>
        </div>
    </div>
    
    <div class="container">
        <div class="form-container">
            <h2>📝 Assignment Details</h2>
            
            {% with messages = get_flashed_messages(with_categories=true) %}
                {% if messages %}
                    {% for category, message in messages %}
                        <div class="alert alert-{{ 'error' if category == 'error' else 'success' }}">
                            {{ message }}
                        </div>
                    {% endfor %}
                {% endif %}
            {% endwith %}
            
            <form method="POST">
                {{ csrf_token() }}
                
                <div class="form-group">
                    <label for="engineer_id">👨‍💻 Select Engineer:</label>
                    <select id="engineer_id" name="engineer_id" required>
                        <option value="">Choose an engineer...</option>
                        {% for engineer in engineers %}
                            <option value="{{ engineer.id }}">
                                {{ engineer.username }} ({{ engineer.engineer_id }}) - {{ engineer.department }}
                            </option>
                        {% endfor %}
                    </select>
                    <small>Select the engineer who will receive this assignment</small>
                </div>
                
                <div class="form-group">
                    <label for="topic">🎯 Topic:</label>
                    <select id="topic" name="topic" required onchange="updateTopicPreview()">
                        <option value="">Choose a topic...</option>
                        {% for topic in topics %}
                            <option value="{{ topic }}">{{ topic.title() }}</option>
                        {% endfor %}
                    </select>
                    <div id="topicPreview" class="topic-preview" style="display: none;">
                        <div class="question-count" id="questionCount"></div>
                        <p>This topic includes comprehensive questions covering technical terminology, methodology, and practical applications.</p>
                    </div>
                </div>
                
                <div class="form-group">
                    <label for="custom_title">📋 Custom Title (Optional):</label>
                    <input type="text" id="custom_title" name="custom_title" 
                           placeholder="Leave blank for auto-generated title">
                    <small>If provided, this will override the default title</small>
                </div>
                
                <div class="form-group">
                    <label for="due_date">📅 Due Date:</label>
                    <input type="date" id="due_date" name="due_date" required>
                    <small>Assignment must be completed by this date</small>
                </div>
                
                <div class="form-group">
                    <label for="points">🏆 Points:</label>
                    <input type="number" id="points" name="points" value="120" min="50" max="200">
                    <small>Total points available for this assignment (50-200)</small>
                </div>
                
                <div style="margin-top: 30px;">
                    <a href="{{ url_for('admin.view_assignments') }}" class="btn btn-secondary">Cancel</a>
                    <button type="submit" class="btn btn-primary">🚀 Create Assignment</button>
                </div>
            </form>
        </div>
    </div>
    
    <script>
        // Set minimum date to tomorrow
        const tomorrow = new Date();
        tomorrow.setDate(tomorrow.getDate() + 1);
        document.getElementById('due_date').min = tomorrow.toISOString().split('T')[0];
        
        // Topic question counts
        const topicQuestions = {
            'floorplanning': 15,
            'placement': 15,
            'routing': 15
        };
        
        function updateTopicPreview() {
            const topic = document.getElementById('topic').value;
            const preview = document.getElementById('topicPreview');
            const questionCount = document.getElementById('questionCount');
            
            if (topic && topicQuestions[topic]) {
                questionCount.textContent = `${topicQuestions[topic]} technical questions included`;
                preview.style.display = 'block';
            } else {
                preview.style.display = 'none';
            }
        }
    </script>
</body>
</html>
"""

# app/cli.py - Command Line Interface
from flask.cli import with_appcontext
import click
from app import db
from app.models.user import User, UserRole
from app.services.init_service import init_demo_data

@click.command()
@with_appcontext
def init_db():
    """Initialize database with tables and demo data."""
    db.create_all()
    init_demo_data()
    click.echo('Database initialized successfully!')

@click.command()
@click.option('--username', prompt='Username', help='Admin username')
@click.option('--email', prompt='Email', help='Admin email')
@click.option('--password', prompt='Password', hide_input=True, help='Admin password')
@with_appcontext
def create_admin(username, email, password):
    """Create admin user."""
    existing = User.query.filter_by(username=username).first()
    if existing:
        click.echo(f'User {username} already exists!')
        return
    
    admin = User(
        username=username,
        email=email,
        role=UserRole.ADMIN
    )
    admin.set_password(password)
    
    db.session.add(admin)
    db.session.commit()
    
    click.echo(f'Admin user {username} created successfully!')

def register_commands(app):
    """Register CLI commands with the Flask app."""
    app.cli.add_command(init_db)
    app.cli.add_command(create_admin)
