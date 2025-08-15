import streamlit as st
from settings import get_operacao, PROJECT_ROOT
from db.models import Operation, File, Message, file_contacts, Contact, operation_targets, Target
from db.session import get_session
import pandas as pd
import os


################  FUNÇÕES PARA CONSULTA  ###############
################  FUNÇÕES PARA CONSULTA  ###############
################  FUNÇÕES PARA CONSULTA  ###############

def get_operation_data(nome_operacao):
    '''Buscar dados da operação pelo nome'''
    
    if not nome_operacao:
        return None
        
    with get_session() as session:
        op = session.query(Operation).filter(Operation.name == nome_operacao).first()    
        if op:
            return {
                'id': op.operation_id, 
                'description': op.description, 
                'created_at': op.created_at.strftime('%d/%m/%Y %H:%M:%S') if op.created_at else 'N/A'
            }
        else:
            return None
        

def get_operation_metrics(nome_operacao):
    '''Buscar todas as métricas da operação'''
    
    if not nome_operacao:
        return None
        
    with get_session() as session:
        from sqlalchemy import func, distinct
        
        # Buscar operação
        operation = session.query(Operation).filter(Operation.name == nome_operacao).first()
        
        if not operation:
            return None
            
        op_id = operation.operation_id
        
        # 1. Número de Targets (Alvos)
        num_targets = session.query(func.count(Target.target_id)).join(
            operation_targets, Target.target_id == operation_targets.c.target_id
        ).filter(operation_targets.c.operation_id == op_id).scalar()
        
        # 2. Número de Files (Arquivos)
        num_files = session.query(func.count(File.file_id)).filter(
            File.operation_id == op_id
        ).scalar()
        
        # 3. Número de Grupos únicos
        num_groups = session.query(func.count(distinct(Message.group_id))).join(
            File, Message.file_id == File.file_id
        ).filter(
            File.operation_id == op_id,
            Message.group_id.isnot(None)
        ).scalar()
        
        # 4. Número total de Mensagens
        num_messages = session.query(func.count(Message.message_id)).join(
            File, Message.file_id == File.file_id
        ).filter(File.operation_id == op_id).scalar()
        
        # 5. Número de Contatos únicos
        num_contacts = session.query(func.count(distinct(Contact.contact_phone))).join(
            file_contacts, Contact.contact_id == file_contacts.c.contact_id
        ).join(
            File, file_contacts.c.file_id == File.file_id
        ).filter(File.operation_id == op_id).scalar()
        
        # 6. Período de dados (primeira e última mensagem)
        date_range = session.query(
            func.min(Message.timestamp).label('start_date'),
            func.max(Message.timestamp).label('end_date')
        ).join(File, Message.file_id == File.file_id).filter(
            File.operation_id == op_id
        ).first()
        
        # 7. Número de IPs únicos
        num_ips = session.query(func.count(distinct(Message.sender_ip))).join(
            File, Message.file_id == File.file_id
        ).filter(
            File.operation_id == op_id,
            Message.sender_ip.isnot(None)
        ).scalar()
        
        # 8. Files por status
        files_by_status = session.query(
            File.process_status,
            func.count(File.file_id).label('count')
        ).filter(File.operation_id == op_id).group_by(File.process_status).all()
        
        # 9. Mensagens por tipo
        messages_by_type = session.query(
            Message.message_type,
            func.count(Message.message_id).label('count')
        ).join(File, Message.file_id == File.file_id).filter(
            File.operation_id == op_id
        ).group_by(Message.message_type).all()
        
        # 10. Top 5 targets mais ativos
        top_targets = session.query(
            Target.target,
            func.count(Message.message_id).label('msg_count')
        ).join(
            operation_targets, Target.target_id == operation_targets.c.target_id
        ).join(
            File, File.target_id == Target.target_id
        ).join(
            Message, Message.file_id == File.file_id
        ).filter(
            operation_targets.c.operation_id == op_id
        ).group_by(Target.target).order_by(func.count(Message.message_id).desc()).limit(5).all()
        
        return {
            'num_targets': num_targets or 0,
            'num_files': num_files or 0,
            'num_groups': num_groups or 0,
            'num_messages': num_messages or 0,
            'num_contacts': num_contacts or 0,
            'num_ips': num_ips or 0,
            'date_range': date_range,
            'files_by_status': files_by_status,
            'messages_by_type': messages_by_type,
            'top_targets': top_targets
        }
    

################  LÓGICA SIDEBAR  ###############
################  LÓGICA SIDEBAR  ###############
################  LÓGICA SIDEBAR  ###############

with st.sidebar:
    st.markdown('''<style>
  div[data-testid="stSidebarHeader"] > img, div[data-testid="collapsedControl"] > img {
      margin-top: 4rem;
      height: 10rem;
      width: auto;
  }
  
  div[data-testid="stSidebarHeader"], div[data-testid="stSidebarHeader"] > *,
  div[data-testid="collapsedControl"], div[data-testid="collapsedControl"] > * {
      display: flex;
      align-items: center;
  }
</style>''', unsafe_allow_html=True)
    logo_path = os.path.join(PROJECT_ROOT, 'logo.png')
    st.logo(image=logo_path, icon_image=logo_path, size="large")
    st.write('')
    st.write('')
    op_data = None
    nome_operacao = get_operacao()

    if nome_operacao:
        op_data = get_operation_data(nome_operacao)

    if not op_data:
        op_data = {'id': None, 'description': None, 'created_at': None}

    description = op_data.get("description", "")
    data = op_data.get("created_at", "")
    if data:
        data = data[:10]

    st.header('Dashboard', divider='red')
    st.header(f'Operação:')
    st.markdown(f'_{nome_operacao}_')
    st.header(f'Descrição:')
    st.markdown(f'_{description}_')
    st.header(f'Criada em:')
    st.markdown(f'_{data}_')

    if nome_operacao:
        print('teste')


################## lÓGICA DA ÁREA CENTRAL ##################
################## lÓGICA DA ÁREA CENTRAL ##################
################## lÓGICA DA ÁREA CENTRAL ##################

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
    
    /* Centralizar métricas */
    div[data-testid="stMetric"] {
        display: flex;
        flex-direction: column;
        align-items: center;
        text-align: center;
        padding: 15px;
        border-radius: 10px;
        background: linear-gradient(135deg, #B0E0E6 0%, #5F9EA0 100%) !important;
        color: black;
        box-shadow: 0 4px 6px rgba(0, 0, 0, 0.1);
        transition: transform 0.3s ease;
    }
    
    div[data-testid="stMetric"]:hover {
        transform: translateY(-5px);
        box-shadow: 0 8px 15px rgba(0, 0, 0, 0.2);
    }
    
    /* Labels das métricas */
    div[data-testid="stMetricLabel"] {
        text-align: center !important;
        color: black !important;
        font-weight: bold !important;
        font-size: 1.1rem !important;
    }
    
    /* Valores das métricas */
    div[data-testid="stMetricValue"] {
        text-align: center !important;
        color: black !important;
        font-size: 2rem !important;
        font-weight: bold !important;
    }
    
    /* Responsivo */
    @media (max-width: 768px) {
        div[data-testid="stMainBlockContainer"] {
            padding-left: 20px !important;
            padding-right: 20px !important;
        }
        
        div[data-testid="stMetricLabel"] {
            font-size: 0.9rem !important;
        }
        
        div[data-testid="stMetricValue"] {
            font-size: 1.5rem !important;
        }
    }
</style>''', unsafe_allow_html=True)

nome_operacao = get_operacao()

if not nome_operacao:
    st.error("Por favor, selecione uma Operação para habilitar os filtros na barra lateral.", icon="🚨")
    st.error("Administração > Configurações > Selecionar operação.", icon="🚨")
    st.stop()

# BUSCAR MÉTRICAS DA OPERAÇÃO
with st.spinner('Carregando métricas da operação...'):
    metrics = get_operation_metrics(nome_operacao)

if not metrics:
    st.error("❌ Não foi possível carregar as métricas da operação.")
    st.stop()

# MÉTRICAS PRINCIPAIS (4 colunas)
st.markdown("### 📈 Métricas Principais")
col1, col2, col3, col4 = st.columns(4)

with col1:
    st.metric("🎯 Alvos", metrics['num_targets'])

with col2:
    st.metric("📁 Número de Pacotes", metrics['num_files'])

with col3:
    st.metric("👥 Total de Grupos", metrics['num_groups'])

with col4:
    st.metric("💬 Total de Mensagens", f"{metrics['num_messages']:,}")

st.write("")

# MÉTRICAS SECUNDÁRIAS (3 colunas)
col1, col2, col3 = st.columns(3)

with col1:
    st.metric("📞 Contatos", f"{metrics['num_contacts']:,}")

with col2:
    st.metric("🌐 IPs Únicos", metrics['num_ips'])

with col3:
    # Calcular média de mensagens por alvo
    avg_messages = metrics['num_messages'] / metrics['num_targets'] if metrics['num_targets'] > 0 else 0
    st.metric("📊 Média de mensagens por alvo", f"{avg_messages:,.0f}")

st.write("")

# INFORMAÇÕES DE PERÍODO
if metrics['date_range'] and metrics['date_range'].start_date and metrics['date_range'].end_date:
    start_date = metrics['date_range'].start_date.strftime('%d/%m/%Y')
    end_date = metrics['date_range'].end_date.strftime('%d/%m/%Y')
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("📅 Data Inicial", start_date)
    with col2:
        st.metric("📅 Data Final", end_date)
    with col3:
        # Calcular duração
        duration = (metrics['date_range'].end_date - metrics['date_range'].start_date).days + 1
        st.metric("⏱️ Duração", f"{duration} dias")

st.markdown("---")

# GRÁFICOS E ANÁLISES DETALHADAS
col1, col2 = st.columns(2)

with col1:
    st.markdown("### 📊 Status dos Arquivos")
    if metrics['files_by_status']:
        
        status_df = pd.DataFrame([
            {'Status': status or 'Sem Status', 'Quantidade': count} 
            for status, count in metrics['files_by_status']
        ])
        
        st.bar_chart(status_df.set_index('Status'))
    else:
        st.info("Nenhum dado de status encontrado.")

with col2:
    st.markdown("### 💬 Tipos de Mensagem")
    if metrics['messages_by_type']:
        type_df = pd.DataFrame([
            {'Tipo': msg_type or 'Sem Tipo', 'Quantidade': count} 
            for msg_type, count in metrics['messages_by_type']
        ])
        
        st.bar_chart(type_df.set_index('Tipo'))
    else:
        st.info("Nenhum dado de tipo encontrado.")

# TOP TARGETS MAIS ATIVOS
st.markdown("### 🏆 Top 5 Alvos Mais Ativos")
if metrics['top_targets']:
    targets_df = pd.DataFrame([
        {'Alvo': target, 'Mensagens': count} 
        for target, count in metrics['top_targets']
    ])
    
    st.dataframe(
        targets_df, 
        use_container_width=True,
        hide_index=True,
        column_config={
            "Alvo": st.column_config.TextColumn("📱 Alvo", width="medium"),
            "Mensagens": st.column_config.NumberColumn(
                "💬 Total de Mensagens", 
                format="%d",
                width="small"
            )
        }
    )
else:
    st.info("Nenhum alvo ativo encontrado.")

# RESUMO FINAL
st.markdown("### 📋 Resumo Final ")

col1, col2, col3 = st.columns(3)

with col1:
    st.markdown(f"""
    
    **📊 Dados Coletados:**
    - 👥 **{metrics['num_targets']}** alvos monitorados
    - 📁 **{metrics['num_files']}** arquivos processados
    - 💬 **{metrics['num_messages']:,}** mensagens analisadas
    - 🌐 **{metrics['num_ips']}** IPs únicos identificados
    """)

with col2:
    if metrics['date_range'] and metrics['date_range'].start_date:
        st.markdown(f"""
        **📅 Período de Análise:**
        - 🟢 **Início:** {start_date}
        - 🔴 **Fim:** {end_date}
        - ⏱️ **Duração:** {duration} dias
        """)

with col3:
    if metrics['date_range'] and metrics['date_range'].start_date:
        st.markdown(f"""
        
        **📈 Produtividade:**
        - 📊 **{avg_messages:,.0f}** mensagens por alvo
        - 💬 **{metrics['num_messages']/duration if duration > 0 else 0:,.0f}** mensagens por dia
        """)

# ALERTA DE STATUS
if metrics['num_messages'] == 0:
    st.error("⚠️ **ATENÇÃO:** Nenhuma mensagem encontrada para esta operação!")
elif metrics['num_targets'] == 0:
    st.warning("⚠️ **AVISO:** Nenhum alvo cadastrado para esta operação!")
