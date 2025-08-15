import streamlit as st

st.set_page_config(
    page_title="CorujaZap",
    page_icon="🦉",
    layout="wide",
    initial_sidebar_state="expanded",
)

pages = {
    "Administração": [
        st.Page("pages/adm/config.py", title="Configurações", default=True),
        st.Page("pages/adm/gerenciar_pacotes.py", title="Gerenciar Pacotes"),
    ],
    "Dashboard": [
        st.Page("pages/dashboard/dashboard.py", title="Dashboard"),
    ],
    "Análise de Dados": [
        st.Page("pages/arq_dados/address_book.py", title="Agenda de Contatos"),
        st.Page("pages/arq_dados/groups.py", title="Grupos"),
    ],
    "Análise PRTT": [
        st.Page("pages/arq_prtt/messages.py", title="Mensagens"),
    ],
    "Análise GeoIP": [
        st.Page("pages/ips/geolocations.py", title="Georeferenciamento por IP"),
    ],
}

pg = st.navigation(pages, position="top", expanded=True)
pg.run()