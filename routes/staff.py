from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from models import (db, StaffProfile, Trek, Booking,
                    BOOKING_BOOKED, BOOKING_CANCELLED, BOOKING_COMPLETED)
from routes import role_required

staff_bp = Blueprint('staff', __name__)

# Statuses a guide is allowed to set on a trek they lead.
GUIDE_STATUSES = ['Approved', 'Open', 'Closed', 'Ongoing', 'Completed']


def my_trek_or_403(trek_id):
    """Guides may only touch treks they are assigned to."""
    trek = Trek.query.get_or_404(trek_id)
    if trek.guide_id != current_user.id:
        abort(403)
    return trek


@staff_bp.route('/dashboard')
@login_required
@role_required('staff')
def dashboard():
    my_treks = Trek.query.filter_by(guide_id=current_user.id).order_by(Trek.start_date).all()

    counts = {
        'assigned': len(my_treks),
        'open': sum(1 for trek in my_treks if trek.status == 'Open'),
        'completed': sum(1 for trek in my_treks if trek.status == 'Completed'),
        'trekkers': sum(trek.seats_taken for trek in my_treks),
    }

    return render_template('staff/dashboard.html', treks=my_treks[:5], counts=counts,
                           active_page='dashboard')


@staff_bp.route('/treks')
@login_required
@role_required('staff')
def treks():
    my_treks = Trek.query.filter_by(guide_id=current_user.id).order_by(Trek.start_date).all()
    return render_template('staff/treks.html', treks=my_treks, active_page='treks')


@staff_bp.route('/treks/<int:trek_id>')
@login_required
@role_required('staff')
def manage_trek(trek_id):
    trek = my_trek_or_403(trek_id)
    participants = [booking for booking in trek.bookings if booking.status != BOOKING_CANCELLED]

    return render_template('staff/manage_trek.html', trek=trek, participants=participants,
                           guide_statuses=GUIDE_STATUSES, active_page='treks')


@staff_bp.route('/treks/<int:trek_id>/update', methods=['POST'])
@login_required
@role_required('staff')
def update_trek(trek_id):
    trek = my_trek_or_403(trek_id)

    seats_left = int(request.form.get('available_slots'))
    free_capacity = trek.total_slots - trek.seats_taken

    if seats_left < 0 or seats_left > free_capacity:
        flash(f'Available slots must be between 0 and {free_capacity}.', 'danger')
        return redirect(url_for('staff.manage_trek', trek_id=trek.id))

    status = request.form.get('status')
    if status not in GUIDE_STATUSES:
        abort(400)

    trek.available_slots = seats_left
    trek.status = status
    db.session.commit()

    flash('Trek details updated.', 'success')
    return redirect(url_for('staff.manage_trek', trek_id=trek.id))


@staff_bp.route('/treks/<int:trek_id>/stage', methods=['POST'])
@login_required
@role_required('staff')
def set_stage(trek_id):
    """One-click progress: start the trek, or close it off as completed."""
    trek = my_trek_or_403(trek_id)
    stage = request.form.get('stage')

    if stage == 'Ongoing':
        trek.status = 'Ongoing'
        trek.available_slots = 0
        flash(f'"{trek.title}" is now ongoing - bookings are closed.', 'success')

    elif stage == 'Completed':
        trek.status = 'Completed'
        trek.available_slots = 0
        for booking in trek.bookings:
            if booking.status == BOOKING_BOOKED:
                booking.status = BOOKING_COMPLETED
        flash(f'"{trek.title}" completed. Participant records moved to history.', 'success')

    else:
        abort(400)

    db.session.commit()
    return redirect(url_for('staff.manage_trek', trek_id=trek.id))


@staff_bp.route('/bookings/<int:booking_id>/payment', methods=['POST'])
@login_required
@role_required('staff')
def mark_payment(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    my_trek_or_403(booking.trek_id)

    booking.payment_status = 'Paid' if booking.payment_status == 'Pending' else 'Pending'
    db.session.commit()

    flash(f'Payment for {booking.trekker.full_name} marked as {booking.payment_status}.', 'info')
    return redirect(url_for('staff.manage_trek', trek_id=booking.trek_id))


@staff_bp.route('/bookings/<int:booking_id>/remove', methods=['POST'])
@login_required
@role_required('staff')
def remove_participant(booking_id):
    booking = Booking.query.get_or_404(booking_id)
    trek = my_trek_or_403(booking.trek_id)

    if booking.status != BOOKING_BOOKED:
        flash('Only active bookings can be removed.', 'warning')
        return redirect(url_for('staff.manage_trek', trek_id=trek.id))

    booking.status = BOOKING_CANCELLED
    trek.available_slots = min(trek.available_slots + 1, trek.total_slots)
    db.session.commit()

    flash(f'{booking.trekker.full_name} removed from the participant list.', 'info')
    return redirect(url_for('staff.manage_trek', trek_id=trek.id))


@staff_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@role_required('staff')
def profile():
    if current_user.staff_profile is None:
        current_user.staff_profile = StaffProfile()
        db.session.commit()

    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name')
        current_user.phone = request.form.get('phone')

        profile_data = current_user.staff_profile
        profile_data.experience_years = int(request.form.get('experience_years') or 0)
        profile_data.specialisation = request.form.get('specialisation')
        profile_data.base_region = request.form.get('base_region')
        profile_data.bio = request.form.get('bio')

        new_password = request.form.get('new_password')
        if new_password:
            current_user.password_hash = generate_password_hash(new_password)

        db.session.commit()
        flash('Profile saved.', 'success')
        return redirect(url_for('staff.profile'))

    return render_template('staff/profile.html', active_page='profile')