from flask import Blueprint, render_template, redirect, url_for, flash, request
from flask_login import login_user, logout_user, login_required, current_user
from werkzeug.security import generate_password_hash, check_password_hash

from models import (db, User, StaffProfile,
                    ROLE_STAFF, ROLE_TREKKER,
                    STATUS_ACTIVE, STATUS_PENDING, STATUS_BLACKLISTED)

auth_bp = Blueprint('auth', __name__)


def dashboard_for(user):
    return url_for(f'{user.role}.dashboard')


def email_taken(email):
    return User.query.filter_by(email=email).first() is not None


@auth_bp.route('/register', methods=['GET', 'POST'])
def register():
    """Trekker sign-up. Accounts are usable straight away."""
    if current_user.is_authenticated:
        return redirect(dashboard_for(current_user))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if email_taken(email):
            flash('That email is already registered.', 'danger')
            return redirect(url_for('auth.register'))

        trekker = User(
            full_name=request.form.get('full_name'),
            email=email,
            password_hash=generate_password_hash(request.form.get('password')),
            phone=request.form.get('phone'),
            role=ROLE_TREKKER,
            account_status=STATUS_ACTIVE
        )
        db.session.add(trekker)
        db.session.commit()

        flash('Account created. You can log in now.', 'success')
        return redirect(url_for('auth.login'))

    return render_template('auth/register.html')


@auth_bp.route('/register/staff', methods=['GET', 'POST'])
def register_staff():
    """Guide sign-up. Stays pending until an admin approves the account."""
    if current_user.is_authenticated:
        return redirect(dashboard_for(current_user))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()

        if email_taken(email):
            flash('That email is already registered.', 'danger')
            return redirect(url_for('auth.register_staff'))

        guide = User(
            full_name=request.form.get('full_name'),
            email=email,
            password_hash=generate_password_hash(request.form.get('password')),
            phone=request.form.get('phone'),
            role=ROLE_STAFF,
            account_status=STATUS_PENDING
        )
        guide.staff_profile = StaffProfile(
            experience=int(request.form.get('experience') or 0),
            specialisation=request.form.get('specialisation'),
            base_region=request.form.get('base_region'),
            bio=request.form.get('bio')
        )
        db.session.add(guide)
        db.session.commit()

        flash('Application submitted. An admin will review it before you can log in.', 'info')
        return redirect(url_for('auth.login'))

    return render_template('auth/register_staff.html')


@auth_bp.route('/login', methods=['GET', 'POST'])
def login():
    if current_user.is_authenticated:
        return redirect(dashboard_for(current_user))

    if request.method == 'POST':
        email = request.form.get('email', '').strip().lower()
        user = User.query.filter_by(email=email).first()

        if not user or not check_password_hash(user.password_hash, request.form.get('password', '')):
            flash('Email or password is incorrect.', 'danger')
            return redirect(url_for('auth.login'))

        if user.account_status == STATUS_PENDING:
            flash('Your guide application is still awaiting admin approval.', 'warning')
            return redirect(url_for('auth.login'))

        if user.account_status == STATUS_BLACKLISTED:
            flash('This account has been deactivated. Please contact the admin.', 'danger')
            return redirect(url_for('auth.login'))

        login_user(user)
        flash(f'Welcome back, {user.full_name}.', 'success')
        return redirect(dashboard_for(user))

    return render_template('auth/login.html')


@auth_bp.route('/logout')
@login_required
def logout():
    logout_user()
    flash('You have been logged out.', 'info')
    return redirect(url_for('auth.login'))