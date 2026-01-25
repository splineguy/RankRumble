"""
Authentication routes.
"""
from flask import render_template, redirect, url_for, flash, request, current_app
from flask_login import login_user, logout_user, login_required, current_user

from app.blueprints.auth import auth_bp
from app.blueprints.auth.forms import LoginForm, RegistrationForm


def get_user_manager():
    """Get the user manager from app context."""
    return current_app.user_manager


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    """User login."""
    if current_user.is_authenticated:
        return redirect(url_for('projects.list_projects'))

    form = LoginForm()
    if form.validate_on_submit():
        user_manager = get_user_manager()
        user = user_manager.get_user_by_username(form.username.data)

        if user and user_manager.verify_password(user, form.password.data):
            login_user(user, remember=form.remember_me.data)
            user_manager.update_last_login(user.id)

            next_page = request.args.get('next')
            if not next_page or not next_page.startswith('/'):
                next_page = url_for('projects.list_projects')
            return redirect(next_page)

        flash('Invalid username or password', 'error')

    return render_template('auth/login.html', form=form)


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """User registration."""
    if current_user.is_authenticated:
        return redirect(url_for('projects.list_projects'))

    form = RegistrationForm()
    if form.validate_on_submit():
        user_manager = get_user_manager()

        try:
            user = user_manager.create_user(
                username=form.username.data,
                email=form.email.data,
                password=form.password.data
            )
            flash('Registration successful! Please log in.', 'success')
            return redirect(url_for('auth.login'))
        except ValueError as e:
            flash(str(e), 'error')

    return render_template('auth/register.html', form=form)


@auth_bp.route('/logout')
@login_required
def logout():
    """User logout."""
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))
