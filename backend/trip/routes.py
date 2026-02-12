from flask import redirect, request, jsonify, url_for
from trip import app, bcrypt, google
from trip.models import Viajante, Viagem, Atividade
from flask_login import login_user, logout_user, current_user, login_required
from trip.utility import calcular_percentual_e_cor, confirm_token, send_confirmation_email
import os
from .firestore_service import ( atualizar_valor_restante,
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
    listar_viagens_por_viajante,
    criar_convite_viagem,
    listar_convites_do_viajante,
    responder_convite,
    revogar_convite,
    tem_acesso_a_viagem,
    listar_viagens_compartilhadas_para_viajante,
    listar_convites_da_viagem,
)


@app.route('/api/viagem/<string:id_viagem>', methods=["GET"])
def api_viagem_detalhe(id_viagem):
    viajante_id = request.headers.get('X-Viajante-ID')
    if not viajante_id:
        return jsonify({"erro": "Autenticação necessária (header X-Viajante-ID ausente)"}), 401

    viagem_raw = buscar_viagem_por_id(viajante_id, id_viagem)

    if not viagem_raw:
        return jsonify({"erro": "Viagem não encontrada"}), 404

    # Lógica de processamento de dados (Cálculos) permanece no Backend
    viagem = Viagem(viagem_raw)
    viagem_pronta = calcular_percentual_e_cor([viagem])[0]

    # Retornamos os dados limpos para o Frontend
    return jsonify({
        "destino": viagem_pronta.destino,
        "valor_total": viagem_pronta.valor_total,
        "valor_restante": viagem_pronta.valor_restante,
        "percentual_gasto": viagem_pronta.percentual_gasto,
        "cor": viagem_pronta.cor,
        "atividades": viagem_pronta.atividades
    }), 200


@app.route('/api/viagem/<string:id_viagem>/atividade', methods=["POST"])
def api_criar_atividade(id_viagem):
    viajante_id = request.headers.get('X-Viajante-ID')
    if not viajante_id:
        return jsonify({"erro": "Autenticação necessária (header X-Viajante-ID ausente)"}), 401

    dados = request.json  # O backend recebe JSON puro

    criar_atividade(viajante_id, id_viagem, dados)
    novo_restante = atualizar_valor_restante(viajante_id, id_viagem)

    return jsonify({"mensagem": "Atividade criada", "novo_restante": novo_restante}), 201


@app.route('/api/viagem/<string:id_viagem>/editar', methods=['GET'])
def api_get_viagem_editar(id_viagem):
    viajante_id = request.headers.get('X-Viajante-ID')
    if not viajante_id:
        return jsonify({"erro": "Autenticação necessária (header X-Viajante-ID ausente)"}), 401

    viagem_data = buscar_viagem_por_id(viajante_id, id_viagem)
    if not viagem_data:
        return jsonify({"erro": "Viagem não encontrada"}), 404

    # Retorna apenas os campos necessários para preencher o formulário
    return jsonify(viagem_data), 200


@app.route('/api/viagem/<string:id_viagem>/editar', methods=['PUT'])
def api_update_viagem(id_viagem):
    viajante_id = request.headers.get('X-Viajante-ID')
    if not viajante_id:
        return jsonify({"erro": "Autenticação necessária (header X-Viajante-ID ausente)"}), 401

    dados_novos = request.json  # Recebe JSON do frontend

    # 1. Atualiza os dados básicos
    atualizar_viagem(viajante_id, id_viagem, dados_novos)

    # 2. Recalcula o saldo (caso o valor_total tenha mudado)
    atualizar_valor_restante(viajante_id, id_viagem)

    return jsonify({"mensagem": "Viagem atualizada com sucesso!"}), 200


@app.route('/api/viagem/<string:viagem_id>', methods=['DELETE'])
def api_deletar_viagem(viagem_id):
    viajante_id = request.headers.get('X-Viajante-ID')
    if not viajante_id:
        return jsonify({"erro": "Autenticação necessária (header X-Viajante-ID ausente)"}), 401

    # Busca a viagem para verificar posse
    viagem_data = buscar_viagem_por_id(viajante_id, viagem_id)

    if not viagem_data:
        return jsonify({"erro": "Viagem não encontrada"}), 404

    # Verifica se o viajante logado é o dono da viagem
    if viagem_data.get('id_viajante') == viajante_id:
        try:
            deletar_viagem_completa(viajante_id, viagem_id)
            return jsonify({"mensagem": "Viagem excluída com sucesso!"}), 200
        except Exception as e:
            return jsonify({"erro": f"Erro ao excluir: {str(e)}"}), 500

    return jsonify({"erro": "Permissão negada"}), 403


@app.route('/api/viagem/<string:id_viagem>/atividade/<string:id_atividade>', methods=['DELETE'])
def api_excluir_atividade(id_viagem, id_atividade):
    print(f"DEBUG: Rota DELETE chamada para viagem {id_viagem}, atividade {id_atividade}")

    viajante_id = request.headers.get('X-Viajante-ID')
    if not viajante_id:
        print("DEBUG: Header X-Viajante-ID ausente")
        return jsonify({"erro": "Autenticação necessária (header X-Viajante-ID ausente)"}), 401

    # 1. Tenta deletar a atividade
    sucesso = deletar_atividade(viajante_id, id_viagem, id_atividade)
    if sucesso:
        print("DEBUG: Atividade deletada com sucesso")
    else:
        print("DEBUG: Atividade não encontrada para deleção")

    if sucesso:
        try:
            # 2. Recalcula o valor restante da viagem pai
            atualizar_valor_restante(viajante_id, id_viagem)
            return jsonify({"mensagem": "Atividade excluída com sucesso!"}), 200
        except Exception as e:
            print(f"DEBUG: Erro ao atualizar saldo: {str(e)}")
            return jsonify({"erro": "Atividade excluída, mas erro ao atualizar saldo."}), 206

    return jsonify({"erro": "Atividade não encontrada."}), 404


@app.route('/test_delete', methods=['DELETE'])
def test_delete():
    return jsonify({"mensagem": "Teste DELETE bem-sucedido!"}), 200

@app.route('/api/viagem/<string:id_viagem>/atividade/<string:id_atividade>', methods=['GET'])
def api_get_atividade(id_viagem, id_atividade):
    viajante_id = request.headers.get('X-Viajante-ID')
    if not viajante_id:
        return jsonify({"erro": "Autenticação necessária (header X-Viajante-ID ausente)"}), 401

    # Busca dados da viagem (para contexto) e da atividade específica
    viagem_data = buscar_viagem_por_id(viajante_id, id_viagem)
    atividade_data = buscar_atividade_por_id(viajante_id, id_viagem, id_atividade)

    if not viagem_data or not atividade_data:
        return jsonify({"erro": "Recurso não encontrado"}), 404

    return jsonify({
        "viagem": viagem_data,
        "atividade": atividade_data
    }), 200


@app.route('/api/viagem/<string:id_viagem>/atividade/<string:id_atividade>', methods=['PUT'])
def api_atualizar_atividade(id_viagem, id_atividade):
    viajante_id = request.headers.get('X-Viajante-ID')
    if not viajante_id:
        return jsonify({"erro": "Autenticação necessária (header X-Viajante-ID ausente)"}), 401

    novos_dados = request.json  # Recebe JSON do frontend

    try:
        # 1. Atualiza a atividade
        atualizar_atividade(viajante_id, id_viagem, id_atividade, novos_dados)
        # 2. Recalcula o saldo da viagem pai
        atualizar_valor_restante(viajante_id, id_viagem)

        return jsonify({"mensagem": "Atividade editada com sucesso!"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/api/confirmar/<token>', methods=['GET'])
def api_confirmar_email(token):
    # 1. Valida o token (Lógica de segurança permanece no Backend)
    email_ou_status = confirm_token(token)

    if email_ou_status == 'expired':
        return jsonify({"erro": "O link expirou."}), 410
    if email_ou_status == 'invalid':
        return jsonify({"erro": "O link é inválido."}), 400

    email = email_ou_status
    viajante_data = buscar_viajante_por_email(email)

    if viajante_data:
        if not viajante_data.get('is_verified'):
            # 2. Ativa o usuário no Firestore
            atualizar_status_verificacao(email, True)
            viajante_data['is_verified'] = True

        # Retornamos os dados para o Frontend logar o usuário
        return jsonify(viajante_data), 200

    return jsonify({"erro": "Usuário não encontrado."}), 404


@app.route('/api/login', methods=['POST'])
def api_login():
    dados = request.json
    email = dados.get('email')
    senha = dados.get('senha')

    viajante_data = buscar_viajante_por_email(email)

    if viajante_data:
        # Verifica a senha usando o bcrypt do Backend
        if bcrypt.check_password_hash(viajante_data.get('senha'), senha):
            if not viajante_data.get('is_verified'):
                return jsonify({"erro": "conta_nao_ativada"}), 403

            if 'doc_id' not in viajante_data:
                viajante_data['doc_id'] = viajante_data.get('email')

            # Retorna os dados do usuário para o frontend logar
            return jsonify(viajante_data), 200

    return jsonify({"erro": "credenciais_invalidas"}), 401


@app.route('/api/cadastro', methods=['POST'])
def api_cadastro():
    dados = request.json

    # Criptografia e preparação dos dados
    senha_hash = bcrypt.generate_password_hash(dados['senha']).decode('utf-8')
    novo_viajante = {
        'nome': dados['nome'],
        'email': dados['email'],
        'senha': senha_hash,
        'is_verified': False
    }

    # Salva e envia e-mail
    criar_viajante(novo_viajante)
    send_confirmation_email(dados['email'])

    return jsonify({"mensagem": "Usuário criado com sucesso!"}), 201


@app.route('/login/google')
def login_google():
    # Esta rota DEVE ser chamada pelo Frontend para iniciar o fluxo
    # Ela gera o 'state' e salva na sessão do Backend
    redirect_uri = url_for('api_auth_google', _external=True)
    return google.authorize_redirect(redirect_uri)

# rota de autenticação do login do google
@app.route('/api/auth/google')
def api_auth_google():
    frontend_url = os.getenv('FRONTEND_URL', 'http://127.0.0.1:8080')
    # O Backend valida o token que o Google enviou
    try:
        token = google.authorize_access_token()
        resp = google.get('userinfo')
        user_info = resp.json()
        email = user_info.get('email')

        # Lógica de buscar ou criar usuário (permanece no Backend)
        viajante_data = buscar_viajante_por_email(email)
        if not viajante_data:
            novo_viajante_dict = {
                'nome': user_info.get('name'),
                'email': email,
                'senha': None,
                'is_verified': True
            }
            criar_viajante(novo_viajante_dict)
            viajante_data = buscar_viajante_por_email(email)

        # REDIRECIONAMENTO CRUCIAL:
        # Após validar, enviamos o usuário de volta para o FRONTEND (porta 8080)
        # Passamos um parâmetro (como o email) para o Front saber quem logar
        return redirect(f"{frontend_url}/login/callback?email={email}")

    except Exception as e:
        print(f"Erro na autenticação Google: {e}")
        return redirect(f"{frontend_url}/acesso?erro=auth_failed")


@app.route('/api/usuario/<string:email>', methods=['GET'])
def api_get_usuario_por_email(email):
    viajante_data = buscar_viajante_por_email(email)
    if viajante_data:
        return jsonify(viajante_data), 200
    return jsonify({"erro": "Usuário não encontrado"}), 404


@app.route('/api/sair')
@login_required
def api_sair():
    logout_user()
    return jsonify({"mensagem": "Logout realizado no backend"}), 200


@app.route('/api/perfil', methods=['GET'])
def api_perfil():
    viajante_id = request.headers.get('X-Viajante-ID')
    if not viajante_id:
        return jsonify({"erro": "Autenticação necessária (header X-Viajante-ID ausente)"}), 401

    # 1) Viagens próprias (dono)
    viagens_proprias_data = listar_viagens_por_viajante(viajante_id)
    for v in viagens_proprias_data:
        v["papel"] = "dono"
        v["owner_id"] = viajante_id

    # 2) Viagens compartilhadas (convidado)
    viagens_compartilhadas_data = listar_viagens_compartilhadas_para_viajante(viajante_id)

    # 3) Calcula percentual/cor para todas
    viagens_todas_data = viagens_proprias_data + viagens_compartilhadas_data
    viagens_objs = [Viagem(dados) for dados in viagens_todas_data]
    viagens_com_calculos = calcular_percentual_e_cor(viagens_objs)

    # 4) Serializa para JSON mantendo papel/owner_id
    lista_final = []
    for idx, v in enumerate(viagens_com_calculos):
        original = viagens_todas_data[idx]
        lista_final.append({
            "doc_id": v.doc_id,
            "destino": v.destino,
            "valor_total": v.valor_total,
            "valor_restante": v.valor_restante,
            "percentual_gasto": v.percentual_gasto,
            "cor": v.cor,
            "papel": original.get("papel"),
            "owner_id": original.get("owner_id"),
        })

    return jsonify({
        "qtd_viagens": len(lista_final),
        "viagens": lista_final
    }), 200


@app.route('/api/viagem/criar', methods=['POST'])
def api_criar_viagem():
    viajante_id = request.headers.get('X-Viajante-ID')
    if not viajante_id:
        return jsonify({"erro": "Autenticação necessária (header X-Viajante-ID ausente)"}), 401

    dados = request.json  # O Backend recebe os dados limpos do formulário

    # Preparamos o dicionário para o Firestore
    nova_viagem_dados = {
        'destino': dados.get('destino'),
        'valor_total': dados.get('valor_total'),
        'valor_restante': dados.get('valor_total'), # Inicialmente sobra tudo
        'id_viajante': viajante_id
    }

    # Salvamos no Firestore
    doc_id = criar_nova_viagem(viajante_id, nova_viagem_dados)

    return jsonify({"mensagem": "Viagem criada com sucesso!", "id": doc_id}), 201
    

@app.route('/api/viagem/<string:viagem_id>/convites', methods=["POST"])
def api_criar_convite(viagem_id):
    owner_id = request.headers.get('X-Viajante-ID')
    if not owner_id:
        return jsonify({"erro": "Autenticação necessária (header X-Viajante-ID ausente)"}), 401

    dados = request.json or {}
    guest_email = dados.get("email_convidado")
    if not guest_email:
        return jsonify({"erro": "Campo obrigatório: email_convidado"}), 400

    # Valida e pega snapshot opcional (ajuda o frontend depois, mas não é UI agora)
    viagem_data = buscar_viagem_por_id(owner_id, viagem_id)
    if not viagem_data:
        return jsonify({"erro": "Viagem não encontrada"}), 404

    convite_id, erro = criar_convite_viagem(
        owner_id=owner_id,
        viagem_id=viagem_id,
        guest_id=guest_email,
        destino_snapshot=viagem_data.get("destino"),
        owner_nome_snapshot=None
    )

    if erro == "convidado_nao_encontrado":
        return jsonify({"erro": "Convidado não encontrado"}), 404
    if erro == "viagem_nao_encontrada":
        return jsonify({"erro": "Viagem não encontrada"}), 404
    if not convite_id:
        return jsonify({"erro": "Erro ao criar convite"}), 500

    return jsonify({"mensagem": "Convite criado", "convite_id": convite_id}), 201


@app.route('/api/convites', methods=["GET"])
def api_listar_convites():
    viajante_id = request.headers.get('X-Viajante-ID')
    if not viajante_id:
        return jsonify({"erro": "Autenticação necessária (header X-Viajante-ID ausente)"}), 401

    status = request.args.get("status")  # ex: ?status=pendente
    convites = listar_convites_do_viajante(viajante_id, status=status)

    return jsonify({
        "qtd": len(convites),
        "convites": convites
    }), 200


@app.route('/api/convites/<string:convite_id>', methods=["PUT"])
def api_responder_convite(convite_id):
    viajante_id = request.headers.get('X-Viajante-ID')
    if not viajante_id:
        return jsonify({"erro": "Autenticação necessária (header X-Viajante-ID ausente)"}), 401

    dados = request.json or {}
    acao = dados.get("acao")  # "aceitar" | "recusar"
    ok, erro = responder_convite(viajante_id, convite_id, acao)

    if erro == "acao_invalida":
        return jsonify({"erro": "Ação inválida. Use 'aceitar' ou 'recusar'."}), 400
    if erro == "convite_nao_encontrado":
        return jsonify({"erro": "Convite não encontrado"}), 404
    if not ok:
        return jsonify({"erro": "Erro ao responder convite"}), 500

    return jsonify({"mensagem": f"Convite {acao} com sucesso"}), 200


@app.route('/api/viagem/<string:viagem_id>/convites/<string:guest_id>', methods=["DELETE"])
def api_revogar_convite(viagem_id, guest_id):
    owner_id = request.headers.get('X-Viajante-ID')
    if not owner_id:
        return jsonify({"erro": "Autenticação necessária (header X-Viajante-ID ausente)"}), 401

    # Garantir que a viagem existe e pertence ao dono (padrão atual do seu projeto)
    viagem_data = buscar_viagem_por_id(owner_id, viagem_id)
    if not viagem_data:
        return jsonify({"erro": "Viagem não encontrada"}), 404
    if viagem_data.get("id_viajante") != owner_id:
        return jsonify({"erro": "Permissão negada"}), 403

    revogou = revogar_convite(owner_id=owner_id, viagem_id=viagem_id, guest_id=guest_id)
    if not revogou:
        return jsonify({"mensagem": "Nenhum convite encontrado para revogar (talvez já tenha sido removido)."}), 200

    return jsonify({"mensagem": "Convite revogado com sucesso"}), 200


def _get_viajante_id_or_401():
    viajante_id = request.headers.get('X-Viajante-ID')
    if not viajante_id:
        return None, (jsonify({"erro": "Autenticação necessária (header X-Viajante-ID ausente)"}), 401)
    return viajante_id, None


def _check_access_or_403(viajante_id, owner_id, viagem_id):
    if not tem_acesso_a_viagem(viajante_id, owner_id, viagem_id):
        return jsonify({"erro": "Permissão negada (convite não aceito ou revogado)"}), 403
    # (Opcional) também garantir que a viagem existe no owner:
    viagem = buscar_viagem_por_id(owner_id, viagem_id)
    if not viagem:
        return jsonify({"erro": "Viagem não encontrada"}), 404
    return None


@app.route('/api/viagem/<string:owner_id>/<string:viagem_id>', methods=["GET"])
def api_viagem_detalhe_compartilhada(owner_id, viagem_id):
    viajante_id, err = _get_viajante_id_or_401()
    if err:
        return err

    acesso_err = _check_access_or_403(viajante_id, owner_id, viagem_id)
    if acesso_err:
        return acesso_err

    viagem_raw = buscar_viagem_por_id(owner_id, viagem_id)
    viagem = Viagem(viagem_raw)
    viagem_pronta = calcular_percentual_e_cor([viagem])[0]

    return jsonify({
        "doc_id": viagem_pronta.doc_id,
        "owner_id": owner_id,
        "papel": "dono" if viajante_id == owner_id else "convidado",
        "destino": viagem_pronta.destino,
        "valor_total": viagem_pronta.valor_total,
        "valor_restante": viagem_pronta.valor_restante,
        "percentual_gasto": viagem_pronta.percentual_gasto,
        "cor": viagem_pronta.cor,
        "atividades": viagem_pronta.atividades
    }), 200


@app.route('/api/viagem/<string:owner_id>/<string:viagem_id>/atividade', methods=["POST"])
def api_criar_atividade_compartilhada(owner_id, viagem_id):
    viajante_id, err = _get_viajante_id_or_401()
    if err:
        return err

    acesso_err = _check_access_or_403(viajante_id, owner_id, viagem_id)
    if acesso_err:
        return acesso_err

    dados = request.json or {}
    if "nome_atividade" not in dados or "valor_atividade" not in dados:
        return jsonify({"erro": "Campos obrigatórios: nome_atividade, valor_atividade"}), 400

    # Marca quem criou (útil para auditoria)
    dados["criado_por"] = viajante_id

    criar_atividade(owner_id, viagem_id, dados)
    novo_restante = atualizar_valor_restante(owner_id, viagem_id)

    return jsonify({"mensagem": "Atividade criada", "novo_restante": novo_restante}), 201


@app.route('/api/viagem/<string:owner_id>/<string:viagem_id>/atividade/<string:atividade_id>', methods=['GET'])
def api_get_atividade_compartilhada(owner_id, viagem_id, atividade_id):
    viajante_id, err = _get_viajante_id_or_401()
    if err:
        return err

    acesso_err = _check_access_or_403(viajante_id, owner_id, viagem_id)
    if acesso_err:
        return acesso_err

    viagem_data = buscar_viagem_por_id(owner_id, viagem_id)
    atividade_data = buscar_atividade_por_id(owner_id, viagem_id, atividade_id)

    if not atividade_data:
        return jsonify({"erro": "Atividade não encontrada"}), 404

    return jsonify({
        "viagem": viagem_data,
        "atividade": atividade_data,
        "owner_id": owner_id,
        "papel": "dono" if viajante_id == owner_id else "convidado"
    }), 200


@app.route('/api/viagem/<string:owner_id>/<string:viagem_id>/atividade/<string:atividade_id>', methods=['PUT'])
def api_atualizar_atividade_compartilhada(owner_id, viagem_id, atividade_id):
    viajante_id, err = _get_viajante_id_or_401()
    if err:
        return err

    acesso_err = _check_access_or_403(viajante_id, owner_id, viagem_id)
    if acesso_err:
        return acesso_err

    novos_dados = request.json or {}
    if not novos_dados:
        return jsonify({"erro": "Body JSON vazio"}), 400

    try:
        atualizar_atividade(owner_id, viagem_id, atividade_id, novos_dados)
        atualizar_valor_restante(owner_id, viagem_id)
        return jsonify({"mensagem": "Atividade editada com sucesso!"}), 200
    except Exception as e:
        return jsonify({"erro": str(e)}), 500


@app.route('/api/viagem/<string:owner_id>/<string:viagem_id>/atividade/<string:atividade_id>', methods=['DELETE'])
def api_excluir_atividade_compartilhada(owner_id, viagem_id, atividade_id):
    viajante_id, err = _get_viajante_id_or_401()
    if err:
        return err

    acesso_err = _check_access_or_403(viajante_id, owner_id, viagem_id)
    if acesso_err:
        return acesso_err

    sucesso = deletar_atividade(owner_id, viagem_id, atividade_id)
    if not sucesso:
        return jsonify({"erro": "Atividade não encontrada."}), 404

    try:
        atualizar_valor_restante(owner_id, viagem_id)
        return jsonify({"mensagem": "Atividade excluída com sucesso!"}), 200
    except Exception:
        return jsonify({"erro": "Atividade excluída, mas erro ao atualizar saldo."}), 206


@app.route('/api/viagem/<string:viagem_id>/convites', methods=["GET"])
def api_listar_convites_da_viagem(viagem_id):
    owner_id = request.headers.get('X-Viajante-ID')
    if not owner_id:
        return jsonify({"erro": "Autenticação necessária (header X-Viajante-ID ausente)"}), 401

    viagem_data = buscar_viagem_por_id(owner_id, viagem_id)
    if not viagem_data:
        return jsonify({"erro": "Viagem não encontrada"}), 404
    if viagem_data.get("id_viajante") != owner_id:
        return jsonify({"erro": "Permissão negada"}), 403

    convites = listar_convites_da_viagem(owner_id, viagem_id)
    return jsonify({"qtd": len(convites), "convites": convites}), 200