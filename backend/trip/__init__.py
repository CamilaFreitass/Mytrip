from flask import Flask
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
from dotenv import load_dotenv
import os
from authlib.integrations.flask_client import OAuth
from flask_mail import Mail
from itsdangerous import URLSafeTimedSerializer
from firebase_admin import initialize_app, credentials, firestore, _apps
from werkzeug.middleware.proxy_fix import ProxyFix

# 1. Ajuste preciso dos caminhos
# Estamos em: Mytrip/backend/trip/__init__.py
pasta_trip = os.path.dirname(__file__)
pasta_backend = os.path.dirname(pasta_trip)
raiz_projeto = os.path.dirname(pasta_backend)

# Carrega o .env da raiz do projeto
load_dotenv(os.path.join(raiz_projeto, '.env'))
app = Flask(__name__,)

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)

app.config['SECRET_KEY'] = os.getenv('SECRET_KEY')

app.config.update(
    SESSION_COOKIE_NAME='backend_session',
    SESSION_COOKIE_SAMESITE='Lax',
    SESSION_COOKIE_SECURE=False, # Permite HTTP
    SESSION_COOKIE_HTTPONLY=True,
    SESSION_COOKIE_DOMAIN=None # Garante que funcione em 127.0.0.1
)

# Força o OAuthlib a aceitar conexões HTTP (sem SSL) para testes locais
os.environ['OAUTHLIB_INSECURE_TRANSPORT'] = '1'

# --- INICIALIZAÇÃO DO FIREBASE FIREBASE ---

FIREBASE_KEY_PATH = os.path.join(raiz_projeto, 'firebase-key.json')

# NOVO: Verifica se o aplicativo Firebase padrão já foi inicializado
# Se a lista de aplicativos inicializados estiver vazia, inicializamos.
if not _apps:
    
    if os.path.exists(FIREBASE_KEY_PATH):
        # Modo de Desenvolvimento Local
        try:
            cred = credentials.Certificate(FIREBASE_KEY_PATH)
            initialize_app(cred)
            print("Firebase inicializado com chave de serviço local.")
        except Exception as e:
            print(f"Erro ao inicializar Firebase (Local): {e}")
    else:
        # Modo de Produção (Cloud Run)
        try:
            initialize_app() 
            print("Firebase inicializado com Credenciais Padrão (ADC).")
        except Exception as e:
            print(f"Aviso: Falha ao inicializar o Firebase com ADC: {e}")


# Cria o cliente do Firestore, que será usado para todas as operações de banco de dados
db = firestore.client()

# Armazena o cliente do DB no objeto 'app' para ser acessado nas rotas
app.config['FIREBASE_DB'] = db

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

# inicializando um objeto serializador seguro que será usado para criar e validar tokens de uso temporário
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
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)
# login_manager.login_view = 'acesso'
# login_manager.login_message_category = 'alert-info'

@login_manager.user_loader
def load_viajante(doc_id):
    """
    Função chamada pelo Flask-Login para recarregar o usuário a partir do ID
    (Doc ID do Firestore) armazenado na sessão.
    """
    # Importação local para evitar erro circular
    from trip.models import Viajante
    from trip.firestore_service import buscar_viajante_por_doc_id

    # Usamos a função de serviço para buscar o Documento pelo ID
    viajante_data = buscar_viajante_por_doc_id(doc_id)

    if viajante_data:
        # Retorna uma instância da nossa nova classe Viajante
        return Viajante(viajante_data)

    return None

# essa importação tem que vir aqui embaixo, pq primeiro eu preciso criar o app para depois importar os routes
from trip import routes