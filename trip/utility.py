from flask import url_for
from trip import s, mail
from flask_mail import Message
from itsdangerous import BadTimeSignature, SignatureExpired

def calcular_percentual_e_cor(viagens):
    """
    Recebe uma lista de objetos Viagem e retorna uma lista de dicionários:
    { "viagem": Viagem, "percentual_gasto": float, "cor": str }
    """
    resultado = []
    for viagem in viagens:
        # Usa valor_restante se existir, senão assume valor_total
        valor_restante = viagem.valor_restante if viagem.valor_restante is not None else viagem.valor_total

        if viagem.valor_total and valor_restante is not None:
            percentual_gasto = ((viagem.valor_total - valor_restante) / viagem.valor_total) * 100
            percentual_gasto = max(0, min(percentual_gasto, 100)) # garante entre 0 e 100
        else:
            percentual_gasto = 0

        # Define a cor da barra com base no percentual
        if percentual_gasto <= 50:
            cor = 'bg-success' # verde
        elif percentual_gasto <= 80:
            cor = 'bg-warning' # amarelo
        else:
            cor = 'bg-danger'  # vermelho

        resultado.append({"viagem": viagem, "percentual_gasto": percentual_gasto, "cor": cor})

    return resultado 


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


