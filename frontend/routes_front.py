import requests
from flask import render_template, redirect, url_for, flash, request
from flask_login import login_required, login_user, logout_user, current_user
from __init__ import app
from forms import FormCriarAtividade, FormCriarViagem, FormLogin, FormCriarConta
from models import Viagem, Atividade, Viajante
import os


BACKEND_URL = os.getenv('BACKEND_URL', 'http://127.0.0.1:5000')


@app.context_processor
def inject_backend_url():
    return dict(BACKEND_URL=BACKEND_URL)

@app.route('/')
def home():
    return render_template("home.html")


@app.route('/viagem/<id_viagem>', methods=["GET", "POST"])
@login_required
def viagem_detalhe(id_viagem):
    form_atividade = FormCriarAtividade()

    if form_atividade.validate_on_submit():
        dados_envio = {
            "nome_atividade": form_atividade.nome_atividade.data,
            "valor_atividade": float(form_atividade.valor_atividade.data)
        }
        headers = {'X-Viajante-ID': current_user.get_id()}
        post_response = requests.post(f"{BACKEND_URL}/api/viagem/{id_viagem}/atividade", json=dados_envio, headers=headers)

        if post_response.status_code == 201:
            flash('Atividade adicionada!', 'alert-success')
        else:
            flash('Erro ao adicionar atividade no servidor.', 'alert-danger')

        return redirect(url_for('viagem_detalhe', id_viagem=id_viagem))

    headers = {'X-Viajante-ID': current_user.get_id()}
    response = requests.get(f"{BACKEND_URL}/api/viagem/{id_viagem}", headers=headers)
    if response.status_code == 200:
        viagem_data = response.json()
        if 'doc_id' not in viagem_data:
            viagem_data['doc_id'] = id_viagem
        convites_viagem = []
        try:
            conv_resp = requests.get(f"{BACKEND_URL}/api/viagem/{id_viagem}/convites", headers=headers)
            if conv_resp.status_code == 200:
                convites_viagem = conv_resp.json().get("convites", [])
        except requests.exceptions.RequestException:
            convites_viagem = []

        return render_template(
            'viagem_detalhe.html',
            viagem=viagem_data,
            form_atividade=form_atividade,
            compartilhada=False,
            convites_viagem=convites_viagem
        )

    flash("Erro ao buscar detalhes da viagem ou acesso negado.", "alert-danger")
    return redirect(url_for('home'))


@app.route('/viagem/<id_viagem>/editar', methods=['GET', 'POST'])
@login_required
def editar_viagem(id_viagem):
    # 1. Busca os dados atuais da API para preencher o formulário
    headers = {'X-Viajante-ID': current_user.get_id()}
    response = requests.get(f"{BACKEND_URL}/api/viagem/{id_viagem}/editar", headers=headers)
    if response.status_code != 200:
        flash("Erro ao carregar dados da viagem.", "alert-danger")
        return redirect(url_for('home'))

    viagem_dados = response.json()
    viagem_objeto = Viagem(viagem_dados)

    # Preenche o formulário com o objeto vindo da API
    form = FormCriarViagem(obj=viagem_objeto)

    if form.validate_on_submit():
        novos_dados = {
            'destino': form.destino.data,
            'valor_total': form.valor_total.data
        }

        # 2. Envia os novos dados para a API via PUT
        update_resp = requests.put(
            f"{BACKEND_URL}/api/viagem/{id_viagem}/editar",
                json=novos_dados,
                headers=headers)

        if update_resp.status_code == 200:
            flash('Viagem atualizada com sucesso!', 'alert-success')
            return redirect(url_for('viagem_detalhe', id_viagem=id_viagem))
        else:
            flash('Erro ao salvar alterações no servidor.', 'alert-danger')

    # 'modo' serve para o template decidir se o título é "Criar" ou "Editar"
    return render_template('criar_viagem.html', form=form, modo='editar', viagem=viagem_objeto)


@app.route('/deletar_viagem/<string:viagem_id>', methods=['POST'])
@login_required
def deletar_viagem(viagem_id):
    # O Frontend solicita a exclusão para a API usando o método DELETE
    headers = {'X-Viajante-ID': current_user.get_id()}
    response = requests.delete(f"{BACKEND_URL}/api/viagem/{viagem_id}", headers=headers)

    if response.status_code == 200:
        flash('Viagem excluída com sucesso!', 'alert-success')
    elif response.status_code == 403:
        flash('Você não tem permissão para deletar esta viagem!', 'alert-danger')
    else:
        flash('Erro ao excluir a viagem. Tente novamente.', 'alert-danger')

    return redirect(url_for('perfil'))


@app.route('/excluir_atividade/<string:id_viagem>/<string:id_atividade>', methods=["POST"])
@login_required
def excluir_atividade(id_viagem, id_atividade):
    # O Frontend pede para a API deletar o recurso
    headers = {'X-Viajante-ID': current_user.get_id()}

    delete_url = f"{BACKEND_URL}/api/viagem/{id_viagem}/atividade/{id_atividade}"
    print(f"DEBUG: Tentando DELETE na URL: {delete_url}")
    print(f"DEBUG: IDs - Viagem: {id_viagem}, Atividade: {id_atividade}, Viajante: {headers['X-Viajante-ID']}")

    response = requests.delete(f"{BACKEND_URL}/api/viagem/{id_viagem}/atividade/{id_atividade}", headers=headers)

    print(f"DEBUG: DELETE status: {response.status_code}, resposta: {response.text}")

    if response.status_code == 200:
        flash('Atividade excluída com sucesso!', 'alert-success')
    elif response.status_code == 206:
        flash('Atividade excluída, mas o saldo da viagem pode estar desatualizado.', 'alert-warning')
    else:
        try:
            erro_msg = response.json().get('erro', 'Erro desconhecido')
        except:
            erro_msg = 'Resposta inválida do servidor'
        flash(f'Erro ao excluir atividade: {erro_msg} (Status: {response.status_code})', 'alert-danger')

    return redirect(url_for('viagem_detalhe', id_viagem=id_viagem))


@app.route('/viagem/<string:id_viagem>/atividade/<string:id_atividade>', methods=["GET", "POST"])
@login_required
def atividade_detalhe(id_viagem, id_atividade):
    # 1. Busca os dados atuais na API
    headers = {'X-Viajante-ID': current_user.get_id()}
    response = requests.get(f"{BACKEND_URL}/api/viagem/{id_viagem}/atividade/{id_atividade}", headers=headers)

    if response.status_code != 200:
        flash("Erro ao carregar dados da atividade.", "alert-danger")
        return redirect(url_for('viagem_detalhe', id_viagem=id_viagem))

    dados = response.json()
    viagem = Viagem(dados['viagem'])
    atividade = Atividade(dados['atividade'])

    form = FormCriarAtividade()

    # Preenche o formulário se for um GET ou se o formulário for reiniciado
    if request.method == 'GET':
        form.nome_atividade.data = atividade.nome_atividade
        form.valor_atividade.data = atividade.valor_atividade

    elif form.validate_on_submit():
        novos_dados = {
            'nome_atividade': form.nome_atividade.data,
            'valor_atividade': float(form.valor_atividade.data)
        }

        # 2. Envia a atualização para a API via PUT
        update_resp = requests.put(
        f"{BACKEND_URL}/api/viagem/{id_viagem}/atividade/{id_atividade}",
            json=novos_dados,
            headers=headers
        )

        if update_resp.status_code == 200:
            flash('Atividade editada com sucesso!', 'alert-success')
            return redirect(url_for('viagem_detalhe', id_viagem=id_viagem))
        else:
            flash('Erro ao editar atividade no servidor.', 'alert-danger')

    return render_template('atividade_detalhe.html', atividade=atividade, form=form, viagem=viagem)


@app.route('/confirm/<token>')
def confirm_email(token):
    # O Frontend pede para o Backend validar e ativar a conta
    response = requests.get(f"{BACKEND_URL}/api/confirmar/{token}")

    if response.status_code == 200:
        viajante_dados = response.json()
        viajante = Viajante(viajante_dados)

        # 3. Inicia a sessão no Frontend
        login_user(viajante)

        flash('Parabéns! Sua conta foi ativada com sucesso!', 'alert-success')
        return redirect(url_for('perfil'))

    elif response.status_code == 410:
        flash('O link de confirmação expirou. Tente logar para receber um novo.', 'alert-danger')
    else:
        flash('Link inválido ou usuário não encontrado.', 'alert-danger')

    return redirect(url_for('acesso'))


@app.route('/login/callback')
def login_callback():
    email = request.args.get('email')

    if not email:
        flash("Erro ao processar login social", "alert-danger")
        return redirect(url_for('acesso'))

    try:
        response = requests.get(f"{BACKEND_URL}/api/usuario/{email}")

        if response.status_code == 200:
            viajante_data = response.json()
            user = Viajante(viajante_data)

            login_user(user, remember=True)

            flash("Login realizado com sucesso!", "alert-success")
            return redirect(url_for('perfil'))

        else:
            flash("Usuário autenticado no Google, mas não encontrado no sistema.", "alert-warning")
            return redirect(url_for('acesso'))

    except requests.exceptions.RequestException as e:
        print(f"Erro de conexão com o Backend: {e}")
        flash("Erro ao conectar com o servidor de autenticação.", "alert-danger")
        return redirect(url_for('acesso'))


@app.route('/acesso', methods=["GET", "POST"])
def acesso():
    # Verifica se há erro vindo do redirecionamento do Backend (Google)
    if request.args.get('erro') == 'auth_failed':
        flash("Falha na autenticação com o Google. Tente novamente.", "alert-danger")

    form_login = FormLogin()
    form_criarconta = FormCriarConta()

    # 1. Lógica de Login
    if form_login.validate_on_submit() and 'submit_login' in request.form:
        dados_login = {"email": form_login.email.data, "senha": form_login.senha.data}
        response = requests.post(f"{BACKEND_URL}/api/login", json=dados_login)

        if response.status_code == 200:
            viajante = Viajante(response.json())
            login_user(viajante, remember=form_login.lembrar_dados.data)
            flash('Login feito com sucesso!', 'alert-success')
            return redirect(url_for('perfil'))
        elif response.status_code == 403:
            flash('Verifique seu e-mail para ativar sua conta.', 'alert-warning')
        else:
            flash('E-mail ou Senha Incorretos', 'alert-danger')

    # 2. Lógica de Cadastro
    if form_criarconta.validate_on_submit() and 'submit_criar_conta' in request.form:
        dados_cadastro = {
            "nome": form_criarconta.nome.data,
            "email": form_criarconta.email.data,
            "senha": form_criarconta.senha.data
        }
        response = requests.post(f"{BACKEND_URL}/api/cadastro", json=dados_cadastro)

        if response.status_code == 201:
            flash(f"Conta criada! Ative no e-mail {dados_cadastro['email']}.", "alert-info")
            return redirect(url_for('acesso'))
        else:
            flash("Erro ao criar conta. Tente outro e-mail.", "alert-danger")

    return render_template('acesso.html', form_login=form_login, form_criarconta=form_criarconta)


@app.route('/sair')
@login_required
def sair():
    # 1. Avisa o backend para encerrar a sessão lá (opcional, mas boa prática)
    requests.get(f"{BACKEND_URL}/api/sair")

    # 2. Encerra a sessão no frontend
    logout_user()

    flash('Logout feito com sucesso!', 'alert-success')
    return redirect(url_for('acesso'))


@app.route('/perfil')
@login_required
def perfil():
    # O Frontend pede os dados processados para a API do Backend
    try:
        headers = {'X-Viajante-ID': current_user.get_id()}
        response = requests.get(f"{BACKEND_URL}/api/perfil", headers=headers)

        if response.status_code == 200:
            dados = response.json()
            # No template, você pode usar dados['viagens'] e dados['qtd_viagens']
            return render_template(
                'perfil.html',
                qtd_viagens=dados['qtd_viagens'],
                viagens_com_percentual=dados['viagens']
            )
        else:
            flash("Erro ao carregar perfil.", "alert-danger")
            return redirect(url_for('home'))

    except requests.exceptions.RequestException:
        flash("Servidor de dados indisponível.", "alert-danger")
        return redirect(url_for('home'))


@app.route('/viagem/criar', methods=['GET', 'POST'])
@login_required
def criar_viagem():
    form = FormCriarViagem()

    if form.validate_on_submit():
        # Preparamos os dados para enviar à API
        dados_envio = {
            'destino': form.destino.data,
            'valor_total': form.valor_total.data
        }

        # Enviamos para o Backend com header de autenticação
        headers = {'X-Viajante-ID': current_user.get_id()}
        response = requests.post(f"{BACKEND_URL}/api/viagem/criar", json=dados_envio, headers=headers)

        if response.status_code == 201:
            flash('Viagem criada com sucesso!', 'alert-success')
            return redirect(url_for('perfil'))
        else:
            flash('Erro ao salvar a viagem no servidor.', 'alert-danger')

    # 'modo' serve para o template exibir o título correto
    return render_template('criar_viagem.html', form=form, modo='criar')


@app.route('/viagem-compartilhada/<string:owner_id>/<string:id_viagem>', methods=["GET", "POST"])
@login_required
def viagem_detalhe_compartilhada(owner_id, id_viagem):
    form_atividade = FormCriarAtividade()
    headers = {'X-Viajante-ID': current_user.get_id()}

    if form_atividade.validate_on_submit():
        dados_envio = {
            "nome_atividade": form_atividade.nome_atividade.data,
            "valor_atividade": float(form_atividade.valor_atividade.data)
        }

        post_response = requests.post(
            f"{BACKEND_URL}/api/viagem/{owner_id}/{id_viagem}/atividade",
            json=dados_envio,
            headers=headers
        )

        if post_response.status_code == 201:
            flash('Atividade adicionada!', 'alert-success')
        else:
            try:
                erro_msg = post_response.json().get("erro", "Erro ao adicionar atividade.")
            except Exception:
                erro_msg = "Erro ao adicionar atividade."
            flash(erro_msg, 'alert-danger')

        return redirect(url_for('viagem_detalhe_compartilhada', owner_id=owner_id, id_viagem=id_viagem))

    response = requests.get(
        f"{BACKEND_URL}/api/viagem/{owner_id}/{id_viagem}",
        headers=headers
    )

    if response.status_code == 200:
        viagem_data = response.json()
        viagem_data["doc_id"] = viagem_data.get("doc_id") or id_viagem
        return render_template(
            'viagem_detalhe.html',
            viagem=viagem_data,
            form_atividade=form_atividade,
            compartilhada=True,
            owner_id=owner_id
        )

    try:
        erro_msg = response.json().get("erro", "Acesso negado.")
    except Exception:
        erro_msg = "Acesso negado."
    flash(erro_msg, "alert-danger")
    return redirect(url_for('perfil'))


@app.route('/excluir_atividade_compartilhada/<string:owner_id>/<string:id_viagem>/<string:id_atividade>', methods=["POST"])
@login_required
def excluir_atividade_compartilhada(owner_id, id_viagem, id_atividade):
    headers = {'X-Viajante-ID': current_user.get_id()}

    response = requests.delete(
        f"{BACKEND_URL}/api/viagem/{owner_id}/{id_viagem}/atividade/{id_atividade}",
        headers=headers
    )

    if response.status_code == 200:
        flash('Atividade excluída com sucesso!', 'alert-success')
    elif response.status_code == 206:
        flash('Atividade excluída, mas o saldo da viagem pode estar desatualizado.', 'alert-warning')
    else:
        try:
            erro_msg = response.json().get('erro', 'Erro desconhecido')
        except Exception:
            erro_msg = 'Resposta inválida do servidor'
        flash(f'Erro ao excluir atividade: {erro_msg} (Status: {response.status_code})', 'alert-danger')

    return redirect(url_for('viagem_detalhe_compartilhada', owner_id=owner_id, id_viagem=id_viagem))


@app.route('/viagem-compartilhada/<string:owner_id>/<string:id_viagem>/atividade/<string:id_atividade>', methods=["GET", "POST"])
@login_required
def atividade_detalhe_compartilhada(owner_id, id_viagem, id_atividade):
    headers = {'X-Viajante-ID': current_user.get_id()}

    # 1) Buscar dados atuais (rota compartilhada)
    response = requests.get(
        f"{BACKEND_URL}/api/viagem/{owner_id}/{id_viagem}/atividade/{id_atividade}",
        headers=headers
    )

    if response.status_code != 200:
        flash("Erro ao carregar dados da atividade.", "alert-danger")
        return redirect(url_for('viagem_detalhe_compartilhada', owner_id=owner_id, id_viagem=id_viagem))

    dados = response.json()
    viagem = Viagem(dados['viagem'])
    atividade = Atividade(dados['atividade'])

    form = FormCriarAtividade()

    if request.method == 'GET':
        form.nome_atividade.data = atividade.nome_atividade
        form.valor_atividade.data = atividade.valor_atividade

    elif form.validate_on_submit():
        novos_dados = {
            'nome_atividade': form.nome_atividade.data,
            'valor_atividade': float(form.valor_atividade.data)
        }

        update_resp = requests.put(
            f"{BACKEND_URL}/api/viagem/{owner_id}/{id_viagem}/atividade/{id_atividade}",
            json=novos_dados,
            headers=headers
        )

        if update_resp.status_code == 200:
            flash('Atividade editada com sucesso!', 'alert-success')
            return redirect(url_for('viagem_detalhe_compartilhada', owner_id=owner_id, id_viagem=id_viagem))
        else:
            flash('Erro ao editar atividade no servidor.', 'alert-danger')

    return render_template(
        'atividade_detalhe.html',
        atividade=atividade,
        form=form,
        viagem=viagem,
        compartilhada=True,
        owner_id=owner_id
    )


@app.route('/viagem/<string:id_viagem>/convidar', methods=["POST"])
@login_required
def convidar_viajante(id_viagem):
    email_convidado = (request.form.get("email_convidado") or "").strip().lower()
    if not email_convidado:
        flash("Informe o e-mail do viajante para enviar o convite.", "alert-warning")
        return redirect(url_for('viagem_detalhe', id_viagem=id_viagem))

    headers = {'X-Viajante-ID': current_user.get_id()}

    try:
        resp = requests.post(
            f"{BACKEND_URL}/api/viagem/{id_viagem}/convites",
            json={"email_convidado": email_convidado},
            headers=headers
        )
    except requests.exceptions.RequestException:
        flash("Servidor indisponível no momento. Tente novamente.", "alert-danger")
        return redirect(url_for('viagem_detalhe', id_viagem=id_viagem))

    if resp.status_code == 201:
        flash("Convite enviado com sucesso!", "alert-success")
    else:
        try:
            erro_msg = resp.json().get("erro", "Erro desconhecido")
        except Exception:
            erro_msg = "Resposta inválida do servidor"
        flash(f"Não foi possível enviar o convite: {erro_msg}", "alert-danger")

    return redirect(url_for('viagem_detalhe', id_viagem=id_viagem))


@app.route('/convites', methods=["GET"])
@login_required
def convites():
    headers = {'X-Viajante-ID': current_user.get_id()}

    try:
        pendentes_resp = requests.get(f"{BACKEND_URL}/api/convites?status=pendente", headers=headers)
        revogados_resp = requests.get(f"{BACKEND_URL}/api/convites?status=revogado", headers=headers)
    except requests.exceptions.RequestException:
        flash("Servidor indisponível no momento. Tente novamente.", "alert-danger")
        return redirect(url_for('perfil'))

    if pendentes_resp.status_code != 200:
        flash("Erro ao carregar convites pendentes.", "alert-danger")
        return redirect(url_for('perfil'))

    convites_pendentes = (pendentes_resp.json() or {}).get("convites", [])

    convites_revogados = []
    if revogados_resp.status_code == 200:
        convites_revogados = (revogados_resp.json() or {}).get("convites", [])

    return render_template(
        "convites.html",
        convites=convites_pendentes,
        convites_revogados=convites_revogados
    )


@app.route('/convites/<string:convite_id>/responder', methods=["POST"])
@login_required
def responder_convite_front(convite_id):
    acao = (request.form.get("acao") or "").strip().lower()
    if acao not in ("aceitar", "recusar"):
        flash("Ação inválida.", "alert-danger")
        return redirect(url_for('convites'))

    headers = {'X-Viajante-ID': current_user.get_id()}

    try:
        resp = requests.put(
            f"{BACKEND_URL}/api/convites/{convite_id}",
            json={"acao": acao},
            headers=headers
        )
    except requests.exceptions.RequestException:
        flash("Servidor indisponível no momento. Tente novamente.", "alert-danger")
        return redirect(url_for('convites'))

    if resp.status_code == 200:
        flash(f"Convite {acao} com sucesso!", "alert-success")
    else:
        try:
            erro_msg = resp.json().get("erro", "Erro desconhecido")
        except Exception:
            erro_msg = "Resposta inválida do servidor"
        flash(f"Não foi possível {acao} o convite: {erro_msg}", "alert-danger")

    return redirect(url_for('convites'))


@app.route('/viagem/<string:id_viagem>/revogar/<string:guest_id>', methods=["POST"])
@login_required
def revogar_convite_front(id_viagem, guest_id):
    headers = {'X-Viajante-ID': current_user.get_id()}

    try:
        resp = requests.delete(
            f"{BACKEND_URL}/api/viagem/{id_viagem}/convites/{guest_id}",
            headers=headers
        )
    except requests.exceptions.RequestException:
        flash("Servidor indisponível no momento. Tente novamente.", "alert-danger")
        return redirect(url_for('viagem_detalhe', id_viagem=id_viagem))

    if resp.status_code == 200:
        flash("Convite revogado com sucesso!", "alert-success")
    else:
        try:
            erro_msg = resp.json().get("erro", "Erro desconhecido")
        except Exception:
            erro_msg = "Resposta inválida do servidor"
        flash(f"Não foi possível revogar: {erro_msg}", "alert-danger")

    return redirect(url_for('viagem_detalhe', id_viagem=id_viagem))
