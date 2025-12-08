from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from flask_migrate import Migrate
from dotenv import load_dotenv
import os
from authlib.integrations.flask_client import OAuth
from flask_mail import Mail
from itsdangerous import URLSafeTimedSerializer
from datetime import timedelta


# --- Carregar variáveis do .env ---
# Caminho absoluto para o .env na raiz do projeto
dotenv_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '.env')
load_dotenv(dotenv_path)


app = Flask(__name__)

app.config['SQLALCHEMY_DATABASE_URI'] = os.getenv('SQLALCHEMY_DATABASE_URI')
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
oauth = OAuth(app)

client_id = os.getenv('GOOGLE_CLIENT_ID')
client_secret = os.getenv('GOOGLE_CLIENT_SECRET')

# Configurações do Servidor SMTP (Google Workspace)
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = os.getenv('MAIL_DEFAULT_SENDER')

s = URLSafeTimedSerializer(app.config['SECRET_KEY'])

# Configuração do OAuth com o Google
google = oauth.register(
    name='google',
    client_id=client_id,
    client_secret=client_secret,
    access_token_url='https://accounts.google.com/o/oauth2/token',
    authorize_url='https://accounts.google.com/o/oauth2/auth',
    api_base_url='https://www.googleapis.com/oauth2/v1/',
    userinfo_endpoint='https://www.googleapis.com/oauth2/v3/userinfo',  # Estenda isso se necessário
    client_kwargs={'scope': 'openid email profile'},
    jwks_uri='https://www.googleapis.com/oauth2/v3/certs'
)

mail = Mail(app)
database = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
login_manager.login_view = 'acesso'
login_manager.login_message_category = 'alert-info'
migrate = Migrate(app, database)

# essa importação tem que vir aqui embaixo, pq primeiro eu preciso criar o app para depois importar os routes
from trip import routes