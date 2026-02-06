"""
Flask application factory.
"""
import os
from flask import Flask, redirect, url_for
from flask_login import LoginManager
from flask_wtf.csrf import CSRFProtect

from app.config import config

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to access this page.'
login_manager.login_message_category = 'info'

csrf = CSRFProtect()


def create_app(config_name=None):
    """Create and configure the Flask application."""
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'development')

    app = Flask(__name__)
    app.config.from_object(config[config_name])

    # Ensure data directories exist
    os.makedirs(app.config['DATA_DIR'], exist_ok=True)
    os.makedirs(app.config['PROJECTS_DIR'], exist_ok=True)

    # Initialize extensions
    login_manager.init_app(app)
    csrf.init_app(app)

    # Initialize managers
    from app.models.user import UserManager
    from app.models.project import ProjectManager
    from app.models.tournament import TournamentManager

    app.user_manager = UserManager(app.config['USERS_FILE'])
    app.project_manager = ProjectManager(app.config['PROJECTS_DIR'])
    app.tournament_manager = TournamentManager(app.project_manager)

    # User loader for Flask-Login
    @login_manager.user_loader
    def load_user(user_id):
        return app.user_manager.get_user_by_id(user_id)

    # Register blueprints
    from app.blueprints.auth import auth_bp
    from app.blueprints.projects import projects_bp
    from app.blueprints.battles import battles_bp
    from app.blueprints.api import api_bp
    from app.blueprints.tournament import tournament_bp

    app.register_blueprint(auth_bp)
    app.register_blueprint(projects_bp)
    app.register_blueprint(battles_bp)
    app.register_blueprint(api_bp)
    app.register_blueprint(tournament_bp)

    # Root route
    @app.route('/')
    def index():
        return redirect(url_for('auth.login'))

    # Error handlers
    @app.errorhandler(404)
    def not_found_error(error):
        return redirect(url_for('projects.list_projects'))

    @app.errorhandler(500)
    def internal_error(error):
        return 'Internal Server Error', 500

    return app
