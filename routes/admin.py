from datetime import datetime

from flask import Blueprint, render_template, request, redirect, url_for, flash
from flask_login import login_required
from werkzeug.security import generate_password_hash

from models import (db, User, StaffProfile, Trek, Booking,
                    ROLE_STAFF, ROLE_TREKKER,
                    STATUS_ACTIVE, STATUS_PENDING, STATUS_BLACKLISTED,
                    TREK_STATUSES, DIFFICULTIES)
from routes import role_required

admin_bp = Blueprint('admin', __name__)


def name_or_id(model, name_column, term):
    # Search filter
    condition = name_column.ilike(f'%{term}%')
    if term.isdigit():
        condition = condition | (model.id == int(term))
    return condition


@admin_bp.route('/dashboard')
@login_required
@role_required('admin')
def dashboard():
    counts = {
        'treks': Trek.query.count(),
        'trekkers': User.query.filter_by(role=ROLE_TREKKER).count(),
        'staff': User.query.filter_by(role=ROLE_STAFF, account_status=STATUS_ACTIVE).count(),
        'bookings': Booking.query.count(),
    }
    awaiting_approval = User.query.filter_by(role=ROLE_STAFF, account_status=STATUS_PENDING).count()
    unassigned = Trek.query.filter_by(guide_id=None).count()
    recent_bookings = Booking.query.order_by(Booking.booked_on.desc()).limit(6).all()

    return render_template('admin/dashboard.html', counts=counts,
                           awaiting_approval=awaiting_approval, unassigned=unassigned,
                           recent_bookings=recent_bookings, active_page='dashboard')



@admin_bp.route('/treks')
@login_required
@role_required('admin')
def treks():
    term = request.args.get('q', '').strip()
    query = Trek.query
    if term:
        query = query.filter(name_or_id(Trek, Trek.title, term))

    return render_template('admin/treks.html',
                           treks=query.order_by(Trek.start_date.desc()).all(),
                           guides=User.query.filter_by(role=ROLE_STAFF, account_status=STATUS_ACTIVE).all(),
                           term=term, active_page='treks')


@admin_bp.route('/treks/new', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def new_trek():
    if request.method == 'POST':
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()

        if end_date < start_date:
            flash('The end date cannot fall before the start date.', 'danger')
            return redirect(url_for('admin.new_trek'))

        total_slots = int(request.form.get('total_slots'))
        trek = Trek(
            title=request.form.get('title'),
            region=request.form.get('region'),
            difficulty=request.form.get('difficulty'),
            start_date=start_date,
            end_date=end_date,
            duration_days=(end_date - start_date).days + 1,
            total_slots=total_slots,
            available_slots=total_slots,
            summary=request.form.get('summary'),
            photo_url=request.form.get('photo_url'),
            status='Pending'
        )
        db.session.add(trek)
        db.session.commit()

        flash(f'"{trek.title}" created. Assign a guide to approve it.', 'success')
        return redirect(url_for('admin.treks'))

    return render_template('admin/trek_form.html', trek=None,
                           difficulties=DIFFICULTIES, statuses=TREK_STATUSES,
                           active_page='treks')


@admin_bp.route('/treks/<int:trek_id>/edit', methods=['GET', 'POST'])
@login_required
@role_required('admin')
def edit_trek(trek_id):
    trek = Trek.query.get_or_404(trek_id)

    if request.method == 'POST':
        start_date = datetime.strptime(request.form.get('start_date'), '%Y-%m-%d').date()
        end_date = datetime.strptime(request.form.get('end_date'), '%Y-%m-%d').date()

        if end_date < start_date:
            flash('The end date cannot fall before the start date.', 'danger')
            return redirect(url_for('admin.edit_trek', trek_id=trek.id))

        new_total = int(request.form.get('total_slots'))
        if new_total < trek.seats_taken:
            flash(f'{trek.seats_taken} seats are already booked - total slots cannot go lower.', 'danger')
            return redirect(url_for('admin.edit_trek', trek_id=trek.id))

        trek.title = request.form.get('title')
        trek.region = request.form.get('region')
        trek.difficulty = request.form.get('difficulty')
        trek.start_date = start_date
        trek.end_date = end_date
        trek.duration_days = (end_date - start_date).days + 1
        trek.total_slots = new_total
        trek.available_slots = new_total - trek.seats_taken
        trek.status = request.form.get('status')
        trek.summary = request.form.get('summary')
        trek.photo_url = request.form.get('photo_url')
        db.session.commit()

        flash('Trek updated.', 'success')
        return redirect(url_for('admin.treks'))

    return render_template('admin/trek_form.html', trek=trek,
                           difficulties=DIFFICULTIES, statuses=TREK_STATUSES,
                           active_page='treks')


@admin_bp.route('/treks/<int:trek_id>/assign', methods=['POST'])
@login_required
@role_required('admin')
def assign_guide(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    guide_id = request.form.get('guide_id')

    if not guide_id:
        trek.guide_id = None
        if trek.status in ('Approved', 'Open'):
            trek.status = 'Pending'
        flash(f'Guide removed from "{trek.title}".', 'info')
    else:
        trek.guide_id = int(guide_id)
        if trek.status == 'Pending':
            trek.status = 'Approved'
        flash(f'{trek.guide.full_name} now leads "{trek.title}".', 'success')

    db.session.commit()
    return redirect(url_for('admin.treks'))


@admin_bp.route('/treks/<int:trek_id>/delete', methods=['POST'])
@login_required
@role_required('admin')
def delete_trek(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    title = trek.title
    db.session.delete(trek)
    db.session.commit()
    flash(f'"{title}" and its booking records were removed.', 'info')
    return redirect(url_for('admin.treks'))


# staff

@admin_bp.route('/staff')
@login_required
@role_required('admin')
def staff():
    term = request.args.get('q', '').strip()
    query = User.query.filter_by(role=ROLE_STAFF)
    if term:
        query = query.filter(name_or_id(User, User.full_name, term))
    everyone = query.all()

    return render_template('admin/staff.html',
                           pending=[guide for guide in everyone if guide.account_status == STATUS_PENDING],
                           active=[guide for guide in everyone if guide.account_status == STATUS_ACTIVE],
                           blocked=[guide for guide in everyone if guide.account_status == STATUS_BLACKLISTED],
                           term=term, active_page='staff')


@admin_bp.route('/staff/add', methods=['POST'])
@login_required
@role_required('admin')
def add_staff():
    email = request.form.get('email', '').strip().lower()

    if User.query.filter_by(email=email).first():
        flash('That email is already registered.', 'danger')
        return redirect(url_for('admin.staff'))

    guide = User(
        full_name=request.form.get('full_name'),
        email=email,
        password_hash=generate_password_hash(request.form.get('password')),
        phone=request.form.get('phone'),
        role=ROLE_STAFF,
        account_status=STATUS_ACTIVE
    )
    guide.staff_profile = StaffProfile(
        experience_years=int(request.form.get('experience_years') or 0),
        specialisation=request.form.get('specialisation'),
        base_region=request.form.get('base_region')
    )
    db.session.add(guide)
    db.session.commit()

    flash(f'{guide.full_name} added as an active guide.', 'success')
    return redirect(url_for('admin.staff'))


@admin_bp.route('/staff/<int:staff_id>/approve', methods=['POST'])
@login_required
@role_required('admin')
def approve_staff(staff_id):
    guide = User.query.filter_by(id=staff_id, role=ROLE_STAFF).first_or_404()
    guide.account_status = STATUS_ACTIVE
    db.session.commit()
    flash(f'{guide.full_name} can now log in.', 'success')
    return redirect(url_for('admin.staff'))


@admin_bp.route('/staff/<int:staff_id>/block', methods=['POST'])
@login_required
@role_required('admin')
def block_staff(staff_id):
    guide = User.query.filter_by(id=staff_id, role=ROLE_STAFF).first_or_404()
    guide.account_status = STATUS_BLACKLISTED
    db.session.commit()
    flash(f'{guide.full_name} has been blacklisted.', 'warning')
    return redirect(url_for('admin.staff'))


@admin_bp.route('/staff/<int:staff_id>/remove', methods=['POST'])
@login_required
@role_required('admin')
def remove_staff(staff_id):
    guide = User.query.filter_by(id=staff_id, role=ROLE_STAFF).first_or_404()
    name = guide.full_name

    # Unassign treks
    for trek in guide.led_treks:
        trek.guide_id = None
        if trek.status in ('Approved', 'Open'):
            trek.status = 'Pending'

    db.session.delete(guide)
    db.session.commit()
    flash(f'{name} removed from the system.', 'info')
    return redirect(url_for('admin.staff'))


# trekkers

@admin_bp.route('/trekkers')
@login_required
@role_required('admin')
def trekkers():
    term = request.args.get('q', '').strip()
    query = User.query.filter_by(role=ROLE_TREKKER)
    if term:
        query = query.filter(name_or_id(User, User.full_name, term))

    return render_template('admin/trekkers.html', trekkers=query.all(),
                           term=term, active_page='trekkers')


@admin_bp.route('/trekkers/<int:user_id>/status', methods=['POST'])
@login_required
@role_required('admin')
def toggle_trekker(user_id):
    trekker = User.query.filter_by(id=user_id, role=ROLE_TREKKER).first_or_404()

    if trekker.account_status == STATUS_BLACKLISTED:
        trekker.account_status = STATUS_ACTIVE
        flash(f'{trekker.full_name} reactivated.', 'success')
    else:
        trekker.account_status = STATUS_BLACKLISTED
        flash(f'{trekker.full_name} has been blacklisted.', 'warning')

    db.session.commit()
    return redirect(url_for('admin.trekkers'))


#  records

@admin_bp.route('/bookings')
@login_required
@role_required('admin')
def bookings():
    status = request.args.get('status', '')
    query = Booking.query
    if status:
        query = query.filter_by(status=status)

    return render_template('admin/bookings.html',
                           bookings=query.order_by(Booking.booked_on.desc()).all(),
                           status=status, active_page='bookings')


@admin_bp.route('/search')
@login_required
@role_required('admin')
def search():
    term = request.args.get('q', '').strip()
    found_treks, found_staff, found_trekkers = [], [], []

    if term:
        found_treks = Trek.query.filter(name_or_id(Trek, Trek.title, term)).all()
        people = User.query.filter(name_or_id(User, User.full_name, term)).all()
        found_staff = [person for person in people if person.role == ROLE_STAFF]
        found_trekkers = [person for person in people if person.role == ROLE_TREKKER]

    return render_template('admin/search.html', term=term, treks=found_treks,
                           staff=found_staff, trekkers=found_trekkers, active_page='search')