from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from werkzeug.security import generate_password_hash

from models import (db, Trek, Booking, DIFFICULTIES,
                    BOOKING_BOOKED, BOOKING_CANCELLED, BOOKING_COMPLETED)
from routes import role_required

trekker_bp = Blueprint('trekker', __name__)


def my_booking_for(trek_id):
    return Booking.query.filter_by(trekker_id=current_user.id, trek_id=trek_id,
                                   status=BOOKING_BOOKED).first()


@trekker_bp.route('/dashboard')
@login_required
@role_required('trekker')
def dashboard():
    my_bookings = (Booking.query.filter_by(trekker_id=current_user.id)
                   .order_by(Booking.booked_on.desc()).all())

    counts = {
        'active': sum(1 for booking in my_bookings if booking.status == BOOKING_BOOKED),
        'completed': sum(1 for booking in my_bookings if booking.status == BOOKING_COMPLETED),
        'cancelled': sum(1 for booking in my_bookings if booking.status == BOOKING_CANCELLED),
        'open_treks': Trek.query.filter_by(status='Open').count(),
    }

    return render_template('trekker/dashboard.html', bookings=my_bookings[:5], counts=counts,
                           active_page='dashboard')


@trekker_bp.route('/treks')
@login_required
@role_required('trekker')
def treks():
    """Only treks that are open, or approved and about to open, are listed."""
    query = Trek.query.filter(Trek.status.in_(['Open', 'Approved']))

    term = request.args.get('q', '').strip()
    difficulty = request.args.get('difficulty', '')
    region = request.args.get('region', '').strip()

    if term:
        query = query.filter(Trek.title.ilike(f'%{term}%'))
    if difficulty:
        query = query.filter_by(difficulty=difficulty)
    if region:
        query = query.filter(Trek.region.ilike(f'%{region}%'))

    return render_template('trekker/treks.html',
                           treks=query.order_by(Trek.start_date).all(),
                           difficulties=DIFFICULTIES, term=term,
                           difficulty=difficulty, region=region, active_page='treks')


@trekker_bp.route('/treks/<int:trek_id>')
@login_required
@role_required('trekker')
def trek_detail(trek_id):
    trek = Trek.query.get_or_404(trek_id)
    return render_template('trekker/trek_detail.html', trek=trek,
                           existing=my_booking_for(trek.id), active_page='treks')


@trekker_bp.route('/treks/<int:trek_id>/book', methods=['POST'])
@login_required
@role_required('trekker')
def book_trek(trek_id):
    trek = Trek.query.get_or_404(trek_id)

    if trek.status != 'Open':
        flash(f'"{trek.title}" is not open for booking right now.', 'danger')
        return redirect(url_for('trekker.trek_detail', trek_id=trek.id))

    if my_booking_for(trek.id):
        flash('You have already booked this trek.', 'warning')
        return redirect(url_for('trekker.bookings'))

    if trek.available_slots <= 0:
        flash(f'"{trek.title}" is fully booked.', 'danger')
        return redirect(url_for('trekker.trek_detail', trek_id=trek.id))

    db.session.add(Booking(trekker_id=current_user.id, trek_id=trek.id))
    trek.available_slots -= 1
    db.session.commit()

    flash(f'Booked! Your seat on "{trek.title}" is confirmed.', 'success')
    return redirect(url_for('trekker.bookings'))


@trekker_bp.route('/bookings')
@login_required
@role_required('trekker')
def bookings():
    my_bookings = (Booking.query.filter_by(trekker_id=current_user.id, status=BOOKING_BOOKED)
                   .order_by(Booking.booked_on.desc()).all())
    return render_template('trekker/bookings.html', bookings=my_bookings, active_page='bookings')


@trekker_bp.route('/bookings/<int:booking_id>/cancel', methods=['POST'])
@login_required
@role_required('trekker')
def cancel_booking(booking_id):
    booking = Booking.query.get_or_404(booking_id)

    if booking.trekker_id != current_user.id:
        abort(403)

    if booking.status != BOOKING_BOOKED:
        flash('That booking can no longer be cancelled.', 'warning')
        return redirect(url_for('trekker.bookings'))

    booking.status = BOOKING_CANCELLED
    booking.trek.available_slots = min(booking.trek.available_slots + 1, booking.trek.total_slots)
    db.session.commit()

    flash('Booking cancelled.', 'info')
    return redirect(url_for('trekker.bookings'))


@trekker_bp.route('/history')
@login_required
@role_required('trekker')
def history():
    """Every past record of this trekker - completed and cancelled alike."""
    past = (Booking.query
            .filter(Booking.trekker_id == current_user.id,
                    Booking.status.in_([BOOKING_COMPLETED, BOOKING_CANCELLED]))
            .order_by(Booking.booked_on.desc()).all())

    days_walked = sum(booking.trek.duration_days for booking in past if booking.status == BOOKING_COMPLETED)

    return render_template('trekker/history.html', bookings=past,
                           days_walked=days_walked, active_page='history')


@trekker_bp.route('/profile', methods=['GET', 'POST'])
@login_required
@role_required('trekker')
def profile():
    if request.method == 'POST':
        current_user.full_name = request.form.get('full_name')
        current_user.phone = request.form.get('phone')

        new_password = request.form.get('new_password')
        if new_password:
            current_user.password_hash = generate_password_hash(new_password)

        db.session.commit()
        flash('Profile saved.', 'success')
        return redirect(url_for('trekker.profile'))

    return render_template('trekker/profile.html', active_page='profile')