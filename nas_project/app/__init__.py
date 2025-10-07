from flask import Flask, redirect, url_for
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from datetime import datetime
from werkzeug.middleware.proxy_fix import ProxyFix
from flask_mail import Mail



# Initialize extensions globally
db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()  # <-- THIS was missing earlier

def create_app():
    app = Flask(__name__)

    # Load config first
    from app.config import Config
    app.config.from_object(Config)

    # Init core extensions
    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    # Init email utils (uses mail)
    from app.utils.email_utils import init_mail
    init_mail(app)

    # Secure cookies
    app.config.update(
        SESSION_COOKIE_SECURE=True,
        SESSION_COOKIE_HTTPONLY=True,
        SESSION_COOKIE_SAMESITE='Strict'
    )

    # Proxy fix for proper header forwarding
    app.wsgi_app = ProxyFix(app.wsgi_app, x_for=1, x_proto=1, x_host=1, x_prefix=1)

    # Login manager config
    login_manager.login_view = 'auth.login'
    login_manager.login_message_category = 'info'

    from app.models import User

    @login_manager.user_loader
    def load_user(user_id):
        return User.query.get(int(user_id))

    with app.app_context():
        # Avoid circular imports
        from app.models import check_and_update_tables, initialize_system_tags

        db.create_all()
        check_and_update_tables()
        initialize_system_tags()

        # Register blueprints
        from app.routes.auth import auth_bp
        from app.routes.admin import admin_bp
        from app.routes.files import files_bp
        from app.routes.groups import groups_bp
        from app.routes.ai_dashboard import ai_bp

        app.register_blueprint(auth_bp, name='auth')
        app.register_blueprint(admin_bp, name='admin')
        app.register_blueprint(files_bp, name='files')
        app.register_blueprint(groups_bp, name='groups')

        @app.route('/')
        def index():
            return redirect(url_for('files.dashboard'))

        @app.after_request
        def add_security_headers(response):
            response.headers['X-Content-Type-Options'] = 'nosniff'
            response.headers['X-Frame-Options'] = 'DENY'
            response.headers['Content-Security-Policy'] = (
                "default-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com; "
                "script-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com 'unsafe-inline' https://www.google.com; "
                "style-src 'self' https://cdn.jsdelivr.net https://cdnjs.cloudflare.com 'unsafe-inline'; "
                "img-src 'self' data:; "
                "font-src 'self' https://cdnjs.cloudflare.com; "
                "connect-src 'self';"

            )
            return response

    @app.context_processor
    def utility_processor():
        return {'current_year': datetime.utcnow().year}

    @app.context_processor
    def add_utility_functions():
        from app.config import Config
        return {'format_size': Config.format_size}

    app.register_blueprint(ai_bp)

    return app



    
