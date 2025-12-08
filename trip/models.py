from trip import database, login_manager
from flask_login import UserMixin


class Viajante(database.Model, UserMixin):
    __tablename__ = 'viajantes'

    id = database.Column(database.Integer, primary_key=True)
    nome = database.Column(database.String, nullable=False)
    email = database.Column(database.String, nullable=False, unique=True)
    senha = database.Column(database.String, nullable=True)
    is_verified = database.Column(database.Boolean, default=False)
    viagem = database.relationship('Viagem', backref='viajante', lazy=True, cascade="all, delete")

    def __repr__(self):
        return f"<Viajante {self.nome}>"


class Viagem(database.Model):
    __tablename__ = 'viagens'

    id = database.Column(database.Integer, primary_key=True)
    destino = database.Column(database.String, nullable=False)
    valor_total = database.Column(database.Float, nullable=False)
    valor_restante = database.Column(database.Float)
    id_viajante = database.Column(database.Integer, database.ForeignKey('viajantes.id', name='fk_viagem_viajante'), nullable=False)
    atividades = database.relationship('Atividade', backref='viagem', lazy=True, cascade="all, delete")

    def __init__(self, destino, valor_total, id_viajante):
        self.destino = destino
        self.valor_total = valor_total
        self.valor_restante = valor_total # inicia igual ao total
        self.id_viajante = id_viajante

    
    def atualizar_valor_restante(self):
        # soma valor de todas as atividades
        total_atividades = sum([atividade.valor_atividade for atividade in self.atividades])
        self.valor_restante = self.valor_total - total_atividades

    def __repr__(self):
        return f"<Viagem para {self.destino}>"


class Atividade(database.Model):
    __tablename__ = 'atividades'

    id = database.Column(database.Integer, primary_key=True)
    nome_atividade = database.Column(database.String, nullable=False)
    valor_atividade = database.Column(database.Float, nullable=False)
    id_viagem = database.Column(database.Integer, database.ForeignKey('viagens.id', name='fk_atividade_viagem'), nullable=False)

    def __repr__(self):
        return f"<Atividade {self.nome_atividade}>"


# o 'login_manager' precisa de uma função que encontre o usuário pelo id dele (chave primária dele)
# e para sinalizar para o 'login_manager' a função precisamos de um decorator 
@login_manager.user_loader
def load_viajante(id_viajante):
    return Viajante.query.get(int(id_viajante))