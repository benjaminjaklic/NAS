from flask import current_app, render_template, url_for
from flask_mail import Message, Mail
from itsdangerous import URLSafeTimedSerializer
from datetime import datetime
import logging

# Initialize Mail
mail = Mail()

def init_mail(app):
    """Initialize Mail with the Flask app
    This uses config values already defined in config.py"""
    mail.init_app(app)
    logging.info(f"Mail configuration initialized with server {app.config['MAIL_SERVER']}")

def generate_verification_token(email):
    """Generate a token for email verification"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    return serializer.dumps(email, salt=current_app.config['SECURITY_PASSWORD_SALT'])

def confirm_verification_token(token, expiration=3600):
    """Confirm a verification token"""
    serializer = URLSafeTimedSerializer(current_app.config['SECRET_KEY'])
    try:
        email = serializer.loads(
            token,
            salt=current_app.config['SECURITY_PASSWORD_SALT'],
            max_age=expiration
        )
        return email
    except Exception as e:
        logging.error(f"Token verification error: {str(e)}")
        return None

def send_email(to, subject, template, **kwargs):
    """Send an email"""
    try:
        msg = Message(subject, recipients=[to])
        msg.html = render_template(template, **kwargs)
        print(f"\n--- EMAIL TO {to} ---\nSubject: {subject}\nHTML:\n{msg.html}\n")
        mail.send(msg)
        logging.info(f"Email sent successfully to {to}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")
        return False
def send_email(to, subject, template, **kwargs):
    """Send an email"""
    try:
        msg = Message(subject, recipients=[to])
        msg.html = render_template(template, **kwargs)
        print(f"\n--- EMAIL TO {to} ---\nSubject: {subject}\nHTML:\n{msg.html}\n")
        mail.send(msg)
        logging.info(f"Email sent successfully to {to}")
        return True
    except Exception as e:
        logging.error(f"Failed to send email: {str(e)}")
        return False


def send_verification_email(user):
    """Send a verification email to the user
    
    Args:
        user: User object (not just email) to store token in database
    """
    # Generate token and store it in the user record
    token = generate_verification_token(user.email)
    user.confirmation_token = token
    user.token_created_at = datetime.utcnow()
    
    from app import db
    db.session.commit()
    
    verify_url = url_for('auth.verify_email', token=token, _external=True)
    
    return send_email(
        to=user.email,
        subject='NAS System - Please verify your email',
        template='auth/email/verify_email.html',
        user_email=user.email,
        verify_url=verify_url
    )

def send_password_reset_email(user):
    """Send a password reset email to the user"""
    print(f"[DEBUG] Sending password reset email to: {user.email}")

    token = generate_verification_token(user.email)
    print(f"[DEBUG] Token generated: {token}")

    user.confirmation_token = token
    user.token_created_at = datetime.utcnow()

    from app import db
    db.session.commit()

    reset_url = url_for('auth.reset_password', token=token, _external=True)
    print(f"[DEBUG] Reset URL: {reset_url}")

    return send_email(
        to=user.email,
        subject='NAS System - Password Reset Request',
        template='auth/email/reset_password.html',
        reset_url=reset_url
    )
