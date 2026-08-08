"""Database bootstrap.

Creates the tables and the single pre-defined Admin account. Run it once by
hand with `python seed.py`; app.py also calls setup_database() on start-up so
the admin always exists. Re-running it never duplicates the admin.
"""

from werkzeug.security import generate_password_hash

from models import db, User, ROLE_ADMIN, STATUS_ACTIVE

ADMIN_NAME = 'Site Administrator'
ADMIN_EMAIL = 'admin@gmail.com'
ADMIN_PASSWORD = 'Admin@000'


def setup_database():
    db.create_all()

    if User.query.filter_by(role=ROLE_ADMIN).first():
        print('Admin account already present - nothing to seed.')
        return

    admin = User(
        full_name=ADMIN_NAME,
        email=ADMIN_EMAIL,
        password_hash=generate_password_hash(ADMIN_PASSWORD),
        role=ROLE_ADMIN,
        account_status=STATUS_ACTIVE
    )
    db.session.add(admin)
    db.session.commit()
    print(f'Admin account created -> {ADMIN_EMAIL} / {ADMIN_PASSWORD}')


if __name__ == '__main__':
    from app import create_app

    with create_app().app_context():
        setup_database()