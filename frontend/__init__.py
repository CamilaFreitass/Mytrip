from flask import Flask
from flask_login import LoginManager
from dotenv import load_dotenv
import os
import requests

# Carrega variáveis de ambiente do .env
load_dotenv()

app = Flask(__name__)

# Configurações essenciais para sessões e login
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')
app.config.update(
    SESSION_COOKIE_NAME='frontend_session',
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False,  # Permite HTTP para testes locais
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_DOMAIN=None   # Funciona em localhost
)

login_manager = LoginManager(app)
login_manager.login_view = 'acesso'  # Rota de redirecionamento se não logado
login_manager.login_message_category = 'alert-info'

@login_manager.user_loader
def load_user(user_id):
    from models import Viajante
    BACKEND_URL = os.getenv('BACKEND_URL', 'http://127.0.0.1:5000')
    response = requests.get(f"{BACKEND_URL}/api/usuario/{user_id}")
    if response.status_code == 200:
        viajante_data = response.json()
        return Viajante(viajante_data)
    return None

# Importa as rotas (deve vir após a criação do app)
import routes_front