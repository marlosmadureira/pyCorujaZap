import streamlit as st
from settings import get_operacao, PROJECT_ROOT
from db.models import Operation, Target, File, operation_targets, Group, GroupMetadata, File, file_groups
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


def get_groups_data(**kwargs):
    '''Buscar grupos - VERSÃO SUPER SIMPLES'''
        
    target_phone = kwargs.get('target_phone')
    nome_operacao = get_operacao()
    
    if not nome_operacao or not target_phone:
        return pd.DataFrame()
    
    try:
        with get_session() as session:
            # Buscar operação
            current_op = session.query(Operation).filter(Operation.name == nome_operacao).first()
            if not current_op:
                return pd.DataFrame()
            
            # Buscar target
            target_obj = session.query(Target).join(operation_targets).filter(
                and_(
                    operation_targets.c.operation_id == current_op.operation_id,
                    Target.target == target_phone
                )
            ).first()
            
            if not target_obj:
                return pd.DataFrame()
            
            # Query direta com joins
            query = session.query(
                Group.group_id,
                Group.creation,
                GroupMetadata.subject,
                GroupMetadata.group_size
            ).select_from(File).join(
                file_groups, File.file_id == file_groups.c.file_id
            ).join(
                Group, file_groups.c.group_id == Group.group_id
            ).outerjoin(
                GroupMetadata, Group.group_id == GroupMetadata.group_id
            ).filter(
                and_(
                    File.operation_id == current_op.operation_id,
                    File.target_id == target_obj.target_id,
                    File.file_type == 'DADOS'
                )
            ).distinct().order_by(Group.creation.desc())
            
            results = query.all()
            print(f"🔍 {len(results)} grupos encontrados")
            
            # Criar DataFrame
            data = []
            for r in results:
                data.append({
                    'group_id': r.group_id,
                    'subject': r.subject or '-',
                    'group_size': r.group_size or 'N/A',
                    'creation': r.creation.strftime('%d/%m/%Y %H:%M:%S') if r.creation else 'N/A'
                })
            
            return pd.DataFrame(data)
            
    except Exception as e:
        print(f"❌ ERRO: {e}")
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
            target_groups_options = get_targets(nome_operacao)
            target_groups_options.insert(0, '')
            
            if not target_groups_options:
                st.warning("Nenhum alvo encontrado para esta operação.")
                target_groups = None
                date_message = None

            st.write('')
            target_groups = st.selectbox(
                "Selecione um telefone:", 
                options=target_groups_options, 
                placeholder='Telefone',
                index=0
            )
            # Botão para buscar agenda
            btn_get_messages = st.button(
                "Buscar grupos",
                type="primary",
                use_container_width=True
            )


################  LÓGICA CENTRAL  ###############
################  LÓGICA CENTRAL  ###############
################  LÓGICA CENTRAL  ###############

nome_operacao = get_operacao()

if not nome_operacao:
    st.error("Por favor, selecione uma Operação para habilitar os filtros na barra lateral.", icon="🚨")
    st.error("Administração > Configurações > Selecionar operação.", icon="🚨")
    st.stop()

st.subheader("Análise de Grupos", divider='red')

# Verificar se o botão foi clicado e se os dados estão disponíveis
if 'btn_get_messages' in locals() and btn_get_messages and 'target_groups' in locals():
    if target_groups and target_groups != '':
        
        # Mostrar spinner enquanto processa
        with st.spinner('Buscando grupos do target...'):
            # Chamar a função e capturar o resultado
            df_groups = get_groups_data(target_phone=target_groups)
        
        # Proteção contra None
        if df_groups is None:
            df_groups = pd.DataFrame()
        
        if not df_groups.empty:
            st.markdown("""
    <style>
    /* Centralizar métricas */
    div[data-testid="stMetric"] {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        padding: 10px;
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
            
            # Métricas resumidas no topo
            col1, col2, col3, col4 = st.columns(4)
            
            with col1:
                st.metric("👥 Total de Grupos", len(df_groups))
            
            with col2:
                # Grupos com nome
                grupos_com_nome = len(df_groups[df_groups['subject'] != '-'])
                st.metric("📝 Com Nome", grupos_com_nome)
            
            with col3:
                # Grupos -
                grupos_sem_nome = len(df_groups[df_groups['subject'] == '-'])
                st.metric("❓ Sem Nome", grupos_sem_nome)
            
            with col4:
                # Média de participantes (quando disponível)
                grupos_com_size = df_groups[df_groups['group_size'] != 'N/A']
                if not grupos_com_size.empty:
                    avg_size = grupos_com_size['group_size'].astype(int).mean()
                    st.metric("👤 Média Participantes", f"{avg_size:.0f}")
                else:
                    st.metric("👤 Média Participantes", "N/A")
            
            
            # Exibir o DataFrame
            st.dataframe(
                df_groups, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "group_id": st.column_config.TextColumn(
                        "🆔 ID do Grupo",
                        help="Identificador único do grupo",
                        width="medium"
                    ),
                    "subject": st.column_config.TextColumn(
                        "📝 Nome do Grupo", 
                        help="Nome/subject do grupo",
                        width="medium"
                    ),
                    "group_size": st.column_config.TextColumn(
                        "👥 Participantes",
                        help="Número de participantes no grupo",
                        width="medium"
                    ),
                    "creation": st.column_config.TextColumn(
                        "📅 Criado em",
                        help="Data de criação do grupo",
                        width="medium"
                    )
                }
            )
        else:
            st.info("👥 Nenhum grupo encontrado para este alvo.", icon="ℹ️")
    else:
        st.info("📱 Por favor, selecione um telefone na barra lateral para buscar os grupos.", icon="ℹ️")
else:
    st.info("🔍 Configure o telefone na barra lateral e clique em 'Buscar grupos' para ver os grupos.", icon="ℹ️")
