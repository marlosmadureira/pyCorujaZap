import streamlit as st
import pandas as pd
import plotly.express as px
import folium
from streamlit_folium import st_folium
from sqlalchemy import func
from settings import get_operacao, get_current_op_id, PROJECT_ROOT
from db.session import get_session
from db.models import Message, File, IP
import os
from datetime import date


################  FUNÇÕES DE CONSULTA  ###############
################  FUNÇÕES DE CONSULTA  ###############
################  FUNÇÕES DE CONSULTA  ###############

def get_senders(operation_id):
    '''Retorna uma lista de senders únicos baseado na operação corrente'''
    try:
        with get_session() as session:
            senders = session.query(Message.sender).join(
                File, Message.file_id == File.file_id
            ).filter(
                File.operation_id == operation_id,
                Message.sender.isnot(None),
                Message.sender != ''
            ).distinct().order_by(Message.sender).all()
            
            return [sender[0] for sender in senders if sender[0]]
    except Exception as e:
        print(f"❌ Erro ao buscar senders: {e}")
        return []


def get_date_for_ips(operation_id, sender_for_ip):
    '''Retorna uma tupla contendo as datas do primeiro e último registro de mensagens para o sender na operação atual'''
    try:
        if not sender_for_ip or sender_for_ip == '':
            return (None, None)
            
        with get_session() as session:
            dates = session.query(
                func.min(func.date(Message.timestamp)),
                func.max(func.date(Message.timestamp))
            ).join(
                File, Message.file_id == File.file_id
            ).filter(
                File.operation_id == operation_id,
                Message.sender == sender_for_ip,
                Message.timestamp.isnot(None)
            ).first()
            
            if dates and dates[0] and dates[1]:
                return (dates[0], dates[1])
            else:
                return (None, None)
    except Exception as e:
        print(f"❌ Erro ao buscar datas para IPs: {e}")
        return (None, None)


def get_ip_data_for_map(operation_id, sender_for_ip, date_range):
    '''Retorna dados de IPs para plotagem no mapa baseado na operação corrente'''
    try:
        # Validar date_range
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        elif hasattr(date_range, '__iter__') and len(date_range) == 2:
            start_date, end_date = date_range[0], date_range[1]
        else:
            return []
        
        with get_session() as session:
            # Query simplificada que funciona
            messages_with_ip = session.query(
                Message.sender,
                Message.sender_ip,
                Message.timestamp,
                IP.city,
                IP.region_name,
                IP.country,
                IP.latitude,
                IP.longitude,
                IP.isp,
                IP.org
            ).join(
                File, Message.file_id == File.file_id
            ).join(
                IP, Message.sender_ip == IP.sender_ip
            ).filter(
                File.operation_id == operation_id,
                Message.sender == sender_for_ip,
                Message.sender_ip.isnot(None),
                Message.sender_ip != '',
                func.date(Message.timestamp) >= start_date,
                func.date(Message.timestamp) <= end_date,
                IP.latitude.isnot(None),
                IP.longitude.isnot(None)
            ).all()
            
            # Agrupar dados manualmente
            from collections import defaultdict
            grouped_data = defaultdict(lambda: {'count': 0, 'data': None})
            
            for row in messages_with_ip:
                key = (row.sender_ip, row.city, row.country, row.latitude, row.longitude)
                grouped_data[key]['count'] += 1
                if grouped_data[key]['data'] is None:
                    grouped_data[key]['data'] = row
            
            # Converter para formato esperado
            result = []
            for key, value in grouped_data.items():
                row_data = value['data']
                result.append({
                    'sender': row_data.sender,
                    'sender_ip': row_data.sender_ip,
                    'city': row_data.city,
                    'region_name': row_data.region_name,
                    'country': row_data.country,
                    'latitude': float(row_data.latitude),
                    'longitude': float(row_data.longitude),
                    'isp': row_data.isp,
                    'org': row_data.org,
                    'message_count': value['count']
                })
            
            return result
            
    except Exception as e:
        print(f"❌ Erro ao buscar dados de IP para mapa: {e}")
        return []


def get_detailed_messages_by_ip(operation_id, sender_for_ip, date_range):
    '''Retorna mensagens detalhadas por IP para o dataframe'''
    try:
        if isinstance(date_range, tuple) and len(date_range) == 2:
            start_date, end_date = date_range
        elif hasattr(date_range, '__iter__') and len(date_range) == 2:
            start_date, end_date = date_range[0], date_range[1]
        else:
            return []
        
        with get_session() as session:
            messages = session.query(
                Message.message_id,
                Message.sender,
                Message.sender_ip,
                Message.timestamp,
                Message.sender_device,
                Message.message_type,
                IP.city,
                IP.region_name,
                IP.country,
                IP.latitude,
                IP.longitude,
                IP.isp,
                IP.org,
                IP.continent
            ).join(
                File, Message.file_id == File.file_id
            ).join(
                IP, Message.sender_ip == IP.sender_ip
            ).filter(
                File.operation_id == operation_id,
                Message.sender == sender_for_ip,
                Message.sender_ip.isnot(None),
                Message.sender_ip != '',
                func.date(Message.timestamp) >= start_date,
                func.date(Message.timestamp) <= end_date
            ).order_by(Message.timestamp.desc()).all()
            
            return messages
    except Exception as e:
        print(f"❌ Erro ao buscar mensagens detalhadas: {e}")
        return []


################  LÓGICA SIDEBAR  ###############
################  LÓGICA SIDEBAR  ###############
################  LÓGICA SIDEBAR  ###############

with st.sidebar:
    st.markdown('''<style>
    div[data-testid="stSidebarHeader"] > img, 
    div[data-testid="collapsedControl"] > img {
        margin-top: 1rem;
        height: 4rem;
        width: auto;
    }
    
    @media (min-width: 769px) {
        div[data-testid="stSidebarHeader"] > img, 
        div[data-testid="collapsedControl"] > img {
            margin-top: 4rem !important;
            height: 10rem !important;
        }
    }
    
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
    operation_id = get_current_op_id()
    
    st.header(f'Operação: {nome_operacao}', divider='red')

    # Filtros baseados na operação corrente
    if nome_operacao and operation_id:
        sender_options = get_senders(operation_id)
        
        if not sender_options:
            st.warning("Nenhum sender encontrado para esta operação.")
            sender_for_ip = None
            date_range = None
        else:
            sender_options.insert(0, '')
            
            st.write('')
            st.write('')
            sender_for_ip = st.selectbox(
                "📱 Selecione um telefone:", 
                options=sender_options, 
                placeholder='Escolha o telefone',
                index=0
            )

            if sender_for_ip and sender_for_ip != '':
                date_for_ip_tuple = get_date_for_ips(operation_id, sender_for_ip)
                
                if date_for_ip_tuple == (None, None):
                    st.warning("Nenhuma mensagem encontrada para este telefone.")
                    date_range = None
                else:
                    
                    date_range = st.date_input(
                        "📅 Selecione o intervalo:", 
                        value=date_for_ip_tuple,
                        min_value=date_for_ip_tuple[0],
                        max_value=date_for_ip_tuple[1],
                        format="DD/MM/YYYY"
                    )
                    
                    # Garantir que date_range seja uma tupla
                    if isinstance(date_range, date):
                        date_range = (date_range, date_range)
                    elif len(date_range) == 1:
                        date_range = (date_range[0], date_range[0])
            else:
                date_range = None
    else:
        sender_for_ip = None
        date_range = None


################  ÁREA CENTRAL  ###############
################  ÁREA CENTRAL  ###############
################  ÁREA CENTRAL  ###############

nome_operacao = get_operacao()
operation_id = get_current_op_id()

if not nome_operacao or not operation_id:
    st.error("Por favor, selecione uma Operação para habilitar os filtros na barra lateral.", icon="🚨")
    st.error("Administração > Configurações > Selecionar operação.", icon="🚨")
    st.stop()

st.header("🗺️ Geolocalização por IPs", divider='red')

# Verificar se todos os filtros estão preenchidos
if not sender_for_ip or sender_for_ip == '':
    st.info("📱 Selecione um telefone na barra lateral para visualizar os IPs no mapa.", icon="ℹ️")
    st.stop()

if not date_range:
    st.info("📅 Selecione um intervalo de datas na barra lateral.", icon="ℹ️")
    st.stop()

# Se o botão foi clicado ou se há filtros válidos, buscar e exibir dados
if sender_for_ip and date_range:
    
    with st.spinner("🔍 Buscando dados de geolocalização..."):
        ip_data = get_ip_data_for_map(operation_id, sender_for_ip, date_range)
        detailed_messages = get_detailed_messages_by_ip(operation_id, sender_for_ip, date_range)
    
    if not ip_data:
        st.warning("Nenhum dado de IP encontrado para os filtros selecionados.", icon="⚠️")
        st.info("💡 Verifique se os IPs foram enriquecidos com dados de geolocalização.")
        st.stop()
    

    # Configurar centro do mapa
    if ip_data:
        center_lat = sum(item['latitude'] for item in ip_data) / len(ip_data)
        center_lon = sum(item['longitude'] for item in ip_data) / len(ip_data)
    else:
        center_lat, center_lon = -15.7801, -47.9292  # Brasília como padrão

    # Definir cores baseadas na quantidade de mensagens
    max_messages = max(item['message_count'] for item in ip_data) if ip_data else 1

    def get_color(message_count):
        ratio = message_count / max_messages
        if ratio > 0.8:
            return 'red'
        elif ratio > 0.6:
            return 'orange'
        elif ratio > 0.4:
            return 'yellow'
        elif ratio > 0.2:
            return 'lightgreen'
        else:
            return 'green'

    # Configurar centro do mapa
    if ip_data and len(ip_data) > 0:
        # Calcular centro geográfico
        latitudes = [item['latitude'] for item in ip_data if item['latitude'] is not None]
        longitudes = [item['longitude'] for item in ip_data if item['longitude'] is not None]
        
        if latitudes and longitudes:
            center_lat = sum(latitudes) / len(latitudes)
            center_lon = sum(longitudes) / len(longitudes)
            
            # Calcular bounds para melhor visualização
            min_lat, max_lat = min(latitudes), max(latitudes)
            min_lon, max_lon = min(longitudes), max(longitudes)
            
            # Determinar zoom baseado na dispersão dos pontos
            lat_range = max_lat - min_lat
            lon_range = max_lon - min_lon
            max_range = max(lat_range, lon_range)
            
            if max_range < 0.01:
                zoom_level = 12  # Pontos muito próximos
            elif max_range < 0.1:
                zoom_level = 10
            elif max_range < 1:
                zoom_level = 8
            elif max_range < 5:
                zoom_level = 6
            else:
                zoom_level = 4   # Pontos muito espalhados
        else:
            center_lat, center_lon = -15.7801, -47.9292  # Brasília como padrão
            zoom_level = 6
    else:
        center_lat, center_lon = -15.7801, -47.9292  # Brasília como padrão
        zoom_level = 6


    # Criar mapa base com configurações otimizadas
    m = folium.Map(
        location=[center_lat, center_lon],
        zoom_start=zoom_level,
        tiles="OpenStreetMap",
        width='100%',
        height='600px'
    )

    # ADICIONAR MARKER CLUSTER
    from folium.plugins import MarkerCluster
    cluster = MarkerCluster(
        name="IPs Cluster",
        overlay=True,
        control=True,
        options={
            'disableClusteringAtZoom': 15,  # Desagrupar em zoom alto
            'maxClusterRadius': 50,         # Raio máximo do cluster
            'spiderfyOnMaxZoom': True,      # Expandir em zoom máximo
            'showCoverageOnHover': False,   # Não mostrar área de cobertura
            'zoomToBoundsOnClick': True     # Zoom ao clicar no cluster
        }
    ).add_to(m)

    # Adicionar marcadores com cluster
    for i, item in enumerate(ip_data):
        
        # Popup com informações detalhadas
        popup_html = f"""
        <div style="width: 320px; font-family: Arial, sans-serif;">
            <div style="background: linear-gradient(135deg, #B0E0E6 0%, #5F9EA0 100%); 
                        color: black; padding: 12px; border-radius: 8px 8px 8px 8px; margin: 10px -5px -10px -10px;">
                <h3 style="margin: 0; font-size: 16px; text-align: center;"><b>{item['sender_ip']}</b></h3>
            </div>
            <div style="padding: 8px; line-height: 1.3; margin-left: -12px">
                <p style="margin: 6px 0;"><b>Localização:</b> {item['city']}, {item['country']}</p>
                <p style="margin: 6px 0;"><b>ISP:</b> {item['isp'] or 'N/A'}</p>
                <p style="margin: 6px 0;"><b>Organização:</b> {item['org'] or 'N/A'}</p>
                <p style="margin: 6px 0;"><b>Mensagens:</b> {item['message_count']}</p>
                <p style="margin: 6px 0;"><b>Coordenadas:</b> {item['latitude']:.4f}, {item['longitude']:.4f}</p>
            </div>
        </div>
        """
        
        # Criar popup
        popup = folium.Popup(popup_html, max_width=340)
        
        # Definir cor baseada na intensidade de mensagens
        ratio = item['message_count'] / max_messages
        
        if ratio > 0.8:
            icon = folium.Icon(color='red', icon='map-marker', prefix='fa')
        elif ratio > 0.6:
            icon = folium.Icon(color='orange', icon='map-marker', prefix='fa')
        elif ratio > 0.4:
            icon = folium.Icon(color='beige', icon='map-marker', prefix='fa')
        elif ratio > 0.2:
            icon = folium.Icon(color='green', icon='map-marker', prefix='fa')
        else:
            icon = folium.Icon(color='blue', icon='map-marker', prefix='fa')
        
        # Verificar se as coordenadas são válidas
        if -90 <= item['latitude'] <= 90 and -180 <= item['longitude'] <= 180:
            # Adicionar marcador ao cluster
            folium.Marker(
                location=[item['latitude'], item['longitude']],
                popup=popup,
                icon=icon,
                tooltip=f"IP: {item['sender_ip']} | {item['city']}, {item['country']} | {item['message_count']} mensagens"
            ).add_to(cluster)
        else:
            st.warning(f"⚠️ Coordenadas inválidas para IP {item['sender_ip']}: {item['latitude']}, {item['longitude']}")

    # ADICIONAR CONTROLE DE CAMADAS
    folium.LayerControl().add_to(m)

    # AJUSTAR VISUALIZAÇÃO PARA MOSTRAR TODOS OS PONTOS
    if ip_data and len(ip_data) > 1:
        # Criar bounds para incluir todos os pontos
        coordinates = [[item['latitude'], item['longitude']] for item in ip_data 
                       if -90 <= item['latitude'] <= 90 and -180 <= item['longitude'] <= 180]
        
        if coordinates:
            m.fit_bounds(coordinates, padding=(20, 20))

    # Exibir mapa com configurações otimizadas
    map_data = st_folium(
        m, 
        width=None,  # Usar largura total do container
        height=600,
        returned_objects=["last_object_clicked"]
    )

    # LEGENDA E INFORMAÇÕES ABAIXO DO MAPA
    st.markdown("---")

    # Layout em 3 colunas para informações organizadas
    col_legend, col_info, col_stats = st.columns(3)

    with col_legend:
        st.markdown("#### 📊 Legenda dos Marcadores")
        st.markdown("**Intensidade de Atividade:**")
        
        # Criar legenda com ícones correspondentes ao cluster
        legend_items = [
            ("🔴", "Muito Alta", f"80-100% ({int(max_messages * 0.8)}-{max_messages})"),
            ("🟠", "Alta", f"60-80% ({int(max_messages * 0.6)}-{int(max_messages * 0.8)})"),
            ("🟡", "Média", f"40-60% ({int(max_messages * 0.4)}-{int(max_messages * 0.6)})"),
            ("🟢", "Baixa", f"20-40% ({int(max_messages * 0.2)}-{int(max_messages * 0.4)})"),
            ("🟢", "Muito Baixa", f"0-20% (1-{int(max_messages * 0.2)})")
        ]
        
        for emoji, label, range_text in legend_items:
            st.markdown(f"{emoji} {label} | {range_text}")
            # st.caption(f"{range_text}")
            # st.caption(f"*{style_desc}*")
            # st.write("")
        

    with col_info:
        st.markdown("#### 📍 Informações do Mapa")
        st.metric("🎯 IPs plotados", len(ip_data))
        st.metric("📊 Máx. mensagens por IP", max_messages)
        st.metric("📊 Min. mensagens por IP", min(item['message_count'] for item in ip_data))

    with col_stats:
        st.markdown("#### 🌍 Resumo Geográfico")
        unique_countries = len(set(item['country'] for item in ip_data))
        unique_cities = len(set(item['city'] for item in ip_data))
        total_messages = sum(item['message_count'] for item in ip_data)
        
        st.metric("🌍 Países únicos", unique_countries)
        st.metric("🏙️ Cidades únicas", unique_cities)
        st.metric("💬 Total de mensagens", total_messages)
    
    # ESTATÍSTICAS RESUMIDAS
    st.divider()
    st.subheader("📊 Estatísticas Resumidas")
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        unique_countries = len(set(item['country'] for item in ip_data))
        st.metric("🌍 Países únicos", unique_countries)
    
    with col2:
        unique_cities = len(set(item['city'] for item in ip_data))
        st.metric("🏙️ Cidades únicas", unique_cities)
    
    with col3:
        unique_isps = len(set(item['isp'] for item in ip_data if item['isp']))
        st.metric("📡 ISPs únicos", unique_isps)
    
    with col4:
        total_messages = sum(item['message_count'] for item in ip_data)
        st.metric("💬 Total de mensagens", total_messages)
    
    # GRÁFICOS DE ANÁLISE
    st.divider()
    st.subheader("📈 Análise por Localização")
    
    # Preparar dados para gráficos
    df_chart = pd.DataFrame(ip_data)
    
    col1, col2 = st.columns(2)
    
    with col1:
        # Gráfico de pizza por país
        country_data = df_chart.groupby('country')['message_count'].sum().reset_index()
        country_data = country_data.sort_values('message_count', ascending=False)
        
        if len(country_data) > 0:
            fig_country = px.pie(
                country_data,
                values='message_count',
                names='country',
                title="Distribuição de Mensagens por País",
                color_discrete_sequence=px.colors.qualitative.Set3
            )
            fig_country.update_traces(textposition='inside', textinfo='percent+label')
            st.plotly_chart(fig_country, use_container_width=True)
    
    with col2:
        # Gráfico de barras por ISP (top 10)
        isp_data = df_chart.groupby('isp')['message_count'].sum().reset_index()
        isp_data = isp_data.sort_values('message_count', ascending=False).head(10)
        
        if len(isp_data) > 0:
            fig_isp = px.bar(
                isp_data,
                x='message_count',
                y='isp',
                orientation='h',
                title="Top 10 ISPs por Mensagens",
                color='message_count',
                color_continuous_scale='Viridis'
            )
            fig_isp.update_layout(
                yaxis={'categoryorder':'total ascending'},
                showlegend=False
            )
            st.plotly_chart(fig_isp, use_container_width=True)
    
    # DATAFRAME DETALHADO
    st.divider()
    st.subheader("📊 Dados Detalhados das Mensagens")
    
    if detailed_messages:
        df_details = pd.DataFrame([
            {
                'ID Mensagem': msg.message_id,
                'Sender': msg.sender,
                'IP': msg.sender_ip,
                'Data/Hora': msg.timestamp,
                'Dispositivo': msg.sender_device,
                'Tipo': msg.message_type,
                'Cidade': msg.city,
                'Estado/Região': msg.region_name,
                'País': msg.country,
                'Latitude': msg.latitude,
                'Longitude': msg.longitude,
                'ISP': msg.isp,
                'Organização': msg.org,
                'Continente': msg.continent
            }
            for msg in detailed_messages
        ])
        
        # Exibir dataframe
        st.dataframe(
            df_details,
            use_container_width=True,
            hide_index=True,
            column_config={
                "Data/Hora": st.column_config.DatetimeColumn(
                    "Data/Hora",
                    format="DD/MM/YYYY HH:mm:ss"
                ),
                "Latitude": st.column_config.NumberColumn(
                    "Latitude",
                    format="%.6f"
                ),
                "Longitude": st.column_config.NumberColumn(
                    "Longitude", 
                    format="%.6f"
                )
            }
        )
        
                
        # GRÁFICO TEMPORAL
        st.divider()
        st.subheader("⏰ Distribuição Temporal das Mensagens")
        
        # Criar gráfico de linha temporal
        df_details['Data'] = pd.to_datetime(df_details['Data/Hora']).dt.date
        temporal_data = df_details.groupby('Data').size().reset_index(name='Quantidade')
        temporal_data['Data'] = pd.to_datetime(temporal_data['Data'])
        
        if len(temporal_data) > 0:
            fig_temporal = px.line(
                temporal_data,
                x='Data',
                y='Quantidade',
                title="Mensagens por Data",
                markers=True
            )
            fig_temporal.update_layout(
                xaxis_title="Data",
                yaxis_title="Quantidade de Mensagens"
            )
            st.plotly_chart(fig_temporal, use_container_width=True)
    
    else:
        st.info("Nenhuma mensagem detalhada encontrada para os filtros selecionados.")

else:
    st.info("👆 Clique em 'Plotar IPs no Mapa' na barra lateral para visualizar os dados.", icon="ℹ️")
