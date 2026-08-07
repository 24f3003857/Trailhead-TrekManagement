from werkzeug.security import generate_password_hash
from models import db, User, ROLE_ADMIN, STATUS_ACTIVE

ADMIN_NAME = 'admin'
ADMIN_EMAIL = 'admin@gmail.com'
ADMIN_PASSWORD = 'admin@0909'

def database_setup():
    db.create_all()
    if User.query.filter_by(role = ROLE_ADMIN).first():
        print('admin account already exists')
        return
    admin = User(
        full_name = ADMIN_NAME,
        email = ADMIN_EMAIL,
        password_hash = generate_password_hash(ADMIN_PASSWORD),
        role = ROLE_ADMIN,
        account_status = STATUS_ACTIVE,
    )
    db.session.add(admin)
    db.session.commit()
    print(f"Admin account details : email : {ADMIN_EMAIL} pass : {ADMIN_PASSWORD}")

if __name__ == '__main__':
    from app import create_app
    with create_app().app_context():
        database_setup()
        