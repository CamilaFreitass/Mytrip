from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate

app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///mytrip.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = '0d22a0a6a40fae9a00bb16054f87751b'

database = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'acesso'
login_manager.login_message_category = 'alert-info'
migrate = Migrate(app, database)

# essa importação tem que vir aqui embaixo, pq primeiro eu preciso criar o app para depois importar os routes
from trip import routes