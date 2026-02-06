from flask import Blueprint

tournament_bp = Blueprint('tournament', __name__)

from app.blueprints.tournament import routes
