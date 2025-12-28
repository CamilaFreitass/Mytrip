from flask import render_template, redirect, url_for, request, flash, abort
from trip import app, bcrypt, google
from trip.forms import FormCriarConta, FormLogin, FormCriarViagem, FormCriarAtividade
from trip.models import Viajante, Viagem, Atividade
from flask_login import login_user, logout_user, current_user, login_required
from trip.utility import calcular_percentual_e_cor, confirm_token, send_confirmation_email
from .firestore_service import (
    get_viagem_ref,
    get_atividades_ref,
    atualizar_valor_restante,
    criar_atividade, 
    buscar_viagem_por_id,
    deletar_atividade,
    atualizar_viagem,
    deletar_viagem_completa,
    buscar_atividade_por_id,
    atualizar_atividade,
    buscar_viajante_por_email,
    atualizar_status_verificacao,
    criar_viajante,
    criar_nova_viagem,
    listar_viagens_por_viajante)

@app.route('/', methods=["GET", "POST"])
def home():
    return render_template("home.html")


# @app.route('/viagem/<string:id_viagem>', methods=["GET", "POST"])
# @login_required
# def viagem_detalhe(id_viagem):
#     # ATENÇÃO: Mudamos o tipo de 'id_viagem' para <string:id_viagem>

#     # 1. BUSCAR A VIAGEM
#     # Acessa o Documento Viagem no Firestore
#     # Você precisará de uma nova função no firestore_service.py: buscar_viagem_por_id
    
#     viagem_data = buscar_viagem_por_id(current_user.get_id(), id_viagem)
    
#     if not viagem_data:
#          abort(404)

#     # 2. VERIFICAÇÃO DE PERMISSÃO E MAPPER
#     # A permissão é verificada na busca (pois a Viagem está aninhada ao Viajante)
#     # Mas se a viagem não for aninhada, você faria:
#     # if viagem_data['id_viajante'] != current_user.get_id():
#     #     abort(403) 
    
#     # Mapeia os dados do dicionário do Firestore para a classe Viagem
#     viagem = viagem_data
    
#     # 3. CONFIGURAÇÃO DE RENDER
#     # O calculo precisa receber a lista de objetos Viagem (ou dicionários com dados)
#     viagens_com_percentual = calcular_percentual_e_cor([viagem_data]) # Passa a lista de dicionários
#     viagem_percentual = viagens_com_percentual[0] # Pega o resultado para usar no template

#     form_atividade = FormCriarAtividade()

#     if form_atividade.validate_on_submit():
        
#         # 4. CRIAR NOVA ATIVIDADE NO FIRESTORE
#         dados_nova_atividade = {
#             'nome_atividade': form_atividade.nome_atividade.data,
#             'valor_atividade': form_atividade.valor_atividade.data,
#             'id_viagem': id_viagem, # Referência ID, mas no Firestore ela será uma subcoleção
#             # Você pode incluir outros campos como data de criação, se necessário
#         }
        
#         # Você precisará de uma nova função no firestore_service.py: criar_atividade
#         criar_atividade(current_user.get_id(), id_viagem, dados_nova_atividade)

#         # 5. ATUALIZAR VALOR RESTANTE (Lógica NoSQL)
#         # Chamamos a função de serviço para recalcular e atualizar o documento pai (Viagem)
#         try:
#              atualizar_valor_restante(current_user.get_id(), id_viagem)
#              flash('Atividade adicionada com sucesso!', 'alert-success')
#              return redirect(url_for('viagem_detalhe', id_viagem=id_viagem))
#         except Exception as e:
#              # Lidar com erros de DB ou NotFound
#              flash(f'Erro ao salvar ou atualizar: {e}', 'alert-danger')
#              app.logger.error(f"Erro ao atualizar valor: {e}")
#              return redirect(url_for('viagem_detalhe', id_viagem=id_viagem))


    # return render_template('viagem_detalhe.html', viagem=viagem, form_atividade=form_atividade, viagens_com_percentual=viagens_com_percentual) 


@app.route('/viagem/<string:id_viagem>', methods=["GET", "POST"])
@login_required
def viagem_detalhe(id_viagem):
    viajante_id = current_user.get_id()

    # 1. Busca os dados crus do Firestore (Dicionário)
    viagem_raw = buscar_viagem_por_id(viajante_id, id_viagem)
    
    if not viagem_raw:
        abort(404)

    # 2. CONVERTE PARA OBJETO (Model)
    # Isso garante que se 'valor_total' não existir no banco, 
    # o objeto terá o valor 0 em vez de quebrar o site.
    viagem = Viagem(viagem_raw)

    # 3. CALCULA PERCENTUAL E COR
    # Passamos a lista contendo o nosso objeto
    viagens_formatadas = calcular_percentual_e_cor([viagem])
    # Pegamos o objeto de volta, agora com os atributos 'percentual' e 'cor' injetados
    viagem_pronta = viagens_formatadas[0]

    form_atividade = FormCriarAtividade()

    if form_atividade.validate_on_submit():
        # ... (lógica de criar atividade permanece igual) ...
        dados_nova_atividade = {
            'nome_atividade': form_atividade.nome_atividade.data,
            'valor_atividade': float(form_atividade.valor_atividade.data),
            'id_viagem': id_viagem
        }
        criar_atividade(viajante_id, id_viagem, dados_nova_atividade)
        atualizar_valor_restante(viajante_id, id_viagem)
        
        flash('Atividade adicionada!', 'alert-success')
        return redirect(url_for('viagem_detalhe', id_viagem=id_viagem))

    # ENVIAMOS 'viagem_pronta' que é o OBJETO com todos os campos
    return render_template('viagem_detalhe.html', 
                           viagem=viagem_pronta, 
                           form_atividade=form_atividade)


@app.route('/viagem/<string:id_viagem>/editar', methods=['GET', 'POST'])
@login_required
def editar_viagem(id_viagem):
    # 1. Busca os dados brutos (dicionário) do Firestore
    viajante_id = current_user.get_id()
    viagem_data = buscar_viagem_por_id(viajante_id, id_viagem)

    if not viagem_data:
        abort(404)

    # 2. Transforma em um objeto da classe Viagem (do seu models.py)
    # Isso permite que o WTForms preencha o formulário automaticamente com 'obj=viagem'
    viagem_objeto = Viagem(viagem_data)

    # Preenche o formulário com os dados atuais do objeto
    form = FormCriarViagem(obj=viagem_objeto)

    if form.validate_on_submit():
        # 3. Prepara os novos dados para salvar
        novos_dados = {
            'destino': form.destino.data,
            'valor_total': form.valor_total.data
        }

        # 4. Salva no Firestore
        atualizar_viagem(viajante_id, id_viagem, novos_dados)

        # 5. RECALCULO: Como o valor_total pode ter mudado, 
        # atualizamos o valor_restante baseado nas atividades existentes
        atualizar_valor_restante(viajante_id, id_viagem)

        flash('Viagem atualizada com sucesso!', 'alert-success')
        return redirect(url_for('viagem_detalhe', id_viagem=id_viagem))

    return render_template('criar_viagem.html', form=form, modo='editar', viagem=viagem_objeto)


@app.route('/deletar_viagem/<string:viagem_id>', methods=['POST'])
@login_required
def deletar_viagem(viagem_id):
    viajante_id = current_user.get_id()
    
    # 1. Tenta buscar a viagem para verificar se ela existe
    viagem_data = buscar_viagem_por_id(viajante_id, viagem_id)

    if not viagem_data:
        flash('Viagem não encontrada!', 'alert-danger')
        return redirect(url_for('perfil'))

    # 2. Verifica a posse (segurança)
    # Como buscamos usando o viajante_id atual, se retornar dados, ela pertence a ele.
    if viagem_data.get('id_viajante') == viajante_id:
        try:
            # 3. Chama a função de serviço para deletar tudo
            deletar_viagem_completa(viajante_id, viagem_id)
            flash('Viagem excluída com sucesso!', 'alert-success')
            return redirect(url_for('perfil'))
        except Exception as e:
            flash(f'Erro ao excluir a viagem: {e}', 'alert-danger')
            return redirect(url_for('perfil'))
    else:
        # Caso o ID da viagem exista mas pertença a outro usuário
        flash('Você não tem permissão para deletar esta viagem!', 'alert-danger')
        return redirect(url_for('perfil'))


@app.route('/excluir_atividade/<string:id_viagem>/<string:id_atividade>', methods=["POST"])
@login_required
def excluir_atividade(id_viagem, id_atividade):
    viajante_id = current_user.get_id()
    
    # 1. Tentamos deletar a atividade usando nossa função de serviço
    # A função deletar_atividade já verifica a existência internamente
    sucesso = deletar_atividade(viajante_id, id_viagem, id_atividade)

    if sucesso:
        # 2. Após deletar, precisamos atualizar o valor restante da viagem pai
        try:
            atualizar_valor_restante(viajante_id, id_viagem)
            flash('Atividade excluída com sucesso!', 'alert-success')
        except Exception as e:
            app.logger.error(f"Erro ao recalcular valor após exclusão: {e}")
            flash('Atividade excluída, mas houve um erro ao atualizar o saldo da viagem.', 'alert-warning')
    else:
        flash('Erro ao excluir atividade ou atividade não encontrada!', 'alert-danger')

    return redirect(url_for('viagem_detalhe', id_viagem=id_viagem))


@app.route('/viagem/<string:id_viagem>/atividade/<string:id_atividade>', methods=["GET", "POST"])
@login_required
def atividade_detalhe(id_viagem, id_atividade):
    viajante_id = current_user.get_id()
    
    # 1. Busca os dados brutos no Firestore
    viagem_data = buscar_viagem_por_id(viajante_id, id_viagem)
    atividade_data = buscar_atividade_por_id(viajante_id, id_viagem, id_atividade)

    if not viagem_data or not atividade_data:
        abort(404)

    # 2. Mapeia para os objetos das suas classes (Models)
    viagem = Viagem(viagem_data)
    atividade = Atividade(atividade_data)

    form = FormCriarAtividade()

    # 3. Lógica do Formulário
    if request.method == 'GET':
        form.nome_atividade.data = atividade.nome_atividade
        form.valor_atividade.data = atividade.valor_atividade
        
    elif form.validate_on_submit():
        novos_dados = {
            'nome_atividade': form.nome_atividade.data,
            'valor_atividade': form.valor_atividade.data
        }
        
        try:
            # 4. Atualiza a atividade
            atualizar_atividade(viajante_id, id_viagem, id_atividade, novos_dados)
            
            # 5. Recalcula o valor restante da viagem pai
            atualizar_valor_restante(viajante_id, id_viagem)
            
            flash('Atividade editada com sucesso!', 'alert-success')
            return redirect(url_for('viagem_detalhe', id_viagem=id_viagem))
        except Exception as e:
            app.logger.error(f"Erro ao editar atividade: {e}")
            flash('Erro ao editar atividade!', 'alert-danger')
            return redirect(url_for('atividade_detalhe', id_viagem=id_viagem, id_atividade=id_atividade))

    return render_template('atividade_detalhe.html', atividade=atividade, form=form, viagem=viagem)


@app.route('/confirm/<token>')
def confirm_email(token):
    # Usa a sua função existente do utility.py
    email_ou_status = confirm_token(token)

    if email_ou_status == 'expired':
        flash('O link de confirmação expirou. Por favor, tente logar para receber um novo link.', 'alert-danger')
        return redirect(url_for('acesso'))
    
    if email_ou_status == 'invalid':
        flash('O link de confirmação é inválido.', 'alert-danger')
        return redirect(url_for('acesso'))

    # Se chegou aqui, email_ou_status contém o e-mail decodificado
    email = email_ou_status
    
    # 1. Busca os dados do viajante no Firestore
    viajante_data = buscar_viajante_por_email(email)

    if viajante_data:
        # Criamos o objeto Viajante a partir dos dados do Firestore 
        # para que o Flask-Login (login_user) consiga usá-lo.
        viajante = Viajante(viajante_data)

        if viajante.is_verified:
            flash('Sua conta já está ativada. Faça o login.', 'alert-success')
        else:
            # 2. Atualiza o status no Firestore usando o serviço
            atualizar_status_verificacao(email, True)
            
            # Atualizamos o atributo no objeto local para refletir a mudança imediata
            viajante.is_verified = True
            
            # 3. Loga o usuário (O Flask-Login usa o objeto Viajante que criamos acima)
            login_user(viajante) 

            flash('Parabéns! Sua conta foi ativada com sucesso!', 'alert-success')
            return redirect(url_for('perfil'))
    else:
        flash('Erro: Usuário não encontrado para este link de confirmação.', 'alert-danger')
        
    return redirect(url_for('acesso'))


@app.route('/acesso', methods=["GET", "POST"])
def acesso():
    form_login = FormLogin()
    form_criarconta = FormCriarConta()

    # --- 1. PROCESSAR LOGIN ---
    if form_login.validate_on_submit() and 'submit_login' in request.form:
        # Busca os dados brutos no Firestore pelo email
        viajante_data = buscar_viajante_por_email(form_login.email.data)
        
        if viajante_data:
            # Transforma o dicionário em um objeto Viajante para o Flask-Login
            viajante = Viajante(viajante_data)
            
            # Verifica a senha usando o hash armazenado no Firestore
            if bcrypt.check_password_hash(viajante.senha, form_login.senha.data):
                
                # Checagem de verificação de e-mail
                if not viajante.is_verified:
                    flash('Sua conta ainda não foi ativada. Verifique seu e-mail para o link de confirmação.', 'alert-warning')
                    return redirect(url_for('acesso'))

                # Realiza o login (viajante agora é um objeto válido para o UserMixin)
                login_user(viajante, remember=form_login.lembrar_dados.data)
                flash(f'Login feito com sucesso!', 'alert-success')
                
                par_next = request.args.get('next')
                return redirect(par_next) if par_next else redirect(url_for('perfil'))
        
        # Se não cair no if acima, o login falhou
        flash(f'Falha no Login. E-mail ou Senha Incorretos', 'alert-danger')

    # --- 2. PROCESSAR CRIAÇÃO DE CONTA ---
    if form_criarconta.validate_on_submit() and 'submit_criar_conta' in request.form:
        # Criptografa a senha (convertendo para string utf-8 para salvar no Firestore)
        senha_cript = bcrypt.generate_password_hash(form_criarconta.senha.data).decode('utf-8')

        # Prepara o dicionário de dados
        dados_viajante = {
            'nome': form_criarconta.nome.data, 
            'email': form_criarconta.email.data, 
            'senha': senha_cript,
            'is_verified': False # Começa desativado
        }

        # Salva no Firestore usando o serviço (o email será o ID do documento)
        criar_viajante(dados_viajante)

        # Enviar o e-mail de confirmação usando sua função do utility.py
        send_confirmation_email(dados_viajante['email'])

        flash(f"Conta criada com sucesso! Enviamos um link de ativação para {dados_viajante['email']}.", "alert-info")
        return redirect(url_for('acesso')) 
    
    # --- 3. LOGIN COM GOOGLE ---
    if 'google_login' in request.args:
        redirect_uri = url_for('auth', _external=True)
        return google.authorize_redirect(redirect_uri)

    return render_template('acesso.html', form_login=form_login, form_criarconta=form_criarconta)


# rota de autenticação do login do google
@app.route('/auth')
def auth():
    try:
        token = google.authorize_access_token()

        if not token:
            flash('Falha ao obter o token do Google.', 'alert-danger')
            return redirect(url_for('acesso'))

        resp = google.get('userinfo')
        if resp.status_code != 200:
            flash('Falha ao obter informações do usuário do Google.', 'alert-danger')
            return redirect(url_for('acesso'))

        user_info = resp.json()
        email = user_info.get('email')

        if not email:
            flash('Email não encontrado nas informações do usuário.', 'alert-danger')
            return redirect(url_for('acesso'))

        # 1. Busca se o viajante já existe no Firestore
        viajante_data = buscar_viajante_por_email(email)
        
        if not viajante_data:
            # 2. Se não existir, cria um novo no Firestore
            # Usuários do Google já chegam como verificados (is_verified=True)
            novo_viajante_dict = {
                'nome': user_info.get('name'),
                'email': email,
                'senha': None, # Não há senha para login social
                'is_verified': True 
            }
            criar_viajante(novo_viajante_dict)
            
            # Recarrega os dados para ter o dicionário completo (incluindo o doc_id)
            viajante_data = buscar_viajante_por_email(email)

        # 3. Transforma o dicionário em Objeto para o Flask-Login
        viajante = Viajante(viajante_data)

        # 4. Realiza o login
        login_user(viajante)
        flash('Login com Google realizado com sucesso!', 'alert-success')
        return redirect(url_for('perfil'))

    except Exception as e:
        app.logger.error(f"Erro no OAuth Google: {str(e)}")
        flash(f'Ocorreu um erro na autenticação: {str(e)}', 'alert-danger')
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
    viajante_id = current_user.get_id()

    # 1. Busca as viagens no Firestore (retorna lista de dicionários)
    viagens_data = listar_viagens_por_viajante(viajante_id)

    # 2. Converte os dicionários em objetos Viagem (Models)
    # Isso garante compatibilidade com a função calcular_percentual_e_cor
    viagens_usuario = [Viagem(dados) for dados in viagens_data]

    # 3. Conta a quantidade de viagens
    qtd_viagens = len(viagens_usuario)

    # 4. Calcula o percentual e cor (a função utility permanece a mesma)
    viagens_com_percentual = calcular_percentual_e_cor(viagens_usuario)

    return render_template(
        'perfil.html',
        qtd_viagens=qtd_viagens, 
        viagens_usuario=viagens_usuario,
        viagens_com_percentual=viagens_com_percentual
    )


@app.route('/viagem/criar', methods=['GET', 'POST'])
@login_required
def criar_viagem():
    form = FormCriarViagem()
    
    if form.validate_on_submit(): 
        viajante_id = current_user.get_id() # Obtém o email/ID do usuário logado
        
        # Preparamos o dicionário de dados
        nova_viagem_dados = {
            'destino': form.destino.data,
            'valor_total': form.valor_total.data,
            'valor_restante': form.valor_total.data, # Inicialmente sobra tudo
            'id_viajante': viajante_id
        }
        
        # Salvamos no Firestore
        criar_nova_viagem(viajante_id, nova_viagem_dados)
        
        flash('Viagem criada com sucesso!', 'alert-success')
        return redirect(url_for('perfil'))
        
    return render_template('criar_viagem.html', form=form, modo='criar')
    
    
    