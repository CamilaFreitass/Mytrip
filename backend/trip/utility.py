import os
from trip import s, mail
from flask_mail import Message
from itsdangerous import BadTimeSignature, SignatureExpired
from trip.currency_service import converter, formatar

def calcular_percentual_e_cor(viagens):
    """
    Recebe uma lista de viagens e injeta o percentual e a cor 
    diretamente em cada item da lista.
    """
    for viagem in viagens:
        # 1. Extração Dinâmica
        if isinstance(viagem, dict):
            v_total = float(viagem.get('valor_total', 0))
            v_restante = viagem.get('valor_restante')
        else:
            v_total = float(getattr(viagem, 'valor_total', 0))
            v_restante = getattr(viagem, 'valor_restante', None)

        if v_restante is None:
            v_restante = v_total
        else:
            v_restante = float(v_restante)

        # 2. Cálculo do percentual
        if v_total > 0:
            gasto = v_total - v_restante
            percentual = max(0, min((gasto / v_total) * 100, 100))
        else:
            percentual = 0

        # 3. Definição da cor
        if percentual <= 50:
            cor = 'bg-success'
        elif percentual <= 80:
            cor = 'bg-warning'
        else:
            cor = 'bg-danger'

        # 4. INJEÇÃO DIRETA (O segredo está aqui)
        if isinstance(viagem, dict):
            viagem['percentual_gasto'] = percentual
            viagem['cor'] = cor
        else:
            setattr(viagem, 'percentual_gasto', percentual)
            setattr(viagem, 'cor', cor)

    return viagens # Retorna a mesma lista, mas com os objetos "turbinados"


def _colunas_moeda(moeda_destino: str, moeda_comparacao: str) -> list:
    colunas = ['BRL']
    if moeda_destino and moeda_destino != 'BRL':
        colunas.append(moeda_destino)
    if moeda_comparacao and moeda_comparacao not in colunas:
        colunas.append(moeda_comparacao)
    return colunas


def enriquecer_atividades_com_moedas(atividades: list, moeda_destino: str, moeda_comparacao: str) -> list:
    colunas = _colunas_moeda(moeda_destino, moeda_comparacao)
    for a in atividades:
        moeda_inserida = a.get('moeda_inserida', 'BRL')
        valor_inserido = float(a.get('valor_inserido') or a.get('valor_atividade') or 0)
        valor_brl = float(a.get('valor_atividade') or 0)

        valores = []
        for moeda in colunas:
            if moeda == 'BRL':
                valores.append(formatar(valor_brl, 'BRL'))
            elif moeda == moeda_inserida:
                valores.append(formatar(valor_inserido, moeda))
            else:
                v = converter(valor_brl, 'BRL', moeda)
                valores.append(formatar(v, moeda))

        a['valores_colunas'] = valores

    return atividades


def enriquecer_orcamento_com_moedas(valor_total: float, valor_restante: float, moeda_destino: str, moeda_comparacao: str) -> tuple:
    colunas = _colunas_moeda(moeda_destino, moeda_comparacao)
    orcamento = []
    for moeda in colunas:
        if moeda == 'BRL':
            orcamento.append({
                'moeda': moeda,
                'total': formatar(valor_total, 'BRL'),
                'restante': formatar(valor_restante, 'BRL'),
            })
        else:
            orcamento.append({
                'moeda': moeda,
                'total': formatar(converter(valor_total, 'BRL', moeda), moeda),
                'restante': formatar(converter(valor_restante, 'BRL', moeda), moeda),
            })
    return orcamento, colunas


def cotacoes_do_dia(moeda_destino: str, moeda_comparacao: str) -> list:
    colunas = _colunas_moeda(moeda_destino, moeda_comparacao)
    resultado = [{'moeda': 'BRL', 'taxa_brl': 'base', 'is_base': True}]

    for moeda in colunas:
        if moeda == 'BRL':
            continue
        # Usa BRL como base (já em cache) e inverte para obter 1 moeda → BRL
        taxa_brl_por_unidade = converter(1.0, 'BRL', moeda)
        if taxa_brl_por_unidade:
            taxa = round(1 / taxa_brl_por_unidade, 2)
            resultado.append({'moeda': moeda, 'taxa_brl': formatar(taxa, 'BRL'), 'is_base': False})
        else:
            resultado.append({'moeda': moeda, 'taxa_brl': None, 'is_base': False})

    return resultado


def processar_moeda_atividade(dados: dict) -> dict:
    moeda_inserida = dados.get('moeda_inserida', 'BRL')
    valor_inserido = float(dados.get('valor_atividade') or 0)

    dados['moeda_inserida'] = moeda_inserida
    dados['valor_inserido'] = valor_inserido

    if moeda_inserida != 'BRL':
        valor_brl = converter(valor_inserido, moeda_inserida, 'BRL')
        dados['valor_atividade'] = valor_brl if valor_brl is not None else valor_inserido

    return dados


# recebe o email do novo usuário e usa a biblioteca itsdangerous para criptografar o email
# 'salt' garante que o token seja exclusivo para essa finalidade
def generate_confirmation_token(email):
    return s.dumps(email, salt='email-confirm-salt')


# essa função usa o servidor SMTP configurado (Google Workspace) p; enviar mensagem formatada para a caixa de entrada do usuário
def send_confirmation_email(user_email):
    token = generate_confirmation_token(user_email)

    frontend_url = os.getenv('FRONTEND_URL', 'http://127.0.0.1:8080')
    confirm_url = f"{frontend_url}/confirm/{token}"
    
    msg = Message(
        subject='Confirme Seu E-mail para Ativar Sua Conta',
        recipients=[user_email],
        html=f"""
        <p>Obrigado por se registrar no MyTrip! Por favor, clique no link abaixo para ativar sua conta:</p>
        <p><a href="{confirm_url}">Confirmar Conta Agora</a></p>
        <p>O link expira em 1 hora.</p>
        """
    )
    
    mail.send(msg)


# Função para decodificar o token 
def confirm_token(token, expiration=3600): # 1 hora
    # tenta descriptografar o token usando a mesma SECRET KEY e salt usados na criação
    try:
        email = s.loads(
            token,
            salt='email-confirm-salt',
            max_age=expiration
        )
    except SignatureExpired:
        return 'expired' # Token expirou
    except BadTimeSignature:
        return 'invalid' # Token inválido ou alterado
    return email


