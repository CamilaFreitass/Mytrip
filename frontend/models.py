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
        # Atributos extras injetados pela API (como percentual e cor)
        self.percentual_gasto = data.get('percentual_gasto', 0)
        self.cor = data.get('cor', 'bg-success')

class Atividade:
    def __init__(self, data):
        self.doc_id = data.get('doc_id')
        self.nome_atividade = data.get('nome_atividade')
        self.valor_atividade = data.get('valor_atividade')