from flask_login import UserMixin
from trip import login_manager 
# Embora o login_manager seja configurado em __init__.py, ele precisa do user_loader
# que usará as novas classes.

class Viajante(UserMixin):
    """
    Classe simples para mapear dados de um Documento 'viajantes' do Firestore.
    Herdar de UserMixin facilita a integração com Flask-Login.
    """
    
    # ATENÇÃO: O 'id' relacional foi substituído pelo 'doc_id' do Firestore
    def __init__(self, data):
        self.doc_id = data.get('doc_id')         # ID do Documento no Firestore
        self.nome = data.get('nome')
        self.email = data.get('email')
        self.senha = data.get('senha')           # Hash da senha
        self.is_verified = data.get('is_verified', False)
        # Não precisamos de 'viagem' aqui, pois relações são estruturadas de forma diferente no NoSQL
    
    # Método obrigatório para o Flask-Login
    def get_id(self):
        # Retornamos o ID do Documento do Firestore, que será usado no user_loader
        return str(self.doc_id)

    def __repr__(self):
        return f"<Viajante {self.nome}>"


# No Firestore, as coleções filhas (Viagem e Atividade) geralmente
# são armazenadas em Documentos separados ou subcoleções.
# As classes abaixo servem para estruturar os dados.

class Viagem:
    
    def __init__(self, data):
        self.doc_id = data.get('doc_id')
        self.destino = data.get('destino')
        self.valor_total = data.get('valor_total')
        self.valor_restante = data.get('valor_restante', self.valor_total)
        self.id_viajante = data.get('id_viajante')
        self.atividades = data.get('atividades', [])
        
    # No Firestore, 'atualizar_valor_restante' exigirá uma consulta a subcoleções
    # e uma escrita (update) no documento pai (Viagem).
    # O método deve ser implementado no firestore_service.py para acessar o DB.
    
    def __repr__(self):
        return f"<Viagem para {self.destino}>"


class Atividade:
    
    def __init__(self, data):
        self.doc_id = data.get('doc_id')
        self.nome_atividade = data.get('nome_atividade')
        self.valor_atividade = data.get('valor_atividade')
        self.id_viagem = data.get('id_viagem')
        
    def __repr__(self):
        return f"<Atividade {self.nome_atividade}>"


# -------------------------------------------------------------------------
# O 'login_manager.user_loader' precisa ser reescrito para o Firestore
# -------------------------------------------------------------------------

@login_manager.user_loader
def load_viajante(doc_id):
    """
    Função chamada pelo Flask-Login para recarregar o usuário a partir do ID 
    (Doc ID do Firestore) armazenado na sessão.
    """
    # Importação local para evitar erro circular
    from trip.firestore_service import buscar_viajante_por_doc_id

    # Usamos a função de serviço para buscar o Documento pelo ID
    viajante_data = buscar_viajante_por_doc_id(doc_id)
    
    if viajante_data:
        # Retorna uma instância da nossa nova classe Viajante
        return Viajante(viajante_data)
        
    return None