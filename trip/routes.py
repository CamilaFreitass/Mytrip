from flask import render_template, redirect, url_for, request, flash, abort
from trip import app, database, bcrypt
from trip.forms import FormCriarConta, FormLogin, FormEditarPerfil, FormCriarViagem, FormCriarAtividade
from trip.models import Viajante, Viagem, Atividade
from flask_login import login_user, logout_user, current_user, login_required
import secrets 
import os
from PIL import Image

orcamento_total = 0

atividades = []

@app.route('/', methods=["GET", "POST"])
def home():
    global orcamento_total, atividades # sem 'global' a atribuição criaria variáveis locais com o mesmo nome. 
    
    if request.method == "POST":
        tipo_form = request.form.get("tipo_form")

        # Registrar orçamento
        if tipo_form == "orcamento":
            orcamento_total = float(request.form["valor_orcamento"])
            atividades = [] # limpa atividades ao definir novo orçamento
            return redirect(url_for("home"))
        
        # Registrar atividade
        elif tipo_form == "atividade":
            nome = request.form["nome_atividade"]
            custo = float(request.form["custo_atividade"])
            atividades.append({"nome": nome, "custo": custo})
            return redirect(url_for("home"))
        
        return redirect(url_for("home"))
        
    # calculo saldo restante
    total_gasto = sum(a["custo"] for a in atividades)
    saldo = orcamento_total - total_gasto

    return render_template("home.html", orcamento_total=orcamento_total, atividades=atividades, saldo=saldo)


@app.route('/viagem/<int:id_viagem>', methods=["GET", "POST"])
@login_required
def viagem_detalhe(id_viagem):
    # Busca a viagem pelo id
    viagem = Viagem.query.get_or_404(id_viagem)

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

    return render_template('viagem_detalhe.html', viagem=viagem, form_atividade=form_atividade)


@app.route('/acesso', methods=["GET", "POST"])
def acesso():
    form_login = FormLogin()
    form_criarconta = FormCriarConta()

    if form_login.validate_on_submit() and 'submit_login' in request.form:
        viajante = Viajante.query.filter_by(email=form_login.email.data).first()
        if viajante and bcrypt.check_password_hash(viajante.senha, form_login.senha.data):
            login_user(viajante, remember=form_login.lembrar_dados.data)
            flash(f'Login feito com sucesso no e-mail: {form_login.email.data}', 'alert-success')
            par_next = request.args.get('next')
            if par_next:
                return redirect(par_next)
            else:
                return redirect(url_for('viagens'))
        else:
            flash(f'Falha no Login. E-mail ou Senha Incorretos', 'alert-danger')
    if form_criarconta.validate_on_submit() and 'submit_criar_conta' in request.form:
        senha_cript = bcrypt.generate_password_hash(form_criarconta.senha.data)
        viajante = Viajante(nome=form_criarconta.nome.data, email=form_criarconta.email.data, senha=senha_cript)
        database.session.add(viajante)
        database.session.commit()
        flash(f'Conta criada com sucesso para o viajante: {form_criarconta.nome.data}', 'alert-success')
        return redirect(url_for('viagens'))
    return render_template('acesso.html', form_login=form_login, form_criarconta=form_criarconta)


@app.route('/sair')
@login_required
def sair():
    logout_user()
    flash(f'Logout Feito com Sucesso!', 'alert-success')
    return redirect(url_for('home'))


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

    # mostra a foto de perfil
    foto_perfil = url_for('static', filename='fotos_perfil/{}'.format(current_user.foto_perfil))

    return render_template(
        'perfil.html', 
        foto_perfil=foto_perfil, 
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
    
    
    