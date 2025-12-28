from flask import url_for
from trip import s, mail
from flask_mail import Message
from itsdangerous import BadTimeSignature, SignatureExpired

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


# recebe o email do novo usuário e usa a biblioteca itsdangerous para criptografar o email
# 'salt' garante que o token seja exclusivo para essa finalidade
def generate_confirmation_token(email):
    return s.dumps(email, salt='email-confirm-salt')


# essa função usa o servidor SMTP configurado (Google Workspace) p; enviar mensagem formatada para a caixa de entrada do usuário
def send_confirmation_email(user_email):
    # o token é usado para construir o link completo de confirmação
    token = generate_confirmation_token(user_email)
    
    # Aponta para a nova rota 
    confirm_url = url_for('confirm_email', token=token, _external=True)
    
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


