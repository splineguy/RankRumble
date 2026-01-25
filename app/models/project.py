"""
Project model and management for ranking projects.
"""
import os
import random
from typing import List, Tuple

from app.core.elo import update_elo
from app.models.storage import load_json, save_json, generate_id, get_timestamp, ensure_directory


class ProjectManager:
    """Manages project data operations."""

    def __init__(self, projects_dir: str):
        self.projects_dir = projects_dir

    def _get_user_dir(self, user_id: str) -> str:
        """Get the directory for a user's projects."""
        return os.path.join(self.projects_dir, user_id)

    def _get_project_path(self, user_id: str, project_id: str) -> str:
        """Get the file path for a project."""
        return os.path.join(self._get_user_dir(user_id), f"{project_id}.json")

    def create_project(self, user_id: str, name: str, description: str = '',
                       settings: dict = None) -> dict:
        """
        Create a new project.

        Args:
            user_id: Owner's user ID
            name: Project name
            description: Project description
            settings: Optional custom settings

        Returns:
            Created project dict
        """
        project_id = generate_id('proj')
        timestamp = get_timestamp()

        default_settings = {
            'k_factor': 32,
            'default_rating': 1000,
            'allow_ties': True,
            'item_type': 'item'
        }
        if settings:
            default_settings.update(settings)

        project = {
            'id': project_id,
            'user_id': user_id,
            'name': name,
            'description': description,
            'created_at': timestamp,
            'updated_at': timestamp,
            'settings': default_settings,
            'items': {},
            'battle_history': [],
            'statistics': {
                'total_items': 0,
                'total_battles': 0
            }
        }

        self._save_project(user_id, project_id, project)
        return project

    def _save_project(self, user_id: str, project_id: str, project: dict) -> None:
        """Save a project to disk."""
        filepath = self._get_project_path(user_id, project_id)
        save_json(filepath, project)

    def get_project(self, user_id: str, project_id: str) -> dict | None:
        """Get a project by ID."""
        filepath = self._get_project_path(user_id, project_id)
        if os.path.exists(filepath):
            return load_json(filepath)
        return None

    def list_projects(self, user_id: str) -> List[dict]:
        """List all projects for a user."""
        user_dir = self._get_user_dir(user_id)
        if not os.path.exists(user_dir):
            return []

        projects = []
        for filename in os.listdir(user_dir):
            if filename.endswith('.json'):
                filepath = os.path.join(user_dir, filename)
                project = load_json(filepath)
                if project:
                    # Return summary only
                    projects.append({
                        'id': project['id'],
                        'name': project['name'],
                        'description': project['description'],
                        'created_at': project['created_at'],
                        'updated_at': project['updated_at'],
                        'total_items': len(project.get('items', {})),
                        'total_battles': len(project.get('battle_history', []))
                    })

        # Sort by updated_at descending
        projects.sort(key=lambda x: x['updated_at'], reverse=True)
        return projects

    def update_project(self, user_id: str, project_id: str,
                       name: str = None, description: str = None,
                       settings: dict = None) -> dict | None:
        """Update project details."""
        project = self.get_project(user_id, project_id)
        if not project:
            return None

        if name is not None:
            project['name'] = name
        if description is not None:
            project['description'] = description
        if settings is not None:
            project['settings'].update(settings)

        project['updated_at'] = get_timestamp()
        self._save_project(user_id, project_id, project)
        return project

    def delete_project(self, user_id: str, project_id: str) -> bool:
        """Delete a project."""
        filepath = self._get_project_path(user_id, project_id)
        if os.path.exists(filepath):
            os.remove(filepath)
            return True
        return False

    # Item management
    def add_item(self, user_id: str, project_id: str, name: str,
                 metadata: dict = None, initial_rating: int = None) -> dict | None:
        """Add an item to a project."""
        project = self.get_project(user_id, project_id)
        if not project:
            return None

        item_id = generate_id('item')
        rating = initial_rating or project['settings']['default_rating']
        timestamp = get_timestamp()

        item = {
            'id': item_id,
            'name': name,
            'rating': rating,
            'created_at': timestamp,
            'metadata': metadata or {},
            'stats': {
                'wins': 0,
                'losses': 0,
                'ties': 0,
                'total_battles': 0,
                'win_rate': 0.0,
                'rating_history': [{
                    'rating': rating,
                    'timestamp': timestamp
                }]
            }
        }

        project['items'][item_id] = item
        project['statistics']['total_items'] = len(project['items'])
        project['updated_at'] = timestamp
        self._save_project(user_id, project_id, project)
        return item

    def update_item(self, user_id: str, project_id: str, item_id: str,
                    name: str = None, metadata: dict = None) -> dict | None:
        """Update an item's details (not rating)."""
        project = self.get_project(user_id, project_id)
        if not project or item_id not in project['items']:
            return None

        item = project['items'][item_id]
        if name is not None:
            item['name'] = name
        if metadata is not None:
            item['metadata'].update(metadata)

        project['updated_at'] = get_timestamp()
        self._save_project(user_id, project_id, project)
        return item

    def delete_item(self, user_id: str, project_id: str, item_id: str) -> bool:
        """Delete an item from a project."""
        project = self.get_project(user_id, project_id)
        if not project or item_id not in project['items']:
            return False

        del project['items'][item_id]
        project['statistics']['total_items'] = len(project['items'])
        project['updated_at'] = get_timestamp()
        self._save_project(user_id, project_id, project)
        return True

    def get_rankings(self, user_id: str, project_id: str,
                     limit: int = None, offset: int = 0) -> List[dict]:
        """Get items sorted by rating descending."""
        project = self.get_project(user_id, project_id)
        if not project:
            return []

        items = list(project['items'].values())
        items.sort(key=lambda x: x['rating'], reverse=True)

        # Add rank
        for i, item in enumerate(items, start=1):
            item['rank'] = i

        if limit:
            return items[offset:offset + limit]
        return items[offset:]

    # Battle system
    def get_battle_pair(self, user_id: str, project_id: str,
                        strategy: str = 'random', exclude_id: str = None) -> Tuple[dict, dict] | None:
        """
        Get a pair of items for battle.

        Strategies:
        - 'random': Completely random selection
        - 'least_compared': Prioritize items with fewer battles
        - 'close_rating': Pick items with similar ratings

        Args:
            exclude_id: Optional item ID to exclude from selection (useful for getting replacement item)
        """
        project = self.get_project(user_id, project_id)
        if not project or len(project['items']) < 2:
            return None

        items = list(project['items'].values())

        # Filter out excluded item if specified
        if exclude_id:
            items = [item for item in items if item['id'] != exclude_id]
            if len(items) < 1:
                return None

        # If we're excluding an item and only need one replacement, return just one
        if exclude_id and len(items) >= 1:
            if strategy == 'least_compared':
                items.sort(key=lambda x: x['stats']['total_battles'])
                return (items[0],)
            elif strategy == 'close_rating':
                items.sort(key=lambda x: x['rating'])
                return (random.choice(items),)
            else:
                return (random.choice(items),)

        # Normal pair selection
        if len(items) < 2:
            return None

        if strategy == 'least_compared':
            # Sort by battle count, pick from least compared
            items.sort(key=lambda x: x['stats']['total_battles'])
            candidates = items[:max(10, len(items) // 4)]
            if len(candidates) < 2:
                candidates = items
            pair = random.sample(candidates, 2)
        elif strategy == 'close_rating':
            # Pick adjacent items in sorted order
            items.sort(key=lambda x: x['rating'])
            idx = random.randint(0, len(items) - 2)
            pair = [items[idx], items[idx + 1]]
        else:
            # Random
            pair = random.sample(items, 2)

        return tuple(pair)

    def submit_battle(self, user_id: str, project_id: str,
                      item_a_id: str, item_b_id: str,
                      result: str) -> dict | None:
        """
        Submit a battle result.

        Args:
            user_id: User ID
            project_id: Project ID
            item_a_id: First item ID
            item_b_id: Second item ID
            result: 'a_wins', 'b_wins', or 'tie'

        Returns:
            Battle record with rating changes
        """
        project = self.get_project(user_id, project_id)
        if not project:
            return None

        if item_a_id not in project['items'] or item_b_id not in project['items']:
            return None

        item_a = project['items'][item_a_id]
        item_b = project['items'][item_b_id]

        # Determine scores
        if result == 'a_wins':
            score_a, score_b = 1.0, 0.0
        elif result == 'b_wins':
            score_a, score_b = 0.0, 1.0
        else:  # tie
            score_a, score_b = 0.5, 0.5

        # Calculate new ratings
        k = project['settings']['k_factor']
        old_a, old_b = item_a['rating'], item_b['rating']

        new_a = round(update_elo(old_a, old_b, score_a, k))
        new_b = round(update_elo(old_b, old_a, score_b, k))

        timestamp = get_timestamp()

        # Create battle record
        battle_record = {
            'id': generate_id('battle'),
            'timestamp': timestamp,
            'item_a_id': item_a_id,
            'item_b_id': item_b_id,
            'item_a_name': item_a['name'],
            'item_b_name': item_b['name'],
            'winner_id': item_a_id if result == 'a_wins' else (item_b_id if result == 'b_wins' else None),
            'result': result,
            'ratings_before': {'item_a': old_a, 'item_b': old_b},
            'ratings_after': {'item_a': new_a, 'item_b': new_b},
            'rating_changes': {'item_a': new_a - old_a, 'item_b': new_b - old_b}
        }

        # Update items
        item_a['rating'] = new_a
        item_b['rating'] = new_b

        # Update stats for item A
        item_a['stats']['total_battles'] += 1
        if result == 'a_wins':
            item_a['stats']['wins'] += 1
        elif result == 'b_wins':
            item_a['stats']['losses'] += 1
        else:
            item_a['stats']['ties'] += 1

        if item_a['stats']['total_battles'] > 0:
            item_a['stats']['win_rate'] = round(
                item_a['stats']['wins'] / item_a['stats']['total_battles'], 3
            )

        item_a['stats']['rating_history'].append({
            'rating': new_a,
            'timestamp': timestamp
        })

        # Update stats for item B
        item_b['stats']['total_battles'] += 1
        if result == 'b_wins':
            item_b['stats']['wins'] += 1
        elif result == 'a_wins':
            item_b['stats']['losses'] += 1
        else:
            item_b['stats']['ties'] += 1

        if item_b['stats']['total_battles'] > 0:
            item_b['stats']['win_rate'] = round(
                item_b['stats']['wins'] / item_b['stats']['total_battles'], 3
            )

        item_b['stats']['rating_history'].append({
            'rating': new_b,
            'timestamp': timestamp
        })

        # Add to history
        project['battle_history'].append(battle_record)
        project['statistics']['total_battles'] = len(project['battle_history'])
        project['updated_at'] = timestamp

        self._save_project(user_id, project_id, project)
        return battle_record

    def get_battle_history(self, user_id: str, project_id: str,
                           limit: int = 50, offset: int = 0) -> List[dict]:
        """Get battle history, most recent first."""
        project = self.get_project(user_id, project_id)
        if not project:
            return []

        history = project.get('battle_history', [])
        # Reverse to get most recent first
        history = list(reversed(history))
        return history[offset:offset + limit]

    # Import functionality
    def import_items_from_txt(self, user_id: str, project_id: str,
                              content: str) -> int:
        """
        Import items from text (one per line).
        Returns count of items added.
        """
        project = self.get_project(user_id, project_id)
        if not project:
            return 0

        existing_names = {item['name'].lower() for item in project['items'].values()}
        added = 0

        for line in content.strip().split('\n'):
            name = line.strip()
            if name and name.lower() not in existing_names:
                self.add_item(user_id, project_id, name)
                existing_names.add(name.lower())
                added += 1

        return added

    def import_items_from_csv(self, user_id: str, project_id: str,
                              content: str) -> int:
        """
        Import items from CSV (name, optional rating, optional notes).
        Returns count of items added.
        """
        import csv
        from io import StringIO

        project = self.get_project(user_id, project_id)
        if not project:
            return 0

        existing_names = {item['name'].lower() for item in project['items'].values()}
        added = 0

        reader = csv.DictReader(StringIO(content))
        for row in reader:
            name = row.get('name', '').strip()
            if not name or name.lower() in existing_names:
                continue

            rating = None
            if 'rating' in row:
                try:
                    rating = int(row['rating'])
                except (ValueError, TypeError):
                    pass

            metadata = {}
            for key in row:
                if key not in ('name', 'rating'):
                    metadata[key] = row[key]

            self.add_item(user_id, project_id, name,
                          metadata=metadata if metadata else None,
                          initial_rating=rating)
            existing_names.add(name.lower())
            added += 1

        return added

    def import_from_legacy_json(self, user_id: str, project_id: str,
                                content: str) -> int:
        """
        Import from legacy ratings.json format {name: rating}.
        Returns count of items added.
        """
        import json

        project = self.get_project(user_id, project_id)
        if not project:
            return 0

        try:
            data = json.loads(content)
        except json.JSONDecodeError:
            return 0

        existing_names = {item['name'].lower() for item in project['items'].values()}
        added = 0

        for name, rating in data.items():
            if name.lower() not in existing_names:
                self.add_item(user_id, project_id, name, initial_rating=int(rating))
                existing_names.add(name.lower())
                added += 1

        return added
