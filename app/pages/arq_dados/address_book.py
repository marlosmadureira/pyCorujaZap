import streamlit as st
from settings import get_operacao, PROJECT_ROOT
from db.models import Operation, Target, Contact, File, operation_targets, file_contacts
from db.session import get_session
from sqlalchemy import and_
import pandas as pd
import os


################  FUNÇÕES DE CONSULTA  ###############
################  FUNÇÕES DE CONSULTA  ###############
################  FUNÇÕES DE CONSULTA  ###############

def get_targets(op_name):
    '''Retorna uma lista de targets, baseado no nome da operação'''
    with get_session() as session:
        # Buscar a operação pelo nome
        current_op = session.query(Operation).filter(Operation.name == op_name).first()
        
        if not current_op:
            return []  # Retorna lista vazia se operação não for encontrada
        
        # Retornar os targets usando o relacionamento
        return [op.target for op in current_op.targets]


def get_address_book_data(**kwargs):
    '''Buscar dados da agenda de contatos do target selecionado'''
   
    target_phone = kwargs.get('target_phone')
    nome_operacao = get_operacao()
    
    if not nome_operacao or not target_phone:
        return pd.DataFrame()
    
    try:
        with get_session() as session:
            # Buscar a operação pelo nome
            current_op = session.query(Operation).filter(Operation.name == nome_operacao).first()
            
            if not current_op:
                return pd.DataFrame()
            
            # Buscar o target_id específico dentro do contexto da operação
            target_in_operation = session.query(Target.target_id).join(
                operation_targets,
                Target.target_id == operation_targets.c.target_id
            ).filter(
                and_(
                    operation_targets.c.operation_id == current_op.operation_id,
                    Target.target == target_phone
                )
            ).first()
            
            if not target_in_operation:
                return pd.DataFrame()
            
            target_id = target_in_operation.target_id
            
            # Buscar contatos do target através dos files
            query = session.query(
                Contact.contact_phone.label('contato'),
                Contact.contact_type.label('tipo'),
                File.generated_timestamp.label('gerado_em'),
                File.archive_name.label('arquivo')
            ).select_from(Contact).join(
                file_contacts, Contact.contact_id == file_contacts.c.contact_id
            ).join(
                File, file_contacts.c.file_id == File.file_id
            ).filter(
                and_(
                    File.operation_id == current_op.operation_id,
                    File.target_id == target_id
                )
            ).order_by(Contact.contact_phone)
            
            results = query.all()
            
            if not results:
                return pd.DataFrame()
            
            # Converter para DataFrame
            data = []
            for r in results:
                # Formatação do tipo de contato
                tipo_formatado = {
                    'symmetric_contact': 'simétrico',
                    'asymmetric_contact': 'assimétrico'
                }.get(r.tipo, r.tipo or 'N/A')
                
                # Formatação da data
                gerado_em = r.gerado_em.strftime('%d/%m/%Y %H:%M:%S') if r.gerado_em else 'N/A'
                
                data.append({
                    'contato': r.contato,
                    'tipo': tipo_formatado,
                    'gerado_em': gerado_em,
                    'arquivo': r.arquivo or 'N/A'
                })
            
            df = pd.DataFrame(data)
            
            # Remover duplicatas mantendo o registro mais recente
            if not df.empty:
                df = df.drop_duplicates(subset=['contato'], keep='first')
                df = df.reset_index(drop=True)
            
            return df
            
    except Exception as e:
        print(f"❌ Erro na função get_address_book_data: {str(e)}")
        return pd.DataFrame()


################  LÓGICA SIDEBAR  ###############
################  LÓGICA SIDEBAR  ###############
################  LÓGICA SIDEBAR  ###############

with st.sidebar:
    st.markdown('''<style>
    /* MOBILE FIRST - Logo responsivo */
    div[data-testid="stSidebarHeader"] > img, 
    div[data-testid="collapsedControl"] > img {
        margin-top: 1rem;
        height: 4rem; /* Menor por padrão */
        width: auto;
    }
    
    /* DESKTOP - Logo maior */
    @media (min-width: 769px) {
        div[data-testid="stSidebarHeader"] > img, 
        div[data-testid="collapsedControl"] > img {
            margin-top: 4rem !important;
            height: 10rem !important;
        }
    }
    
    /* Garantir espaçamento da navegação */
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
    nome_operacao = get_operacao()
    st.header(f'Operação: {nome_operacao}', divider='red')

    if nome_operacao:
            target_adressbook_options = get_targets(nome_operacao)
            target_adressbook_options.insert(0, '')
            
            if not target_adressbook_options:
                st.warning("Nenhum alvo encontrado para esta operação.")
                target_adressbook = None
                date_message = None

            st.write('')
            target_adressbook = st.selectbox(
                "Selecione um telefone:", 
                options=target_adressbook_options, 
                placeholder='Telefone',
                index=0
            )
            # Botão para buscar agenda
            btn_get_messages = st.button(
                "Buscar agenda",
                type="primary",
                use_container_width=True
            )


################  LÓGICA CENTRAL  ###############
################  LÓGICA CENTRAL  ###############
################  LÓGICA CENTRAL  ###############

# CSS para estilização
st.markdown("""
    <style>
    /* Centralizar métricas */
    div[data-testid="stMetric"] {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        padding-top: 10px;
        border-radius: 8px;
    }
    
    /* Centralizar label das métricas */
    div[data-testid="stMetricLabel"] {
        text-align: center !important;
        justify-content: center !important;
        width: 100% !important;
    }
    
    /* Centralizar valor das métricas */
    div[data-testid="stMetricValue"] {
        text-align: center !important;
        justify-content: center !important;
        width: 100% !important;
    }
    
    /* Centralizar o texto dentro do valor */
    div[data-testid="stMetricValue"] div {
        text-align: center !important;
        margin: 0 auto !important;
        display: block !important;
        width: 100% !important;
    }
    
    /* Centralizar colunas das métricas */
    div[data-testid="stColumn"] {
        display: flex;
        justify-content: center;
    }
    </style>
    """, unsafe_allow_html=True)

nome_operacao = get_operacao()

if not nome_operacao:
    st.error("Por favor, selecione uma Operação para habilitar os filtros na barra lateral.", icon="🚨")
    st.error("Administração > Configurações > Selecionar operação.", icon="🚨")
    st.stop()

st.subheader("Agenda de Contatos", divider='red')

# Verificar se o botão foi clicado e se os dados estão disponíveis
if 'btn_get_messages' in locals() and btn_get_messages and 'target_adressbook' in locals():
    if target_adressbook and target_adressbook != '':
        
        # Mostrar spinner enquanto processa
        with st.spinner('Buscando agenda de contatos...'):
            # Chamar a função e capturar o resultado
            df_contacts = get_address_book_data(target_phone=target_adressbook)
        
        # PROTEÇÃO: Garantir que df_contacts seja sempre um DataFrame
        if df_contacts is None:
            df_contacts = pd.DataFrame()
        
        if not df_contacts.empty:
            
            # Métricas resumidas no topo
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("📞 Total de Contatos", len(df_contacts))
            
            with col2:
                simetricos = len(df_contacts[df_contacts['tipo'] == 'simétrico'])
                st.metric("🔄 Simétricos", simetricos)
            
            with col3:
                assimetricos = len(df_contacts[df_contacts['tipo'] == 'assimétrico'])
                st.metric("➡️ Assimétricos", assimetricos)
            
            with col4:
                # Calcular percentual de simétricos
                percentual = (simetricos / len(df_contacts) * 100) if len(df_contacts) > 0 else 0
                st.metric("📊 % Simétricos", f"{percentual:.1f}%")
                       
            # Exibir o DataFrame
            st.dataframe(
                df_contacts, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "contato": st.column_config.TextColumn(
                        "📱 Contato",
                        help="Número do telefone do contato",
                        width="medium"
                    ),
                    "tipo": st.column_config.TextColumn(
                        "🔄 Tipo", 
                        help="Tipo de relacionamento na agenda",
                        width="medium"
                    ),
                    "gerado_em": st.column_config.TextColumn(
                        "📅 Gerado em",
                        help="Data e hora de geração do arquivo",
                        width="medium"
                    ),
                    "arquivo": st.column_config.TextColumn(
                        "📁 Arquivo",
                        help="Nome do arquivo de origem",
                        width="medium"
                    )
                }
            )
            
        else:
            st.info("📭 Nenhum contato encontrado na agenda para este alvo.", icon="ℹ️")
    else:
        st.info("📱 Por favor, selecione um telefone na barra lateral para buscar a agenda.", icon="ℹ️")
else:
    st.info("🔍 Configure o telefone na barra lateral e clique em 'Buscar agenda' para ver os contatos.", icon="ℹ️")
