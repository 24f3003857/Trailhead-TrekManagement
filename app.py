from flask import Flask, render_template
from flask_login import LoginManager

from config import Config
from models import db, User, Trek
from seed import setup_database

login_manager = LoginManager()
login_manager.login_view = 'auth.login'
login_manager.login_message = 'Please log in to continue.'
login_manager.login_message_category = 'warning'


@login_manager.user_loader
def load_user(user_id):
    return db.session.get(User, int(user_id))


def create_app():
    app = Flask(__name__)
    app.config.from_object(Config)

    db.init_app(app)
    login_manager.init_app(app)

    from routes.auth import auth_bp
    from routes.admin import admin_bp
    from routes.staff import staff_bp
    from routes.trekker import trekker_bp

    app.register_blueprint(auth_bp, url_prefix='/auth')
    app.register_blueprint(admin_bp, url_prefix='/admin')
    app.register_blueprint(staff_bp, url_prefix='/staff')
    app.register_blueprint(trekker_bp, url_prefix='/trekker')

    with app.app_context():
        setup_database()

    @app.route('/')
    def home():
        featured = (Trek.query
                    .filter(Trek.status == 'Open')
                    .order_by(Trek.start_date)
                    .limit(3).all())
        return render_template('home.html', featured=featured)

    @app.errorhandler(403)
    def forbidden(error):
        return render_template('error.html', code=403,
                               message='This area belongs to a different role.'), 403

    @app.errorhandler(404)
    def not_found(error):
        return render_template('error.html', code=404,
                               message='That trail does not exist.'), 404

    return app

app = create_app()
if __name__ == '__main__':
    app.run(debug=True)