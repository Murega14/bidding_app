from flask import Flask
from .models import db
from .Routes.admin import admin
from .Routes.user import user
from flask_migrate import Migrate
from config import Config
from flask_jwt_extended import JWTManager

app = Flask(__name__)

app.config.from_object(Config)
db.init_app(app)
migrate = Migrate(app, db)
jwt = JWTManager()
jwt.init_app(app)

app.register_blueprint(admin, url_prefix='')
app.register_blueprint(user, url_prefix='')

if __name__ == '__main__':
    app.run(debug=True)