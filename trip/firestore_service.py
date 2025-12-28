from trip import app 
from firebase_admin import firestore
from google.api_core.exceptions import NotFound

# -------------------------------------------------------------
# 1. CONFIGURAÇÃO BASE
# -------------------------------------------------------------
# Obtém o cliente do Firestore que foi inicializado em __init__.py
db = app.config['FIREBASE_DB']

# Referência à Coleção Principal
VIAJANTES_REF = db.collection('viajantes') 

# -------------------------------------------------------------
# 2. FUNÇÕES DE VIAJANTE (Usuário)
# -------------------------------------------------------------

def criar_viajante(dados_viajante):
    """
    Cria um novo documento 'viajante', usando o email como ID do Documento (Doc ID).
    """
    doc_id = dados_viajante['email']
    
    # .set() cria ou sobrescreve o documento
    VIAJANTES_REF.document(doc_id).set(dados_viajante)
    return doc_id


def buscar_viajante_por_doc_id(doc_id):
    """
    Busca um viajante diretamente pelo ID do Documento (Doc ID).
    Usado pelo user_loader e quando o Doc ID é conhecido.
    """
    doc = VIAJANTES_REF.document(doc_id).get()
    
    if doc.exists:
        viajante_data = doc.to_dict()
        viajante_data['doc_id'] = doc.id
        return viajante_data
    
    return None


def buscar_viajante_por_email(email):
    """
    Busca um viajante pelo campo 'email'.
    Assume que o EMAIL é o ID do Documento (Doc ID) para buscar diretamente.
    """
    
    # Se o email for o Doc ID, a busca é rápida (get() vs where()).
    return buscar_viajante_por_doc_id(email)


def atualizar_status_verificacao(email, status):
    """Atualiza o campo is_verified de um viajante."""
    
    # Supondo que o ID do documento seja o e-mail
    VIAJANTES_REF.document(email).update({'is_verified': status})

# -------------------------------------------------------------
# 3. FUNÇÕES DE VIAGEM E ATIVIDADE (Lógica de Subcoleção)
# -------------------------------------------------------------

def get_viagem_ref(viajante_id, viagem_id):
    # GARANTA que o caminho comece por viajantes
    return db.collection('viajantes').document(viajante_id).collection('viagens').document(viagem_id)


def get_atividades_ref(viajante_id, viagem_id):
    return get_viagem_ref(viajante_id, viagem_id).collection('atividades')


# --- NOVO: BUSCAR VIAGEM ---
def buscar_viagem_por_id(viajante_id, viagem_id):
    # .strip() remove espaços em branco ou quebras de linha invisíveis
    id_limpo = viagem_id.strip()
    
    # Busca direta na coleção raiz 'viagens'
    viagem_ref = VIAJANTES_REF.document(viajante_id).collection('viagens').document(id_limpo)

    print(f"--- DEBUG: Buscando no caminho CORRETO: viajantes/{viajante_id}/viagens/{id_limpo} ---")

    viagem_doc = viagem_ref.get()
    
    if viagem_doc.exists:
        viagem_data = viagem_doc.to_dict()
        viagem_data['doc_id'] = viagem_doc.id 
        
        # Busca a subcoleção
        atividades_snapshot = viagem_ref.collection('atividades').stream()
        
        lista_atividades = []
        for doc in atividades_snapshot:
            ativid_data = doc.to_dict()
            ativid_data['doc_id'] = doc.id
            lista_atividades.append(ativid_data)
        
        viagem_data['atividades'] = lista_atividades
        print(f"--- SUCESSO: Encontrada viagem com {len(lista_atividades)} atividades ---")
        return viagem_data
    
    print(f"--- ERRO: Viagem {id_limpo} não encontrada dentro do viajante {viajante_id} ---")
    return None


# --- NOVO: CRIAR ATIVIDADE ---
def criar_atividade(viajante_id, viagem_id, dados_atividade):
    """
    Adiciona um novo documento à subcoleção 'atividades' da viagem especificada.
    Retorna o ID do documento da atividade criada.
    """
    # 1. Cria a referência do documento primeiro (isso gera o ID automaticamente)
    doc_ref = get_atividades_ref(viajante_id, viagem_id).document()
    
    # 2. Salva os dados usando a referência criada
    doc_ref.set(dados_atividade)
    
    # 3. Agora o doc_ref existe e possui o atributo .id
    return doc_ref.id


# --- NOVO: DELETAR ATIVIDADE ---
def deletar_atividade(viajante_id, viagem_id, atividade_id):
    """
    Deleta um documento de Atividade específico na subcoleção.
    """
    
    atividade_doc_ref = get_atividades_ref(viajante_id, viagem_id).document(atividade_id)
    
    # Opcional: verifica se existe antes, mas o delete() é seguro mesmo que não exista.
    if not atividade_doc_ref.get().exists:
        return False
        
    atividade_doc_ref.delete()
    
    return True


# --- ATUALIZAR VALOR RESTANTE (EXISTENTE) ---
def atualizar_valor_restante(viajante_id, viagem_id):
    """
    Calcula o total gasto nas atividades e atualiza o campo 'valor_restante' 
    no Documento Viagem pai dentro da subcoleção do viajante.
    """
    # 1. Obter a referência da viagem (Caminho: viajantes/ID/viagens/ID)
    viagem_ref = get_viagem_ref(viajante_id, viagem_id)
    viagem_doc = viagem_ref.get()
    
    if not viagem_doc.exists:
        # Importante: certifique-se de que 'NotFound' está importado ou use Exception
        print(f"ERRO: Viagem {viagem_id} não encontrada para o usuário {viajante_id}")
        return None
    
    # Pegamos o valor total definido para a viagem
    dados_viagem = viagem_doc.to_dict()
    valor_total_viagem = float(dados_viagem.get('valor_total', 0.0))

    # 2. Acessar a subcoleção de atividades usando nossa função de referência
    # Usamos .stream() que é mais eficiente para leitura de coleções no Firestore
    atividades_ref = get_atividades_ref(viajante_id, viagem_id)
    atividades_docs = atividades_ref.stream()
    
    total_gasto_atividades = 0.0
    
    # 3. Somar os valores de cada atividade
    for doc in atividades_docs:
        ativid_data = doc.to_dict()
        # Somamos o valor, garantindo que seja tratado como número (float)
        total_gasto_atividades += float(ativid_data.get('valor_atividade', 0.0))
        
    # 4. Calcular o novo valor restante
    # Usamos round(..., 2) para garantir que o valor fique bonito (ex: 150.50)
    valor_restante = round(valor_total_viagem - total_gasto_atividades, 2)
    
    # 5. Atualizar o documento da Viagem no Firestore
    viagem_ref.update({
        'valor_restante': valor_restante
    })

    print(f"--- SINCRO: Viagem {viagem_id} atualizada. Restante: R$ {valor_restante} ---")
    return valor_restante


def atualizar_viagem(viajante_id, viagem_id, dados):
    """Atualiza os campos de um documento de viagem específico."""
    viagem_ref = get_viagem_ref(viajante_id, viagem_id)
    viagem_ref.update(dados)



def deletar_viagem_completa(viajante_id, viagem_id):
    """
    Deleta uma viagem e todas as suas atividades (subcoleção).
    """
    viagem_ref = get_viagem_ref(viajante_id, viagem_id)
    
    # 1. No Firestore, temos que deletar os documentos da subcoleção manualmente
    atividades_ref = get_atividades_ref(viajante_id, viagem_id)
    atividades = atividades_ref.get()
    
    for doc in atividades:
        doc.reference.delete()
    
    # 2. Agora deletamos o documento da viagem em si
    viagem_ref.delete()
    return True


def buscar_atividade_por_id(viajante_id, viagem_id, atividade_id):
    """Busca os dados de uma atividade específica."""
    doc = get_atividades_ref(viajante_id, viagem_id).document(atividade_id).get()
    if doc.exists:
        data = doc.to_dict()
        data['doc_id'] = doc.id
        return data
    return None


def atualizar_atividade(viajante_id, viagem_id, atividade_id, dados):
    """Atualiza os campos de uma atividade específica."""
    ref = get_atividades_ref(viajante_id, viagem_id).document(atividade_id)
    ref.update(dados)


def listar_viagens_por_viajante(viajante_id):
    """
    Recupera todas as viagens de um viajante específico.
    """
    # Acessa a subcoleção: viajantes/{id}/viagens
    viagens_ref = VIAJANTES_REF.document(viajante_id).collection('viagens')
    docs = viagens_ref.get()
    
    viagens = []
    for doc in docs:
        dados = doc.to_dict()
        dados['doc_id'] = doc.id # Importante para links de edição/exclusão
        viagens.append(dados)
        
    return viagens


def criar_nova_viagem(viajante_id, dados_viagem):
    """
    Cria um novo documento na subcoleção 'viagens' do viajante.
    """
    # 1. Acessa o caminho correto: viajantes -> id_do_usuario -> viagens
    viagens_ref = VIAJANTES_REF.document(viajante_id).collection('viagens')
    
    # 2. Cria uma referência de documento vazia dentro dessa subcoleção
    novo_doc_ref = viagens_ref.document()
    
    # 3. Salva os dados
    novo_doc_ref.set(dados_viagem)
    
    print(f"--- SUCESSO: Viagem criada no caminho: viajantes/{viajante_id}/viagens/{novo_doc_ref.id} ---")
    
    # 4. Retorna o ID gerado
    return novo_doc_ref.id
