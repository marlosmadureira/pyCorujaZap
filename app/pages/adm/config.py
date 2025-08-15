import streamlit as st
from settings import PROJECT_ROOT, set_operacao, get_operacao, set_current_op_id
from db.models import Operation
from db.session import get_session
import os


# Inicialização de estados
if 'modo_operacao' not in st.session_state:
    st.session_state['modo_operacao'] = None
if 'operacao_definida' not in st.session_state:
    st.session_state['operacao_definida'] = False

# Sidebar (pode ser usada a qualquer momento)
with st.sidebar:
    st.markdown('''<style>
    /* ✅ MOBILE FIRST - Logo responsivo */
    div[data-testid="stSidebarHeader"] > img, 
    div[data-testid="collapsedControl"] > img {
        margin-top: 1rem;
        height: 4rem; /* Menor por padrão */
        width: auto;
    }
    
    /* ✅ DESKTOP - Logo maior */
    @media (min-width: 769px) {
        div[data-testid="stSidebarHeader"] > img, 
        div[data-testid="collapsedControl"] > img {
            margin-top: 4rem !important;
            height: 10rem !important;
        }
    }
    
    /* ✅ Garantir espaçamento da navegação */
    nav[data-testid="stSidebarNav"] {
        margin-top: 1rem !important;
        position: relative !important;
        z-index: 999 !important;
    }
    
</style>''', unsafe_allow_html=True)
    logo_path = os.path.join(PROJECT_ROOT, 'logo.png')
    st.logo(image=logo_path, icon_image=logo_path, size="large")
    st.write('')
    st.write('')
    st.header('Escolha uma opção', divider='red')
    if st.button("🔍 - Selecionar operação", type="tertiary"):
        st.session_state['modo_operacao'] = 'selecionar'
    if st.button("🆕 - Adicionar operação", type="tertiary"):
        st.session_state['modo_operacao'] = 'criar'
    if st.button("✏️ - Alterar operação", type="tertiary"):
        st.session_state['modo_operacao'] = 'alterar'


if st.session_state.pop('operacao_criada', False):
    st.toast("Operação criada com sucesso! Agora selecione para continuar.", icon="✅")

# Cabeçalho
st.header("Configurações de ambiente", divider='red')

# Mensagens de orientação
def exibe_info_inicial():
    st.write(' ')
    st.text('Para iniciar a aplicação, é necessário definir uma Operação.')
    st.text('Após a seleção, todas as análises serão feitas com base neste contexto.')
    for _ in range(3):
        st.write(' ')
    st.error('Selecione ou crie uma operação utilizando o menu lateral.')

def exibe_info_final():
    operacao = get_operacao()
    operacao = str(operacao)
    st.success(f"Operação selecionada: {operacao}")
    st.info('Clique no menu "Recursos" na barra acima para prosseguir com a análise.')

# Caso nenhuma operação esteja definida e nenhum formulário aberto
if not st.session_state['operacao_definida'] and st.session_state['modo_operacao'] is None:
    exibe_info_inicial()

# Formulário de seleção
if st.session_state['modo_operacao'] == 'selecionar':
    st.subheader("Selecionar operação existente")
    with st.form("form_selecionar", clear_on_submit=True):
        with get_session() as session:
            operacoes = session.query(Operation).all()
            nomes_operacoes = [op.name for op in operacoes]
            operacoes_dict = [{'id': op.operation_id, 'name': op.name} for op in operacoes]

        if not nomes_operacoes:
            st.warning("Nenhuma operação encontrada. Crie uma nova operação.")
            st.form_submit_button("Criar nova operação", 
                                  on_click=lambda: st.session_state.update({'modo_operacao': 'criar'}), 
                                  type="primary"
            )
            
        else:
            operacao = st.selectbox("Operação", index=None, options=nomes_operacoes,placeholder="Escolha a operação")
            submitted = st.form_submit_button("Confirmar seleção", type="primary")
            if submitted:
                if not operacao:
                    st.warning("Por favor, informe uma operação válida.")
                else:
                    set_operacao(nome_operacao=operacao)

                    # Fixa ID da operação selecionado no session_state para ser utilizado nas futuras queries.
                    operacao_obj = next((op for op in operacoes_dict if op['name'] == operacao), None)
                    set_current_op_id(operacao_obj['id'])

                    st.session_state['operacao_definida'] = True
                    st.session_state['modo_operacao'] = None
                    st.toast('Operação selecionada com sucesso!', icon="✅")
                    st.rerun()

# Formulário de criação
if st.session_state['modo_operacao'] == 'criar':
    st.subheader("Criar nova operação")
    with st.form("form_criar", clear_on_submit=True):
        name = st.text_input("Nome", placeholder="Nome da operação")
        description = st.text_area("Descrição", placeholder="Descrição da operação")
        botao_criar = st.form_submit_button("Criar Operação", type="primary")
        if botao_criar:
            if not name or not description:
                st.error("Por favor, preencha todos os campos.")
            else:
                
                with get_session() as session:
                    operacao = Operation(name=name, description=description)
                    session.add(operacao)
                    session.commit()

                st.session_state['operacao_criada'] = True  # ← Flag para mostrar o toast
                st.session_state['modo_operacao'] = None
                st.rerun()  # ← O toast será mostrado após o rerun

# Formulário de alteração
if st.session_state['modo_operacao'] == 'alterar':
    st.subheader("Alterar nova operação")
    with st.form("form_alterar", clear_on_submit=True):

        with get_session() as session:
            operacoes = session.query(Operation).all()
            nomes_operacoes = [op.name for op in operacoes]

        nome_anterior = st.selectbox("Selecione o nome anterior", index=None, options=nomes_operacoes, placeholder="Nome da operação", key='anterior')
        nome_alterado = st.text_input("Digite o novo nome", placeholder="Nome da operação", key='novo')
        description = st.text_area("Descrição", placeholder="Descrição da operação")
        botao_alterar = st.form_submit_button("Alterar Operação", type="primary")
        if botao_alterar:
            if not nome_anterior or not nome_alterado or not description:
                st.error("Por favor, preencha todos os campos.")
            else:
                # set_operacao(nome_operacao=name)
                with get_session() as session:
                    operacao = session.query(Operation).filter(Operation.name == nome_anterior).first()
                    if operacao:
                        operacao.name = nome_alterado
                        operacao.description = description
                        session.commit()
                    else:
                        st.error("Operação não encontrada.")
                
                st.session_state['operacao_criada'] = True  # ← Flag para mostrar o toast
                st.session_state['modo_operacao'] = None
                st.rerun()  # ← O toast será mostrado após o rerun

# Exibir mensagem final se já houver operação definida e nenhum formulário em aberto
if st.session_state['operacao_definida'] and st.session_state['modo_operacao'] is None:
    exibe_info_final()
