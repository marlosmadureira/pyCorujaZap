import streamlit as st
import pandas as pd
from sqlalchemy import func, and_, case
from settings import get_operacao, PROJECT_ROOT
from db.session import get_session
from db.models import Operation, Target, Message, File, operation_targets, MessageRecipient, GroupMetadata
import os
from datetime import datetime


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


def get_date_messages(nome_operacao, target_messages):
    ''' Retorna uma tupla contendo as datas do primeiro e último registro de mensagens para o alvo em questão.'''
    
    if not nome_operacao or not target_messages:
        return None, None
    
    with get_session() as session:
                
        # Buscar a operação pelo nome
        current_op = session.query(Operation).filter(Operation.name == nome_operacao).first()
        
        if not current_op:
            return None, None
        
        # Buscar o target_id específico dentro do contexto da operação
        # Usa a tabela operation_targets para garantir que o target pertence à operação
        target_in_operation = session.query(Target.target_id).join(
            operation_targets,
            Target.target_id == operation_targets.c.target_id
        ).filter(
            and_(
                operation_targets.c.operation_id == current_op.operation_id,
                Target.target == target_messages
            )
        ).first()
        
        if not target_in_operation:
            return None, None  # Target não encontrado nesta operação
        
        target_id = target_in_operation.target_id
        
        # Query para buscar min e max timestamp das mensagens
        # Usa as FKs compostas para garantir contexto de operação + target
        result = session.query(
            func.min(Message.timestamp).label('min_date'),
            func.max(Message.timestamp).label('max_date')
        ).select_from(Message).join(
            File, Message.file_id == File.file_id
        ).filter(
            and_(
                File.operation_id == current_op.operation_id,  # FK composta: operação
                File.target_id == target_id                    # FK composta: target
            )
        ).first()
        
        if result and result.min_date and result.max_date:
            return result.min_date.date(), result.max_date.date()
        else:
            return None, None


def get_data_messages(**kwargs):
    '''Versão CORRIGIDA com conversas bidirecionais e contagem única de mensagens'''
    
    target_messages = kwargs.get('target_messages')
    date_message = kwargs.get('date_message')
    nome_operacao = get_operacao()
    
    if not nome_operacao or not target_messages:
        return pd.DataFrame()
    
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
                Target.target == target_messages
            )
        ).first()
        
        if not target_in_operation:
            return pd.DataFrame()
        
        target_id = target_in_operation.target_id
        
        # Filtro de data
        date_filter = True
        if date_message:
            if isinstance(date_message, (tuple, list)) and len(date_message) == 2:
                start_date, end_date = date_message
                
                # GARANTIR que são objetos date
                if isinstance(start_date, datetime):
                    start_date = start_date.date()
                if isinstance(end_date, datetime):
                    end_date = end_date.date()
                
                date_filter = and_(
                    func.date(Message.timestamp) >= start_date,
                    func.date(Message.timestamp) <= end_date
                )
            else:
                # Data única
                single_date = date_message
                if isinstance(single_date, datetime):
                    single_date = single_date.date()
                    
                date_filter = func.date(Message.timestamp) >= single_date
        
        # Query com DISTINCT para evitar duplicatas por recipients
        query = session.query(
            Message.message_id,  # Inclui message_id para garantir unicidade
            Message.sender,
            MessageRecipient.recipient_phone.label('recipient'),
            Message.group_id,
            case(
                (Message.sender == target_messages, 1),
                else_=0
            ).label('enviada'),
            case(
                (MessageRecipient.recipient_phone == target_messages, 1),
                else_=0
            ).label('recebida')
        ).select_from(Message).join(
            File, Message.file_id == File.file_id
        ).join(
            MessageRecipient, Message.message_id == MessageRecipient.message_id
        ).filter(
            and_(
                File.operation_id == current_op.operation_id,
                File.target_id == target_id,
                date_filter
            )
        )
        
        results = query.all()
        
        if not results:
            return pd.DataFrame()
        
        # Para grupos: uma mensagem pode ter múltiplos recipients, mas conta como 1 só
        unique_messages = {}
        
        for r in results:
            message_key = r.message_id
            
            if message_key not in unique_messages:
                unique_messages[message_key] = r
            else:
                # Se já existe, manter apenas se o target está envolvido
                existing = unique_messages[message_key]
                if r.enviada == 1 or r.recebida == 1:  # Target está envolvido nesta linha
                    unique_messages[message_key] = r
        
        # Converter de volta para lista
        results = list(unique_messages.values())
                
        # Buscar metadata dos grupos
        group_ids = [r.group_id for r in results if r.group_id]
        group_metadata = {}
        
        if group_ids:
            unique_group_ids = list(set(group_ids))
            metadata_query = session.query(
                GroupMetadata.group_id,
                GroupMetadata.subject
            ).filter(GroupMetadata.group_id.in_(unique_group_ids))
            
            for meta in metadata_query.all():
                group_metadata[meta.group_id] = meta.subject
        
        # Conversão para conversas bidirecionais (mesmo código anterior)
        data = []
        for r in results:
            if r.group_id:  # É mensagem de grupo
                group_name = group_metadata.get(r.group_id, 'Pendente')
                
                if r.enviada == 1:  # Target enviou para o grupo
                    conversa_key = f"GRUPO_{r.group_id}"
                    contact = 'Grupo'
                else:  # Target recebeu do grupo
                    conversa_key = f"GRUPO_{r.group_id}"
                    contact = 'Grupo'
                
                group_key = r.group_id
                
            else:  # Conversa particular
                group_name = '-'
                
                # Chave única para conversas bidirecionais
                if r.sender == target_messages:
                    # Target enviou
                    contact = r.recipient
                else:
                    # Target recebeu
                    contact = r.sender
                
                conversa_key = f"PARTICULAR_{contact}"
                group_key = 'CONVERSA_PARTICULAR'
            
            data.append({
                'target': target_messages,
                'contact': contact,
                'conversa_key': conversa_key,
                'group_id': group_key,
                'nome_grupo': group_name,
                'quantidade_enviadas': r.enviada,
                'quantidade_recebidas': r.recebida
            })
        
        df = pd.DataFrame(data)
        
        # Agrupamento por conversa_key
        df_grouped = df.groupby(['target', 'contact', 'conversa_key', 'group_id', 'nome_grupo']).agg({
            'quantidade_enviadas': 'sum',
            'quantidade_recebidas': 'sum'
        }).reset_index()
        
        # Adicionar coluna de soma total
        df_grouped['total_mensagens'] = df_grouped['quantidade_enviadas'] + df_grouped['quantidade_recebidas']
        
        # Ordenar por total de mensagens (maior primeiro)
        df_grouped = df_grouped.sort_values('total_mensagens', ascending=False).reset_index(drop=True)
        
        # Limpeza final: Ajustar colunas para o formato desejado
        df_final = pd.DataFrame({
            'sender': df_grouped['target'],
            'recipient': df_grouped['contact'],
            'group_id': df_grouped['group_id'],
            'nome_grupo': df_grouped['nome_grupo'],
            'quantidade_enviadas': df_grouped['quantidade_enviadas'],
            'quantidade_recebidas': df_grouped['quantidade_recebidas'],
            'total_mensagens': df_grouped['total_mensagens']
        })
        
        # Voltar None para conversas particulares
        df_final.loc[df_final['group_id'] == 'CONVERSA_PARTICULAR', 'group_id'] = None
                
        return df_final


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
        target_messages_options = get_targets(nome_operacao)
        target_messages_options.insert(0, '')
        
        if not target_messages_options:
            st.warning("Nenhum alvo encontrado para esta operação.")
            target_messages = None
            date_message = None
        
        target_messages = st.selectbox(
            "Selecione um telefone:", 
            options=target_messages_options, 
            placeholder='Telefone',
            index=0
        )

        date_messages_tuple = get_date_messages(nome_operacao, target_messages)
        
        if date_messages_tuple == (None, None) and target_messages != '':
            st.warning("Nenhuma mensagem encontrada para este alvo.")

        if date_messages_tuple and date_messages_tuple[0] and date_messages_tuple[1]:
            date_message = st.date_input(
                "Selecione o intervalo:", 
                value=date_messages_tuple,
                min_value=date_messages_tuple[0],
                max_value=date_messages_tuple[1],
                format="DD/MM/YYYY"
            )
            
            # Definir o dicionário de filtros
            message_filter = {
                'target_messages': target_messages,
                'date_message': date_message
            }

            # Botão para buscar mensagens
            btn_get_messages = st.button(
                "Buscar mensagens",
                type="primary",
                use_container_width=True
            )
            
    else:
        st.warning("Nenhuma mensagem encontrada para este alvo.")
        date_message = None


################  LÓGICA CENTRAL  ###############
################  LÓGICA CENTRAL  ###############
################  LÓGICA CENTRAL  ###############

nome_operacao = get_operacao()

if not nome_operacao:
    st.error("Por favor, selecione uma Operação para habilitar os filtros na barra lateral.", icon="🚨")
    st.error("Administração > Configurações > Selecionar operação.", icon="🚨")
    st.stop()

st.subheader("Análise de Mensagens", divider='red')

# Verificar se o botão foi clicado e se os dados estão disponíveis
if 'btn_get_messages' in locals() and btn_get_messages and 'target_messages' in locals() and 'date_message' in locals():
    if target_messages and target_messages != '' and date_message:
        
        # Prepara o filtro
        message_filter = {
            'target_messages': target_messages,
            'date_message': date_message
        }
        
        # Mostrar spinner enquanto processa
        with st.spinner('Buscando mensagens...'):
            # CHAMAR A FUNÇÃO E CAPTURAR O RESULTADO
            df_messages = get_data_messages(**message_filter)
        
        if not df_messages.empty:
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
                st.metric("Total de Conversas", len(df_messages))
            with col2:
                st.metric("Mensagens Enviadas", df_messages['quantidade_enviadas'].sum())
            with col3:
                st.metric("Mensagens Recebidas", df_messages['quantidade_recebidas'].sum())
            with col4:
                st.metric("Total de Mensagens", df_messages['total_mensagens'].sum())
            
            
            # Exibir o DataFrame com configurações de centralização
            st.dataframe(
                df_messages, 
                use_container_width=True,
                hide_index=True,
                column_config={
                    "sender": st.column_config.TextColumn(
                        "Remetente",
                        help="Número do remetente",
                        width=104
                    ),
                    "recipient": st.column_config.TextColumn(
                        "Destinatário", 
                        help="Número do destinatário",
                        width=104
                    ),
                    "group_id": st.column_config.TextColumn(
                        "ID do Grupo",
                        help="Identificador do grupo",
                        width=140
                    ),
                    "nome_grupo": st.column_config.TextColumn(
                        "Nome do Grupo",
                        help="Nome ou descrição do grupo",
                        width=250
                    ),
                    "quantidade_enviadas": st.column_config.NumberColumn(
                        "Enviadas",
                        help="Quantidade de mensagens enviadas pelo alvo",
                        format="%d",  # ✅ Formato numérico sem decimais
                        width=62
                    ),
                    "quantidade_recebidas": st.column_config.NumberColumn(
                        "Recebidas", 
                        help="Quantidade de mensagens recebidas pelo alvo",
                        format="%d",  # ✅ Formato numérico sem decimais
                        width=67
                    ),
                    "total_mensagens": st.column_config.NumberColumn(
                        "Total",
                        help="Total de mensagens na conversa",
                        format="%d",  # ✅ Formato numérico sem decimais
                        width=60
                    )
                }
            )
        else:
            st.info("Nenhuma mensagem encontrada para os filtros selecionados.", icon="ℹ️")
    else:
        st.info("Por favor, selecione um telefone e período para buscar mensagens.", icon="ℹ️")
else:
    st.info("Configure os filtros na barra lateral e clique em 'Buscar mensagens' para ver os resultados.", icon="ℹ️")
