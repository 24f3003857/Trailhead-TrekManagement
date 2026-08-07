from datetime import datetime
from flask_sqlalchemy import SQLAlchemy
from flask_login import UserMixin

db = SQLAlchemy()

ROLE_ADMIN = 'admin'
ROLE_STAFF = 'staff'
ROLE_TREKKER = 'trekker'

#Account statuses:
STATUS_ACTIVE = 'active'
STATUS_PENDING = 'pending'
STATUS_BLACKLISTED = 'blacklisted'

#Trek Lifecycle:
TREK_STATUSES = ['Pending','Approved', 'Ongoing', 'Completed']
DIFFICULTIES = ['Easy','Moderate','Hard']

#Booking states:
BOOKING_BOOKED = 'Booked'
BOOKING_CANCELLED = 'Cancelled'
BOOKING_COMPLETED = 'Completed'

#Users table:
class User(db.Model, UserMixin):
    __tablename__ = 'users'
    id = db.Column(db.Integer, primary_key = True)
    full_name = db.Column(db.String(120), nullable = False)
    email = db.Column(db.String(120), unique = True, nullable = False)
    phone = db.Column(db.String(20))
    password_hash = db.Column(db.String(255), nullable = False)
    role = db.Column(db.String(20), nullable = False)
    account_status = db.Column(db.String(20), nullable = False, default = STATUS_ACTIVE)
    joined_on = db.Column(db.DateTime, default = datetime.utcnow)
    staff_profile = db.relationship(
        'StaffProfile',
        back_populates = 'user',
        uselist = False,
        cascade = 'all, delete-orphan'
    )
    bookings = db.relationship(
        'Booking',
        back_populates = 'trekker',
        cascade = 'all delete-orphan'
    )
    treks_guided = db.relationship(
        'Trek',
        back_populates = 'guide'
    )

    @property
    def is_active(self):
        return self.account_status == STATUS_ACTIVE

class StaffProfile(db.Model):
    __tablename__ = 'staff_profiles'
    id = db.Column(db.Integer, primary_key = True)
    user_id = db.Column(db.Integer, db.ForeignKey('users.id'), unique = True, nullable = False)
    experience = db.Column(db.Integer, default = 0)
    specialisation = db.Column(db.String(120))
    base_region = db.Column(db.String(120))
    bio = db.Column(db.Text)
    user = db.relationship(
        'User',
        back_populates = 'staff_profile'
    )

class Trek(db.Model):
    __tablename__ = 'treks'
    id = db.Column(db.Integer, primary_key = True)
    title = db.Column(db.String(120), nullable = False)
    region = db.Column(db.String(120), nullable = False)
    difficulty = db.Column(db.String(20), nullable = False)
    duration_days = db.Column(db.Integer, nullable = False)
    total_slots = db.Column(db.Integer, nullable = False)
    available_slots = db.Column(db.Integer, nullable = False)
    status = db.Column(db.String(20), nullable = False, default = 'Pending')
    start_date = db.Column(db.Date, nullable = False)
    end_date = db.Column(db.Date, nullable = False)
    summary = db.Column(db.Text)
    photo_url = db.Column(db.String(300))
    guide_id = db.Column(db.Integer, db.ForeignKey('users.id'))
    created_on = db.Column(db.DateTime, nullable = False, default = datetime.utcnow)
    guide = db.relationship(
        'User', 
        back_populates = 'treks_guided'
    )
    bookings = db.relationship(
        'Booking',
        back_populates = 'trek',
        cascade = 'all delete-orphan'
    )

    @property
    def seats_taken(self):
        return sum(1 for booking in self.bookings if booking.status == BOOKING_BOOKED)

    @property
    def is_bookable(self):
        return self.status == 'Open' and self.available_slots > 0

    class Booking(db.Model):
        __tablename__ = 'bookings'
        id = db.Column(db.Integer, primary_key = True)
        trekker_id = db.Column(db.Integer, db.ForeignKey('users.id'), nullable = False)
        trek_id = db.Column(db.Integer, db.ForeignKey('treks.id'), nullable = False)
        status = db.Column(db.String(20), nullable = False, default = BOOKING_BOOKED)
        payment_status = db.Column(db.String(20), nullable = False, default = 'Pending')
        booked_on = db.Column(db.DateTime, default = datetime.utcnow)
        trekker = db.relationship(
            'User',
            back_populates = 'bookings'
        )
        trek = db.relationship(
            'Trek',
            back_populates = 'bookings'
        )
