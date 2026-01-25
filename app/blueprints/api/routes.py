"""
RESTful API endpoints for AJAX operations.
"""
from flask import jsonify, request, current_app
from flask_login import login_required, current_user

from app.blueprints.api import api_bp


def get_project_manager():
    """Get the project manager from app context."""
    return current_app.project_manager


@api_bp.route('/projects/<project_id>/pair')
@login_required
def get_battle_pair(project_id):
    """Get a random pair for battle."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project:
        return jsonify({'error': 'Project not found'}), 404

    strategy = request.args.get('strategy', 'random')
    exclude_id = request.args.get('exclude')  # Optional: exclude this item from selection

    pair = project_manager.get_battle_pair(current_user.id, project_id, strategy, exclude_id=exclude_id)

    if not pair:
        return jsonify({'error': 'Not enough items for battle'}), 400

    # If we got a single item (replacement), return just item_a
    if len(pair) == 1:
        return jsonify({
            'item_a': pair[0]
        })

    # Otherwise return both items
    return jsonify({
        'item_a': pair[0],
        'item_b': pair[1]
    })


@api_bp.route('/projects/<project_id>/battle', methods=['POST'])
@login_required
def submit_battle(project_id):
    """Submit a battle result."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project:
        return jsonify({'error': 'Project not found'}), 404

    data = request.get_json()
    if not data:
        return jsonify({'error': 'Invalid JSON'}), 400

    item_a_id = data.get('item_a_id')
    item_b_id = data.get('item_b_id')
    result = data.get('result')

    if not all([item_a_id, item_b_id, result]):
        return jsonify({'error': 'Missing required fields'}), 400

    if result not in ('a_wins', 'b_wins', 'tie'):
        return jsonify({'error': 'Invalid result value'}), 400

    battle_record = project_manager.submit_battle(
        user_id=current_user.id,
        project_id=project_id,
        item_a_id=item_a_id,
        item_b_id=item_b_id,
        result=result
    )

    if not battle_record:
        return jsonify({'error': 'Failed to submit battle'}), 400

    return jsonify({
        'success': True,
        'battle': battle_record
    })


@api_bp.route('/projects/<project_id>/rankings')
@login_required
def get_rankings(project_id):
    """Get rankings as JSON."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project:
        return jsonify({'error': 'Project not found'}), 404

    limit = request.args.get('limit', type=int)
    offset = request.args.get('offset', 0, type=int)

    rankings = project_manager.get_rankings(
        current_user.id, project_id, limit=limit, offset=offset
    )

    return jsonify({
        'rankings': rankings,
        'total': len(project['items'])
    })


@api_bp.route('/projects/<project_id>/items')
@login_required
def get_items(project_id):
    """Get all items as JSON."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project:
        return jsonify({'error': 'Project not found'}), 404

    items = list(project['items'].values())
    return jsonify({
        'items': items,
        'total': len(items)
    })


@api_bp.route('/projects/<project_id>/stats')
@login_required
def get_stats(project_id):
    """Get project statistics."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project:
        return jsonify({'error': 'Project not found'}), 404

    items = list(project['items'].values())
    if not items:
        return jsonify({
            'total_items': 0,
            'total_battles': 0
        })

    ratings = [item['rating'] for item in items]
    sorted_items = sorted(items, key=lambda x: x['rating'], reverse=True)

    stats = {
        'total_items': len(items),
        'total_battles': len(project.get('battle_history', [])),
        'average_rating': round(sum(ratings) / len(ratings), 1),
        'highest_rated': {
            'name': sorted_items[0]['name'],
            'rating': sorted_items[0]['rating']
        } if sorted_items else None,
        'lowest_rated': {
            'name': sorted_items[-1]['name'],
            'rating': sorted_items[-1]['rating']
        } if sorted_items else None
    }

    return jsonify(stats)


@api_bp.route('/projects/<project_id>/history')
@login_required
def get_history(project_id):
    """Get battle history as JSON."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project:
        return jsonify({'error': 'Project not found'}), 404

    limit = request.args.get('limit', 50, type=int)
    offset = request.args.get('offset', 0, type=int)

    history = project_manager.get_battle_history(
        current_user.id, project_id, limit=limit, offset=offset
    )

    return jsonify({
        'battles': history,
        'total': len(project.get('battle_history', []))
    })


@api_bp.route('/projects/<project_id>/items/<item_id>/history')
@login_required
def get_item_history(project_id, item_id):
    """Get rating history for a specific item."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project:
        return jsonify({'error': 'Project not found'}), 404

    if item_id not in project['items']:
        return jsonify({'error': 'Item not found'}), 404

    item = project['items'][item_id]
    return jsonify({
        'item': item,
        'rating_history': item['stats']['rating_history']
    })


@api_bp.route('/projects/<project_id>/items/<item_id>', methods=['DELETE'])
@login_required
def delete_item(project_id, item_id):
    """Delete an item from the project."""
    project_manager = get_project_manager()
    project = project_manager.get_project(current_user.id, project_id)

    if not project:
        return jsonify({'error': 'Project not found'}), 404

    if item_id not in project['items']:
        return jsonify({'error': 'Item not found'}), 404

    success = project_manager.delete_item(current_user.id, project_id, item_id)

    if not success:
        return jsonify({'error': 'Failed to delete item'}), 400

    return jsonify({
        'success': True,
        'message': 'Item deleted successfully'
    })
