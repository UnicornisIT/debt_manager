import os

from flask import Flask
from flask_login import LoginManager
from flask_migrate import Migrate
from config import Config
from extensions import db
from app.utils import format_currency

login_manager = LoginManager()
login_manager.login_view = 'login'


def create_app():
    base_dir = os.path.abspath(os.path.join(os.path.dirname(__file__), '..'))
    app = Flask(
        __name__,
        template_folder=os.path.join(base_dir, 'templates'),
        static_folder=os.path.join(base_dir, 'static'),
        static_url_path='/static'
    )
    app.config.from_object(Config)

    db.init_app(app)
    Migrate(app, db)
    login_manager.init_app(app)

    app.jinja_env.filters['money'] = format_currency

    from app.routes import auth, admin, debts, payments, incomes, expenses, main

    auth.init_app(app)
    admin.init_app(app)
    debts.init_app(app)
    payments.init_app(app)
    incomes.init_app(app)
    expenses.init_app(app)
    main.init_app(app)

    return app


app = create_app()
