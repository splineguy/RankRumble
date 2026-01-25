from flask import Blueprint

battles_bp = Blueprint('battles', __name__)

from app.blueprints.battles import routes
