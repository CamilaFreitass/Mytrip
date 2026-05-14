from flask_login import UserMixin

class Viajante(UserMixin):
    def __init__(self, data):
        # Mapeia os dados básicos que o Frontend precisa para a sessão
        self.doc_id = data.get('doc_id') or data.get('email')
        self.nome = data.get('nome')
        self.email = data.get('email')
        self.is_verified = data.get('is_verified', False)

    def get_id(self):
        return str(self.doc_id)

    def __repr__(self):
        return f"<Viajante {self.nome}>"


class Viagem:
    def __init__(self, data):
        self.doc_id = data.get('doc_id')
        self.destino = data.get('destino')
        self.valor_total = data.get('valor_total')
        self.valor_restante = data.get('valor_restante', self.valor_total)
        self.atividades = data.get('atividades', [])
        self.data_inicio = data.get('data_inicio')
        self.data_fim = data.get('data_fim')
        self.percentual_gasto = data.get('percentual_gasto', 0)
        self.cor = data.get('cor', 'bg-success')
        self.moeda_destino = data.get('moeda_destino')
        self.moeda_comparacao = data.get('moeda_comparacao', 'USD')

class Atividade:
    def __init__(self, data):
        self.doc_id = data.get('doc_id')
        self.nome_atividade = data.get('nome_atividade')
        self.valor_atividade = data.get('valor_atividade')
        self.moeda_inserida = data.get('moeda_inserida', 'BRL')
        self.valor_inserido = data.get('valor_inserido', self.valor_atividade)
        self.data_atividade = data.get('data_atividade')