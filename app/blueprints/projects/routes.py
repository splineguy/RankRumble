"""
Project management routes.
"""
import csv
import json
from io import StringIO

from flask import render_template, redirect, url_for, flash, request, current_app, Response
from flask_login import login_required, current_user

from app.blueprints.projects import projects_bp
from app.blueprints.projects.forms import ProjectForm, ItemForm, ImportForm


def get_project_manager():
    """Get the project manager from app context."""
    return current_app.project_manager


@projects_bp.route('/')
@login_required
def list_projects():
    """List all projects for current user."""
    project_manager = get_project_manager()
    projects = project_manager.list_projects(current_user.id)
    return render_template('projects/list.html', projects=projects)


@projects_bp.route('/create', methods=['GET', 'POST'])
@login_required
def create_project():
    """Create a new project."""
    form = ProjectForm()
    if form.validate_on_submit():
        project_manager = get_project_manager()
        settings = {
            'k_factor': form.k_factor.data,
            'default_rating': form.default_rating.data,
            'allow_ties': form.allow_ties.data,
            'item_type': form.item_type.data or 'item'
        }
        project = project_manager.create_project(
            user_id=current_user.id,
            name=form.name.data,
            description=form.description.data,
            settings=settings
        )
        flash(f'Project "{project["name"]}" created!', 'success')
        return redirect(url_for('projects.detail', project_id=project['id']))

    return render_template('projects/create.html', form=form)


@projects_bp.route('/<project_id>')
@login_required
def detail(project_id):
    """View project details."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects.list_projects'))

    rankings = project_manager.get_rankings(current_user.id, project_id, limit=20)
    return render_template('projects/detail.html', project=project, rankings=rankings)


@projects_bp.route('/<project_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_project(project_id):
    """Edit project settings."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects.list_projects'))

    form = ProjectForm()
    if form.validate_on_submit():
        settings = {
            'k_factor': form.k_factor.data,
            'default_rating': form.default_rating.data,
            'allow_ties': form.allow_ties.data,
            'item_type': form.item_type.data or 'item'
        }
        project_manager.update_project(
            user_id=current_user.id,
            project_id=project_id,
            name=form.name.data,
            description=form.description.data,
            settings=settings
        )
        flash('Project updated!', 'success')
        return redirect(url_for('projects.detail', project_id=project_id))

    # Pre-populate form
    if request.method == 'GET':
        form.name.data = project['name']
        form.description.data = project['description']
        form.k_factor.data = project['settings']['k_factor']
        form.default_rating.data = project['settings']['default_rating']
        form.allow_ties.data = project['settings']['allow_ties']
        form.item_type.data = project['settings'].get('item_type', 'item')

    return render_template('projects/edit.html', form=form, project=project)


@projects_bp.route('/<project_id>/delete', methods=['POST'])
@login_required
def delete_project(project_id):
    """Delete a project."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects.list_projects'))

    project_manager.delete_project(current_user.id, project_id)
    flash(f'Project "{project["name"]}" deleted.', 'success')
    return redirect(url_for('projects.list_projects'))


# Item routes
@projects_bp.route('/<project_id>/items/add', methods=['GET', 'POST'])
@login_required
def add_item(project_id):
    """Add an item to a project."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects.list_projects'))

    form = ItemForm()
    if form.validate_on_submit():
        metadata = {}
        if form.notes.data:
            metadata['notes'] = form.notes.data

        project_manager.add_item(
            user_id=current_user.id,
            project_id=project_id,
            name=form.name.data,
            metadata=metadata if metadata else None
        )
        flash(f'Item "{form.name.data}" added!', 'success')
        return redirect(url_for('projects.detail', project_id=project_id))

    return render_template('projects/add_item.html', form=form, project=project)


@projects_bp.route('/<project_id>/items/<item_id>/edit', methods=['GET', 'POST'])
@login_required
def edit_item(project_id, item_id):
    """Edit an item."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project or item_id not in project['items']:
        flash('Item not found', 'error')
        return redirect(url_for('projects.detail', project_id=project_id))

    item = project['items'][item_id]
    form = ItemForm()

    if form.validate_on_submit():
        metadata = item.get('metadata', {})
        if form.notes.data:
            metadata['notes'] = form.notes.data
        elif 'notes' in metadata:
            del metadata['notes']

        project_manager.update_item(
            user_id=current_user.id,
            project_id=project_id,
            item_id=item_id,
            name=form.name.data,
            metadata=metadata if metadata else None
        )
        flash('Item updated!', 'success')
        return redirect(url_for('projects.detail', project_id=project_id))

    # Pre-populate
    if request.method == 'GET':
        form.name.data = item['name']
        form.notes.data = item.get('metadata', {}).get('notes', '')

    return render_template('projects/edit_item.html', form=form, project=project, item=item)


@projects_bp.route('/<project_id>/items/<item_id>/delete', methods=['POST'])
@login_required
def delete_item(project_id, item_id):
    """Delete an item."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project or item_id not in project['items']:
        flash('Item not found', 'error')
        return redirect(url_for('projects.detail', project_id=project_id))

    item_name = project['items'][item_id]['name']
    project_manager.delete_item(current_user.id, project_id, item_id)
    flash(f'Item "{item_name}" deleted.', 'success')
    return redirect(url_for('projects.detail', project_id=project_id))


@projects_bp.route('/<project_id>/items/<item_id>')
@login_required
def item_detail(project_id, item_id):
    """View item details and stats."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project or item_id not in project['items']:
        flash('Item not found', 'error')
        return redirect(url_for('projects.detail', project_id=project_id))

    item = project['items'][item_id]

    # Get battles involving this item
    item_battles = [
        b for b in project.get('battle_history', [])
        if b['item_a_id'] == item_id or b['item_b_id'] == item_id
    ]
    item_battles = list(reversed(item_battles))[:20]  # Most recent 20

    return render_template('projects/item_detail.html',
                           project=project, item=item, battles=item_battles)


# Import/Export routes
@projects_bp.route('/<project_id>/import', methods=['GET', 'POST'])
@login_required
def import_items(project_id):
    """Import items to a project."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects.list_projects'))

    form = ImportForm()
    if form.validate_on_submit():
        content = None
        format_type = form.import_format.data

        # Get content from file or text area
        if form.file.data:
            content = form.file.data.read().decode('utf-8')
            filename = form.file.data.filename.lower()
            if format_type == 'auto':
                if filename.endswith('.csv'):
                    format_type = 'csv'
                elif filename.endswith('.json'):
                    format_type = 'json'
                else:
                    format_type = 'txt'
        elif form.text_content.data:
            content = form.text_content.data
            if format_type == 'auto':
                # Try to detect format
                content_stripped = content.strip()
                if content_stripped.startswith('{'):
                    format_type = 'json'
                elif ',' in content_stripped.split('\n')[0]:
                    format_type = 'csv'
                else:
                    format_type = 'txt'

        if not content:
            flash('Please provide a file or paste content', 'error')
            return render_template('projects/import.html', form=form, project=project)

        # Import based on format
        if format_type == 'csv':
            added = project_manager.import_items_from_csv(
                current_user.id, project_id, content
            )
        elif format_type == 'json':
            added = project_manager.import_from_legacy_json(
                current_user.id, project_id, content
            )
        else:  # txt
            added = project_manager.import_items_from_txt(
                current_user.id, project_id, content
            )

        if added > 0:
            flash(f'Successfully imported {added} items!', 'success')
        else:
            flash('No new items were imported (may be duplicates)', 'warning')

        return redirect(url_for('projects.detail', project_id=project_id))

    return render_template('projects/import.html', form=form, project=project)


@projects_bp.route('/<project_id>/export')
@login_required
def export_items(project_id):
    """Export project rankings."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects.list_projects'))

    format_type = request.args.get('format', 'csv')
    rankings = project_manager.get_rankings(current_user.id, project_id)

    if format_type == 'json':
        # Full project export
        output = json.dumps(project, indent=2)
        mimetype = 'application/json'
        filename = f"{project['name']}_backup.json"
    else:
        # CSV rankings export
        output = StringIO()
        writer = csv.writer(output)
        writer.writerow(['rank', 'name', 'rating', 'wins', 'losses', 'ties', 'win_rate'])
        for item in rankings:
            writer.writerow([
                item['rank'],
                item['name'],
                item['rating'],
                item['stats']['wins'],
                item['stats']['losses'],
                item['stats']['ties'],
                item['stats']['win_rate']
            ])
        output = output.getvalue()
        mimetype = 'text/csv'
        filename = f"{project['name']}_rankings.csv"

    return Response(
        output,
        mimetype=mimetype,
        headers={'Content-Disposition': f'attachment; filename="{filename}"'}
    )


@projects_bp.route('/<project_id>/rankings')
@login_required
def rankings(project_id):
    """View full rankings."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project:
        flash('Project not found', 'error')
        return redirect(url_for('projects.list_projects'))

    page = request.args.get('page', 1, type=int)
    per_page = 50
    offset = (page - 1) * per_page

    all_rankings = project_manager.get_rankings(current_user.id, project_id)
    total_items = len(all_rankings)
    total_pages = (total_items + per_page - 1) // per_page

    rankings = all_rankings[offset:offset + per_page]

    return render_template('rankings/view.html',
                           project=project,
                           rankings=rankings,
                           page=page,
                           total_pages=total_pages,
                           total_items=total_items)
