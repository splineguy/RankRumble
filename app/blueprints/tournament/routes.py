"""
Tournament page routes.
"""
import random
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_required, current_user

from app.blueprints.tournament import tournament_bp


def get_project_manager():
    return current_app.project_manager


def get_tournament_manager():
    return current_app.tournament_manager


@tournament_bp.route('/projects/<project_id>/tournament/new')
@login_required
def setup(project_id):
    """Tournament setup page - select 16 items."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('projects.list_projects'))

    items = sorted(
        project['items'].values(),
        key=lambda x: x['rating'],
        reverse=True
    )

    return render_template('tournament/setup.html',
                           project=project, items=items)


@tournament_bp.route('/projects/<project_id>/tournament/create', methods=['POST'])
@login_required
def create(project_id):
    """Create a tournament from selected items."""
    project_manager = get_project_manager()
    tournament_manager = get_tournament_manager()

    project = project_manager.get_project(current_user.id, project_id)
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('projects.list_projects'))

    item_ids = request.form.getlist('item_ids')
    name = request.form.get('name', '').strip()

    if len(item_ids) != 16:
        flash('You must select exactly 16 items.', 'error')
        return redirect(url_for('tournament.setup', project_id=project_id))

    tournament = tournament_manager.create_tournament(
        current_user.id, project_id, item_ids, name=name or None
    )

    if not tournament:
        flash('Failed to create tournament.', 'error')
        return redirect(url_for('tournament.setup', project_id=project_id))

    flash('Tournament created! Let the battles begin!', 'success')
    return redirect(url_for('tournament.bracket', project_id=project_id,
                            tournament_id=tournament['id']))


@tournament_bp.route('/projects/<project_id>/tournament/<tournament_id>')
@login_required
def bracket(project_id, tournament_id):
    """Bracket view."""
    project_manager = get_project_manager()
    tournament_manager = get_tournament_manager()

    project = project_manager.get_project(current_user.id, project_id)
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('projects.list_projects'))

    tournament = tournament_manager.get_tournament(current_user.id, project_id, tournament_id)
    if not tournament:
        flash('Tournament not found.', 'error')
        return redirect(url_for('projects.detail', project_id=project_id))

    display = tournament_manager.get_bracket_display(tournament, project)
    next_match = tournament_manager.get_next_match(tournament, project)

    return render_template('tournament/bracket.html',
                           project=project, tournament=tournament,
                           display=display, next_match=next_match)


@tournament_bp.route('/projects/<project_id>/tournament/<tournament_id>/play')
@login_required
def play(project_id, tournament_id):
    """Play the next match."""
    project_manager = get_project_manager()
    tournament_manager = get_tournament_manager()

    project = project_manager.get_project(current_user.id, project_id)
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('projects.list_projects'))

    tournament = tournament_manager.get_tournament(current_user.id, project_id, tournament_id)
    if not tournament:
        flash('Tournament not found.', 'error')
        return redirect(url_for('projects.detail', project_id=project_id))

    if tournament['status'] == 'completed':
        return redirect(url_for('tournament.results', project_id=project_id,
                                tournament_id=tournament_id))

    next_match = tournament_manager.get_next_match(tournament, project)
    if not next_match:
        return redirect(url_for('tournament.results', project_id=project_id,
                                tournament_id=tournament_id))

    return render_template('tournament/play.html',
                           project=project, tournament=tournament,
                           match_info=next_match)


@tournament_bp.route('/projects/<project_id>/tournament/<tournament_id>/results')
@login_required
def results(project_id, tournament_id):
    """Tournament results page."""
    project_manager = get_project_manager()
    tournament_manager = get_tournament_manager()

    project = project_manager.get_project(current_user.id, project_id)
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('projects.list_projects'))

    tournament = tournament_manager.get_tournament(current_user.id, project_id, tournament_id)
    if not tournament:
        flash('Tournament not found.', 'error')
        return redirect(url_for('projects.detail', project_id=project_id))

    display = tournament_manager.get_bracket_display(tournament, project)

    champion_name = ''
    runner_up_name = ''
    if tournament.get('results'):
        champ_id = tournament['results'].get('1st')
        runner_id = tournament['results'].get('2nd')
        if champ_id and champ_id in project['items']:
            champion_name = project['items'][champ_id]['name']
        if runner_id and runner_id in project['items']:
            runner_up_name = project['items'][runner_id]['name']

    return render_template('tournament/results.html',
                           project=project, tournament=tournament,
                           display=display, champion_name=champion_name,
                           runner_up_name=runner_up_name)


@tournament_bp.route('/projects/<project_id>/tournaments')
@login_required
def list_tournaments(project_id):
    """List all tournaments for a project."""
    project_manager = get_project_manager()
    tournament_manager = get_tournament_manager()

    project = project_manager.get_project(current_user.id, project_id)
    if not project:
        flash('Project not found.', 'error')
        return redirect(url_for('projects.list_projects'))

    tournaments = tournament_manager.list_tournaments(current_user.id, project_id)

    return render_template('tournament/list.html',
                           project=project, tournaments=tournaments)
