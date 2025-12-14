from flask import Flask
import sys
import os
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))
from config import DB_PATH
from .db import db

def create_app():
    app = Flask(__name__)
    app.config['SQLALCHEMY_DATABASE_URI'] = f'sqlite:///{DB_PATH}'
    app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
    app.secret_key = 'super_secret_key_1234567890'  # Dodano klucz sesji
    db.init_app(app)
    with app.app_context():
        from . import views  # tylko import, bez rejestracji blueprinta
        db.create_all()
    return app

app = create_app()

if __name__ == '__main__':
    from .views import views as views_blueprint
    app.register_blueprint(views_blueprint)
    app.run(debug=True)
