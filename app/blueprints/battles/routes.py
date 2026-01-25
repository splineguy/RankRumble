"""
Battle arena and history routes.
"""
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user

from app.blueprints.battles import battles_bp


def get_project_manager():
    """Get the project manager from app context."""
    return current_app.project_manager


@battles_bp.route('/projects/<project_id>/battle')
@login_required
def arena(project_id):
    """Battle arena page."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects.list_projects'))

    if len(project['items']) < 2:
        flash('You need at least 2 items to start battles', 'warning')
        return redirect(url_for('projects.detail', project_id=project_id))

    return render_template('battles/arena.html', project=project)


@battles_bp.route('/projects/<project_id>/battle/history')
@login_required
def history(project_id):
    """View battle history."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects.list_projects'))

    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page

    all_history = project_manager.get_battle_history(
        current_user.id, project_id, limit=10000
    )
    total_battles = len(all_history)
    total_pages = (total_battles + per_page - 1) // per_page

    battles = all_history[offset:offset + per_page]

    return render_template('battles/history.html',
                           project=project,
                           battles=battles,
                           page=page,
                           total_pages=total_pages,
                           total_battles=total_battles)
