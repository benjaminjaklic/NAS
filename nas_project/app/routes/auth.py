from flask import Blueprint, render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.urls import url_parse  # Changed from werkzeug.utils to werkzeug.urls
from app.models import db, User, ActivityLog
from datetime import datetime
import os

auth_bp = Blueprint('auth', __name__)

@auth_bp.route('/')
def index():
    if current_user.is_authenticated:
        return redirect(url_for('files.dashboard'))
    return redirect(url_for('auth.login'))

@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(url_for('files.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        password = request.form.get('password')
        remember = True if request.form.get('remember') else False
        
        user = User.query.filter_by(username=username).first()
        
        if not user or not user.check_password(password):
            flash('Invalid username or password', 'danger')
            return redirect(url_for('auth.login'))
        
        if not user.is_approved and not user.is_admin:
            flash('Your account is pending approval', 'warning')
            return redirect(url_for('auth.login'))
        
        login_user(user, remember=remember)
        
        # Log activity
        log = ActivityLog(
            user_id=user.id,
            action='login',
            ip_address=request.remote_addr,
            details='Successful login',
            timestamp=datetime.utcnow()
        )
        db.session.add(log)
        
        # Update last login
        user.last_login = datetime.utcnow()
        db.session.commit()
        
        next_page = request.args.get('next')
        if not next_page or url_parse(next_page).netloc != '':
            next_page = url_for('files.dashboard')
        return redirect(next_page)
    
    return render_template('auth/login.html')

@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('files.dashboard'))
    
    if request.method == 'POST':
        username = request.form.get('username')
        email = request.form.get('email')
        password = request.form.get('password')
        confirm_password = request.form.get('confirm_password')
        
        # Validate input
        if not email or not username or not password:
            flash('All fields are required', 'danger')
            return redirect(url_for('auth.register'))
            
        if password != confirm_password:
            flash('Passwords do not match', 'danger')
            return redirect(url_for('auth.register'))
        
        # Check if user exists
        if User.query.filter_by(username=username).first():
            flash('Username already exists', 'danger')
            return redirect(url_for('auth.register'))
        
        if User.query.filter_by(email=email).first():
            flash('Email already registered', 'danger')
            return redirect(url_for('auth.register'))
        
        # Create new user
        new_user = User(
            username=username,
            email=email,
            is_approved=False,  # Requires admin approval
            storage_limit=current_app.config['DEFAULT_STORAGE_LIMIT'],
            storage_used=0,
            created_at=datetime.utcnow()
        )
        new_user.set_password(password)
        
        try:
            db.session.add(new_user)
            db.session.commit()
            
            # Create user storage directory
            user_dir = os.path.join(current_app.config['UPLOAD_FOLDER'], str(new_user.id))
            os.makedirs(user_dir, exist_ok=True)
            
            # Log activity
            log = ActivityLog(
                user_id=new_user.id,
                action='register',
                ip_address=request.remote_addr,
                details='New user registration',
                timestamp=datetime.utcnow()
            )
            db.session.add(log)
            db.session.commit()
            
            flash('Registration successful! Please wait for admin approval.', 'success')
            return redirect(url_for('auth.login'))
        except Exception as e:
            db.session.rollback()
            flash(f'An error occurred during registration: {str(e)}', 'danger')
            
    return render_template('auth/register.html')

@auth_bp.route('/logout')
@login_required
def logout():
    # Log activity before logging out
    log = ActivityLog(
        user_id=current_user.id,
        action='logout',
        ip_address=request.remote_addr,
        details='User logged out',
        timestamp=datetime.utcnow()
    )
    db.session.add(log)
    db.session.commit()
    
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))

@auth_bp.route('/profile', methods=['GET', 'POST'])
@login_required
def profile():
    if request.method == 'POST':
        if 'current_password' in request.form and request.form.get('new_password'):
            current_password = request.form.get('current_password')
            new_password = request.form.get('new_password')
            confirm_password = request.form.get('confirm_password')
            
            if not current_user.check_password(current_password):
                flash('Current password is incorrect', 'danger')
            elif new_password != confirm_password:
                flash('New passwords do not match', 'danger')
            else:
                current_user.set_password(new_password)
                
                # Log password change
                log = ActivityLog(
                    user_id=current_user.id,
                    action='password_change',
                    ip_address=request.remote_addr,
                    details='User changed password',
                    timestamp=datetime.utcnow()
                )
                db.session.add(log)
                db.session.commit()
                flash('Password updated successfully', 'success')
        
        # Update username if it was changed
        if 'username' in request.form and request.form.get('username') != current_user.username:
            new_username = request.form.get('username')
            if User.query.filter(User.username == new_username, User.id != current_user.id).first():
                flash('Username already taken', 'danger')
            else:
                old_username = current_user.username
                current_user.username = new_username
                
                # Log username change
                log = ActivityLog(
                    user_id=current_user.id,
                    action='username_change',
                    ip_address=request.remote_addr,
                    details=f'Username changed from {old_username} to {new_username}',
                    timestamp=datetime.utcnow()
                )
                db.session.add(log)
                db.session.commit()
                flash('Username updated successfully', 'success')
    
    return render_template('auth/profile.html', user=current_user)

@auth_bp.route('/register_post', methods=['POST'])
def register_post():
    """Handler for register form submission"""
    return register()




@auth_bp.route('/forgot_password', methods=['GET', 'POST'])
def forgot_password():
    if request.method == 'POST':
        email = request.form.get('email')
        user = User.query.filter_by(email=email).first()

        if user:
            from app.utils.email_utils import send_password_reset_email
            send_password_reset_email(user)
            flash('If the email exists, a reset link was sent.', 'info')
        else:
            flash('If the email exists, a reset link was sent.', 'info')

        return redirect(url_for('auth.login'))

    return render_template('auth/forgot_password.html')



@auth_bp.route('/reset_password/<token>', methods=['GET', 'POST'])
def reset_password(token):
    from app.utils.email_utils import confirm_verification_token
    email = confirm_verification_token(token)

    if not email:
        flash('Reset link is invalid or has expired.', 'danger')
        return redirect(url_for('auth.login'))

    user = User.query.filter_by(email=email).first()
    if not user:
        flash('Invalid user.', 'danger')
        return redirect(url_for('auth.login'))

    if request.method == 'POST':
        password = request.form.get('password')
        confirm = request.form.get('confirm_password')
        if password != confirm:
            flash('Passwords do not match.', 'danger')
        else:
            user.set_password(password)
            from app import db
            db.session.commit()
            flash('Password has been reset.', 'success')
            return redirect(url_for('auth.login'))

    return render_template('auth/reset_password.html', token=token)
