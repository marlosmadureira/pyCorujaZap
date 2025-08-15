import streamlit as st
import sys
from pathlib import Path

# Configuração do path para imports do projeto
PROJECT_ROOT = Path(__file__).absolute().parent.parent
if str(PROJECT_ROOT) not in sys.path:
    sys.path.append(str(PROJECT_ROOT))


def set_operacao(nome_operacao):
    st.session_state["nome_operacao"] = nome_operacao

def get_operacao():
    return st.session_state.get("nome_operacao", None)

def set_current_op_id(id_operacao_selecionada):
    st.session_state["current_op_id"] = id_operacao_selecionada

def get_current_op_id():
    return st.session_state.get("current_op_id", None)