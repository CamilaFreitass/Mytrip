from flask import render_template, redirect, url_for, request, flash, abort
from trip import app, database, bcrypt, google, mail, s
from trip.forms import FormCriarConta, FormLogin, FormEditarPerfil, FormCriarViagem, FormCriarAtividade
from trip.models import Viajante, Viagem, Atividade
from flask_login import login_user, logout_user, current_user, login_required
import secrets 
import os
from PIL import Image
from flask_mail import Message
from itsdangerous import BadTimeSignature, SignatureExpired


@app.route('/', methods=["GET", "POST"])
def home():
    return render_template("home.html")


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


@app.route('/viagem/<int:id_viagem>', methods=["GET", "POST"])
@login_required
def viagem_detalhe(id_viagem):
    # Busca a viagem pelo id
    viagem = Viagem.query.get_or_404(id_viagem)

    viagens = [viagem]

    # Calcula o percentual e cor das barras usando a função auxiliar
    viagens_com_percentual = calcular_percentual_e_cor(viagens)

    # Verifica se a viagem pertence ao usuário logado
    if viagem.id_viajante != current_user.id:
        abort(403)  # Proíbe acesso a viagens de outros usuários

    form_atividade = FormCriarAtividade()

    if form_atividade.validate_on_submit():
        nova_atividade = Atividade(
            nome_atividade=form_atividade.nome_atividade.data,
            valor_atividade=form_atividade.valor_atividade.data,
            id_viagem=viagem.id
        )
        database.session.add(nova_atividade)

        # atualiza o valor restante da viagem
        viagem.atualizar_valor_restante()

        database.session.commit()
        flash('Atividade adicionada com sucesso!', 'alert-success')
        return redirect(url_for('viagem_detalhe', id_viagem=id_viagem))

    return render_template('viagem_detalhe.html', viagem=viagem, form_atividade=form_atividade, viagens_com_percentual=viagens_com_percentual)


@app.route('/excluir_atividade/<int:id_atividade>', methods=["GET", "POST"])
@login_required
def excluir_atividade(id_atividade):
    atividade = Atividade.query.get(id_atividade)
    viagem = Viagem.query.get(atividade.id_viagem)
    if current_user == atividade.viagem.viajante:
        database.session.delete(atividade)
        viagem.atualizar_valor_restante()
        database.session.commit()
        flash('Atividade excluida com sucesso!', 'alert-success')
        return redirect(url_for('viagem_detalhe', id_viagem=viagem.id))
    else:
        flash('Erro ao excluir atividade!')
        return redirect(url_for('viagem_detalhe', id_viagem=viagem.id))



# O conversor '<int:id_atividade>' transforma o segmento da URL em 'int' e passa como armento para a função
@app.route('/atividade/<int:id_atividade>', methods=["GET", "POST"])
@login_required
# função view que recebe o id_atividade (inteiro) vindo da URL
def atividade_detalhe(id_atividade):
    # busca a atividade pelo id que a função recebeu (id_atividade) ou retorna 404 se não existir
    atividade = Atividade.query.get_or_404(id_atividade)
    # apartir de 'atividade.id_viagem' busca o objeto viagem
    viagem = Viagem.query.get_or_404(atividade.id_viagem)
    # instancia o form
    form = FormCriarAtividade()
    # se for requisição GET, pré-preenche os campos do form com os valores atuais
    if request.method == 'GET':
        form.nome_atividade.data = atividade.nome_atividade
        form.valor_atividade.data = atividade.valor_atividade
    # se não for GET e o form validou (POST com dados válidos)
    elif form.validate_on_submit():
        atividade.nome_atividade = form.nome_atividade.data
        atividade.valor_atividade = form.valor_atividade.data
        try:
            # chama método da viagem para recalcular/atualizar o valor restante
            viagem.atualizar_valor_restante()
            database.session.commit()
            flash('Atividade editada com sucesso!', 'alert-success')
            return redirect(url_for('viagem_detalhe', id_viagem=viagem.id))
        except Exception:
            database.session.rollback()
            flash('Erro ao editar atividade!', 'alert-danger')
            return redirect(url_for('atividade_detalhe', id_atividade=id_atividade))
    return render_template('atividade_detalhe.html', atividade=atividade, form=form, viagem=viagem)


def generate_confirmation_token(email):
    return s.dumps(email, salt='email-confirm-salt')


def send_confirmation_email(user_email):
    token = generate_confirmation_token(user_email)
    
    # Aponta para a nova rota que você criará (passo 3)
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
    # A linha abaixo deve ser executada de forma assíncrona em produção (opcional)
    mail.send(msg)


# Função para decodificar o token (coloque no seu app.py)
def confirm_token(token, expiration=3600): # 1 hora
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


@app.route('/confirm/<token>')
def confirm_email(token):
    email_ou_status = confirm_token(token)

    if email_ou_status == 'expired':
        flash('O link de confirmação expirou. Por favor, tente logar para receber um novo link.', 'alert-danger')
        return redirect(url_for('acesso'))
    
    if email_ou_status == 'invalid':
        flash('O link de confirmação é inválido.', 'alert-danger')
        return redirect(url_for('acesso'))

    # Se a decodificação foi bem-sucedida, temos o e-mail
    email = email_ou_status
    
    viajante = Viajante.query.filter_by(email=email).first()

    if viajante:
        if viajante.is_verified:
            flash('Sua conta já está ativada. Faça o login.', 'alert-success')
        else:
            # 1. Atualizar o status
            viajante.is_verified = True
            database.session.commit()
            
            # 2. Fazer o login imediatamente (opcional, mas conveniente)
            login_user(viajante) 

            flash('Parabéns! Sua conta foi ativada com sucesso!', 'alert-success')
            return redirect(url_for('perfil'))
    else:
        # Caso o e-mail no token não corresponda a nenhum usuário
        flash('Erro: Usuário não encontrado para este link de confirmação.', 'alert-danger')
        
    return redirect(url_for('acesso'))


@app.route('/acesso', methods=["GET", "POST"])
def acesso():
    form_login = FormLogin()
    form_criarconta = FormCriarConta()

    # Processar login com formulário tradicional
    if form_login.validate_on_submit() and 'submit_login' in request.form:
        viajante = Viajante.query.filter_by(email=form_login.email.data).first()
        if viajante and bcrypt.check_password_hash(viajante.senha, form_login.senha.data):

            # NOVO: Checagem de verificação de e-mail
            if not viajante.is_verified:
                flash('Sua conta ainda não foi ativada. Verifique seu e-mail para o link de confirmação.', 'alert-warning')
                return redirect(url_for('acesso'))

            login_user(viajante, remember=form_login.lembrar_dados.data)
            flash(f'Login feito com sucesso no e-mail: {form_login.email.data}', 'alert-success')
            par_next = request.args.get('next')
            if par_next:
                return redirect(par_next)
            else:
                return redirect(url_for('perfil'))
        else:
            flash(f'Falha no Login. E-mail ou Senha Incorretos', 'alert-danger')

    # Processar criação de conta
    if form_criarconta.validate_on_submit() and 'submit_criar_conta' in request.form:
        senha_cript = bcrypt.generate_password_hash(form_criarconta.senha.data)

        viajante = Viajante(
            nome=form_criarconta.nome.data, 
            email=form_criarconta.email.data, 
            senha=senha_cript,
            is_verified=False # O usuário é criado como NÃO verificado
            )

        database.session.add(viajante)
        database.session.commit()

        # Enviar o e-mail de confirmação
        send_confirmation_email(viajante.email)

        # Alerta o usuário para verificar o e-mail, NÃO faz login
        flash(f"Conta criada com sucesso! Enviamos um link de ativação para {viajante.email}. Por favor, verifique sua caixa de entrada.", "alert-info")
        return redirect(url_for('acesso')) # Redireciona para a mesma página de acesso/login
    
    # Processar login com Google
    if 'google_login' in request.args:  # Verifica se foi chamado o login do Google
        redirect_uri = url_for('auth', _external=True)
        return google.authorize_redirect(redirect_uri)

    return render_template('acesso.html', form_login=form_login, form_criarconta=form_criarconta)


@app.route('/auth')
def auth():
    try:
        print("Tentando obter token...")
        token = google.authorize_access_token()

        if not token:
            flash('Falha ao obter o token do Google.', 'alert-danger')
            print("Token não obtido.")
            return redirect(url_for('acesso'))

        print("Tentando obter informações do usuário...")
        resp = google.get('userinfo')
        if resp.status_code != 200:
            flash('Falha ao obter informações do usuário do Google.', 'alert-danger')
            print("Erro ao obter informações do usuário:", resp.status_code)
            return redirect(url_for('acesso'))

        # obtem as informações do usuário
        user_info = resp.json()

        if 'email' not in user_info:
            flash('Email não encontrado nas informações do usuário.', 'alert-danger')
            print("Email não encontrado nas informações do usuário.")
            return redirect(url_for('acesso'))

        # Verifica se o usuário já existe no banco de dados
        viajante = Viajante.query.filter_by(email=user_info['email']).first()
        if not viajante:
            # Cria um novo visitante se não existir
            viajante = Viajante(
                nome=user_info.get('name'),
                email=user_info['email'],
                senha=None
            )
            database.session.add(viajante)
            database.session.commit()

        login_user(viajante)
        flash('Login com Google realizado com sucesso!', 'alert-success')
        return redirect(url_for('perfil'))

    except Exception as e:
        print(f'Ocorreu um erro: {str(e)}')  # Mostra o erro no console
        flash(f'Ocorreu um erro: {str(e)}', 'alert-danger')
        return redirect(url_for('acesso'))


@app.route('/sair')
@login_required
def sair():
    logout_user()
    flash(f'Logout Feito com Sucesso!', 'alert-success')
    return redirect(url_for('acesso'))


@app.route('/perfil')
@login_required
def perfil():
    form = FormEditarPerfil()

    #preenche o form com os dados atuais do usuário
    form.email.data = current_user.email
    form.nome.data = current_user.nome

    # Conta quantas viagens o usuário tem
    qtd_viagens = Viagem.query.filter_by(id_viajante=current_user.id).count()

    # Mostra todas as viagens do usuário
    viagens_usuario = Viagem.query.filter_by(id_viajante=current_user.id).all()

    # Calcula o percentual e cor das barras usando a função auxiliar
    viagens_com_percentual = calcular_percentual_e_cor(viagens_usuario)

    return render_template(
        'perfil.html',  
        form=form, 
        qtd_viagens=qtd_viagens, 
        viagens_usuario=viagens_usuario,
        viagens_com_percentual=viagens_com_percentual
        )


@app.route('/viagem/criar', methods=['GET', 'POST'])
@login_required
def criar_viagem():
    form = FormCriarViagem()
    if form.validate_on_submit(): 
        nova_viagem = Viagem(
            destino=form.destino.data,
            valor_total=form.valor_total.data,
            id_viajante=current_user.id
            )
        database.session.add(nova_viagem)
        database.session.commit()
        flash('Viagem criada com sucesso', 'alert-success')
        return redirect(url_for('perfil'))
    return render_template('criar_viagem.html', form=form)


def salvar_imagem(imagem):
    # adicionar um código aleatorio no nome da imagem
    codigo = secrets.token_hex(8)
    nome, extensao = os.path.splitext(imagem.filename)
    nome_arquivo = nome + codigo + extensao
    caminho_completo = os.path.join(app.root_path, 'static/fotos_perfil', nome_arquivo)

    # reduzir o tamanho da imagem
    tamanho = (200, 200)
    imagem_reduzida = Image.open(imagem)
    imagem_reduzida.thumbnail(tamanho)

    # salvar a imagem na pasta fotos_perfil
    imagem_reduzida.save(caminho_completo)

    return nome_arquivo

@app.route('/perfil/editar', methods=['POST'])
@login_required
def editar_perfil():
    form = FormEditarPerfil()

    if form.validate_on_submit():
        current_user.email = form.email.data
        current_user.nome = form.nome.data
        if form.foto_perfil.data:
            # mudar o campo foto_perfil do usuario para o novo nome da imagem
            nome_imagem = salvar_imagem(form.foto_perfil.data)
            current_user.foto_perfil = nome_imagem
        database.session.commit()
        flash('Perfil atualizado com sucesso!', 'alert-success')
        return redirect(url_for('perfil'))
    
    else:
        flash('Erro ao atualizar o perfil. Verifique os dados.', 'alert-danger')
    return redirect(url_for('perfil'))
    
    
    