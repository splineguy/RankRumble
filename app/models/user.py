"""
User model and management for authentication.
"""
import bcrypt
from flask_login import UserMixin

from app.models.storage import load_json, save_json, generate_id, get_timestamp


class User(UserMixin):
    """User class for Flask-Login integration."""

    def __init__(self, user_data: dict):
        self.id = user_data['id']
        self.username = user_data['username']
        self.email = user_data['email']
        self.password_hash = user_data['password_hash']
        self.created_at = user_data.get('created_at')
        self.last_login = user_data.get('last_login')
        self.settings = user_data.get('settings', {})

    def to_dict(self) -> dict:
        """Convert user to dictionary for storage."""
        return {
            'id': self.id,
            'username': self.username,
            'email': self.email,
            'password_hash': self.password_hash,
            'created_at': self.created_at,
            'last_login': self.last_login,
            'settings': self.settings
        }


class UserManager:
    """Manages user data operations."""

    def __init__(self, users_file: str):
        self.users_file = users_file
        self._ensure_data_structure()

    def _ensure_data_structure(self) -> None:
        """Ensure the users file has the correct structure."""
        data = load_json(self.users_file)
        if 'users' not in data:
            data['users'] = {}
        if 'username_index' not in data:
            data['username_index'] = {}
        if 'email_index' not in data:
            data['email_index'] = {}
        save_json(self.users_file, data)

    def _load_data(self) -> dict:
        """Load users data."""
        return load_json(self.users_file, {
            'users': {},
            'username_index': {},
            'email_index': {}
        })

    def _save_data(self, data: dict) -> None:
        """Save users data."""
        save_json(self.users_file, data)

    def create_user(self, username: str, email: str, password: str) -> User:
        """
        Create a new user.

        Args:
            username: Unique username
            email: Unique email address
            password: Plain text password (will be hashed)

        Returns:
            Created User object

        Raises:
            ValueError: If username or email already exists
        """
        data = self._load_data()

        # Check uniqueness
        if username.lower() in data['username_index']:
            raise ValueError("Username already exists")
        if email.lower() in data['email_index']:
            raise ValueError("Email already exists")

        # Create user
        user_id = generate_id('user')
        password_hash = bcrypt.hashpw(
            password.encode('utf-8'),
            bcrypt.gensalt()
        ).decode('utf-8')

        timestamp = get_timestamp()
        user_data = {
            'id': user_id,
            'username': username,
            'email': email,
            'password_hash': password_hash,
            'created_at': timestamp,
            'last_login': None,
            'settings': {
                'default_k_factor': 32,
                'items_per_page': 20,
                'theme': 'light'
            }
        }

        # Update data
        data['users'][user_id] = user_data
        data['username_index'][username.lower()] = user_id
        data['email_index'][email.lower()] = user_id

        self._save_data(data)
        return User(user_data)

    def get_user_by_id(self, user_id: str) -> User | None:
        """Get user by ID."""
        data = self._load_data()
        user_data = data['users'].get(user_id)
        if user_data:
            return User(user_data)
        return None

    def get_user_by_username(self, username: str) -> User | None:
        """Get user by username."""
        data = self._load_data()
        user_id = data['username_index'].get(username.lower())
        if user_id:
            return self.get_user_by_id(user_id)
        return None

    def get_user_by_email(self, email: str) -> User | None:
        """Get user by email."""
        data = self._load_data()
        user_id = data['email_index'].get(email.lower())
        if user_id:
            return self.get_user_by_id(user_id)
        return None

    def verify_password(self, user: User, password: str) -> bool:
        """Verify a user's password."""
        return bcrypt.checkpw(
            password.encode('utf-8'),
            user.password_hash.encode('utf-8')
        )

    def update_last_login(self, user_id: str) -> None:
        """Update user's last login timestamp."""
        data = self._load_data()
        if user_id in data['users']:
            data['users'][user_id]['last_login'] = get_timestamp()
            self._save_data(data)

    def update_settings(self, user_id: str, settings: dict) -> None:
        """Update user settings."""
        data = self._load_data()
        if user_id in data['users']:
            data['users'][user_id]['settings'].update(settings)
            self._save_data(data)
