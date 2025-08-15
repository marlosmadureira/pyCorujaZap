from typing import List, Dict
import zipfile
import re
import os
import tempfile
from bs4 import BeautifulSoup
import pandas as pd
from datetime import datetime
import sys


sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def get_account_data_from_buffer(file_buffer, filename):
    """
    Extrai account_data de um buffer sem salvar arquivo permanentemente.
    
    Args:
        file_buffer: Buffer do arquivo
        filename: Nome do arquivo
    
    Returns:
    {
    'internal_ticket_number': '22222264',
    'account_identifier': '5518999999999', 
    'generated_timestamp': '2025-04-21 15:00:46 UTC', 
    'date_range_start': '2025-04-01 00:00:00 UTC',
    'date_range_end': '2025-04-16 23:59:59 UTC', 
    'file_type': 'DADOS', # ou PRTT
    'archive_name': 'tmpc282l2wy.zip' # temp name file - buffer
    }
    """
    # Criar arquivo temporário
    with tempfile.NamedTemporaryFile(delete=False, suffix='.zip') as temp_file:
        temp_file.write(file_buffer)
        temp_path = temp_file.name
    
    try:
        # Usar função existente
        account_data = get_account_data(temp_path)
        print(account_data)
        return account_data
    finally:
        # Limpar arquivo temporário
        os.unlink(temp_path)


def get_account_data(zip_path: str) -> Dict[str, str]:
    """
    Extrai dados gerais da conta do texto limpo do WhatsApp Business Record.
    Inclui: ticket, identificador, tipo, geração, intervalo de datas desmembrado,
    tipo de arquivo (PRTT ou DADOS), e nome do arquivo ZIP.

    Exemplo::
    {
    'internal_ticket_number': '22222264',
    'account_identifier': '5518999999999', 
    'generated_timestamp': '2025-04-21 15:00:46 UTC', 
    'date_range_start': '2025-04-01 00:00:00 UTC',
    'date_range_end': '2025-04-16 23:59:59 UTC', 
    'file_type': 'DADOS', # ou PRTT
    'archive_name': '1023333333333331.zip'
    }
    """
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as myzip:
            with myzip.open('records.html') as myfile:
                content = myfile.read().decode('utf-8', errors='replace')
                soup = BeautifulSoup(content, 'html.parser')
                texto_limpo = soup.get_text(separator='\n')

        dados = {}

        padroes = {
            'internal_ticket_number': r'Internal Ticket Number\s+(\d+)',
            'account_identifier': r'Account Identifier\s+(\+\d+)',
            'generated_timestamp': r'Generated\s+([0-9:\- ]+ UTC)',
            'Date Range': r'Date Range\s+([0-9:\- UTC]+)\s+to\s+([0-9:\- UTC]+)'
        }

        # Extrair os campos com regex
        for chave, padrao in padroes.items():
            match = re.search(padrao, texto_limpo)
            if match:
                if chave == 'Date Range':
                    dados['date_range_start'] = match.group(1).strip()
                    dados['date_range_end'] = match.group(2).strip()
                else:
                    dados[chave] = match.group(1).strip()
            else:
                if chave == 'Date Range':
                    dados['date_range_start'] = ''
                    dados['date_range_end'] = ''
                else:
                    dados[chave] = ''

        # Determinar o tipo do arquivo
        if 'Message Log' in texto_limpo or 'Call Logs' in texto_limpo:
            dados['file_type'] = 'PRTT'
        elif any(x in texto_limpo for x in [
            'Ncmec Reports', 'Emails', 'Connection Info', 'Web Info',
            'Groups Info', 'Address Book Info', 'Small Medium Business', 'Device Info'
        ]):
            dados['file_type'] = 'DADOS'
        else:
            dados['file_type'] = 'DESCONHECIDO'

        # Nome do arquivo ZIP
        dados['archive_name'] = os.path.basename(zip_path)

        # Exclui o + do número da conta. Ex: +551899991234
        if dados['account_identifier'].startswith('+'):
            dados['account_identifier'] = dados['account_identifier'][1:]

        # Converter strings para datetime antes de retornar
        if dados.get('date_range_start'):
            dados['date_range_start'] = datetime.strptime(dados['date_range_start'], '%Y-%m-%d %H:%M:%S UTC')
        if dados.get('date_range_end'):
            dados['date_range_end'] = datetime.strptime(dados['date_range_end'], '%Y-%m-%d %H:%M:%S UTC')
        if dados.get('generated_timestamp'):
            dados['generated_timestamp'] = datetime.strptime(dados['generated_timestamp'], '%Y-%m-%d %H:%M:%S UTC')

        return dados
    
    except Exception as e:
        print(f"Erro ao extrair dados: {e}")
        return {}
    
    finally:
        print(f'Arquivo {zip_path} processado com sucesso.')


def get_messages(zip_path: str) -> List[Dict[str, str]]:
    """
    Extrai mensagens de um arquivo ZIP contendo um arquivo 'records.html' exportado do WhatsApp Business.
    O arquivo HTML é processado para identificar e extrair blocos de mensagens, retornando uma lista de dicionários
    com os principais campos de cada mensagem.

    Args:
        zip_path (str): Caminho para o arquivo ZIP que contém o 'records.html'.

    Returns:
        List[Dict[str, Any]]: Lista de dicionários, cada um representando uma mensagem extraída, com os campos:
            - 'message_id' (str): Identificador único da mensagem.
            - 'timestamp' (datetime): Data e hora da mensagem.
            - 'sender' (str): Número do remetente.
            - 'recipients' (List[str]): Lista com números dos destinatários.
            - 'group_id' (str ou None): Identificador do grupo (se aplicável).
            - 'sender_ip' (str): IP do remetente.
            - 'sender_port' (str): Porta do remetente.
            - 'sender_device' (str): Dispositivo do remetente.
            - 'type' (str): Tipo da mensagem.
            - 'message_style' (str): Estilo da mensagem (individual ou grupo).
            - 'message_size' (int): Tamanho da mensagem.
    """
    try:
        # Extrair o HTML do ZIP
        with zipfile.ZipFile(zip_path, 'r') as myzip:
            with myzip.open('records.html') as myfile:
                content = myfile.read().decode('utf-8', errors='replace')
                soup = BeautifulSoup(content, 'html.parser')
                texto_limpo = soup.get_text(separator='\n')

        # Dividir em blocos a partir de "Message\nTimestamp"
        blocos = re.split(r'(?=Message\s*\nTimestamp)', texto_limpo)

        mensagens = []

        for bloco in blocos:
            if not bloco.strip():
                continue

            # Ignorar blocos que não tenham um campo obrigatório
            if "Message Id" not in bloco or "Timestamp" not in bloco:
                continue

            # Limpar o texto
            bloco = re.sub(r'WhatsApp Business Record Page \d+\n', '', bloco).strip()

            # Extrair campos principais
            dados = {}
            padroes = {
                "Timestamp": r"Timestamp\s*\n(.*?)(?:\n|$)",
                "Message Id": r"Message Id\s*\n(.*?)(?:\n|$)",
                "Sender": r"Sender\s*\n(.*?)(?:\n|$)",
                "Recipients": r"Recipients\s*\n(.*?)(?:\n|$)",
                "Group Id": r"Group Id\s*\n(.*?)(?:\n|$)",
                "Sender Ip": r"Sender Ip\s*\n(.*?)(?:\n|$)",
                "Sender Port": r"Sender Port\s*\n(.*?)(?:\n|$)",
                "Sender Device": r"Sender Device\s*\n(.*?)(?:\n|$)",
                "Type": r"Type\s*\n(.*?)(?:\n|$)",
                "Message Style": r"Message Style\s*\n(.*?)(?:\n|$)",
                "Message Size": r"Message Size\s*\n(.*?)(?:\n|$)"
            }

            for campo, padrao in padroes.items():
                match = re.search(padrao, bloco)
                dados[campo] = match.group(1).strip() if match else None

            # Recipients como lista de strings
            recipients_raw = dados["Recipients"]
            recipients_list = []
            if recipients_raw:
                # Dividir por vírgula, espaço ou quebra de linha e limpar espaços
                recipients_list = [r.strip() for r in re.split(r'[,\s\n]+', recipients_raw) if r.strip()]

            # Converter timestamp para datetime
            timestamp_obj = None
            if dados["Timestamp"]:
                try:
                    timestamp_obj = datetime.strptime(dados["Timestamp"], '%Y-%m-%d %H:%M:%S UTC')
                except ValueError:
                    timestamp_obj = None

            # Converter message_size para int
            message_size_int = None
            if dados["Message Size"]:
                try:
                    message_size_int = int(dados["Message Size"])
                except ValueError:
                    message_size_int = None

            mensagem = {
                "message_id": dados["Message Id"],                           # Message Id -> message_id
                "timestamp": timestamp_obj,                                  # Timestamp -> timestamp (datetime)
                "sender": dados["Sender"],                                   # Sender -> sender
                "recipients": recipients_list,                               # Recipients -> recipients (List[str])
                "group_id": dados["Group Id"] if dados["Message Style"] == "group" else None,  # Group Id -> group_id
                "sender_ip": dados["Sender Ip"],                            # Sender Ip -> sender_ip
                "sender_port": dados["Sender Port"],                        # Sender Port -> sender_port
                "sender_device": dados["Sender Device"],                    # Sender Device -> sender_device
                "type": dados["Type"],                                      # Type -> type
                "message_style": dados["Message Style"],                    # Message Style -> message_style
                "message_size": message_size_int                            # Message Size -> message_size (int)
            }

            # Só adiciona se tiver message_id e timestamp
            if mensagem["message_id"] and mensagem["timestamp"]:
                mensagens.append(mensagem)

        return mensagens

    except Exception as e:
        print(f"Erro ao extrair mensagens: {e}")
        return []

    finally:
        print(f'Arquivo {zip_path} processado com sucesso.')
        

def get_groups(zip_path: str) -> List[Dict[str, str]]:
    """
    Esta função lê o arquivo 'records.html' dentro de um arquivo ZIP, processa o conteúdo HTML,
    e utiliza expressões regulares para identificar e extrair blocos de informações de grupos.
    Cada grupo é representado por um dicionário contendo os campos 'ID', 'Creation', 'Size' e 'Subject'.

    Parâmetros:
        zip_path (str): Caminho para o arquivo ZIP a ser processado.

    Retorna:
        List[Dict[str, str]]: Uma lista de dicionários, cada um representando um grupo extraído.

    Exemplo:

        [
        {
        'ID': '12333333333333306', 
        'Creation': '2024-07-09 18:49:06 UTC', 
        'Size': '11', 
        'Subject': 'ARAÇATUBA 018'
        }
        ]
 
    Exceções:
        Em caso de erro na extração, a função imprime uma mensagem de erro e retorna uma lista vazia.

    Observação:
        O campo 'Subject' pode ser vazio caso não seja identificado corretamente no bloco do grupo.

    """
   
    try:
        with zipfile.ZipFile(zip_path, 'r') as myzip:
            with myzip.open('records.html') as myfile:
                content = myfile.read().decode('utf-8', errors='replace')
                soup = BeautifulSoup(content, 'html.parser')
                texto_limpo = soup.get_text(separator='\n')

        # Usar regex para extrair blocos de grupo
        blocos = re.split(r'\nID\s+', texto_limpo)
        grupos = []
        
        for bloco in blocos:
            if not bloco.strip():
                continue

            bloco = 'ID ' + bloco  # recoloca o "ID" que foi removido no split

            id_match = re.search(r'ID\s+(\d+)', bloco)
            creation_match = re.search(r'Creation\s+([0-9:\- ]+ UTC)', bloco)
            size_match = re.search(r'Size\s+(\d+)', bloco)
            subject_match = re.search(r'Subject\s*(.*)', bloco)

            if id_match and creation_match and size_match:
                subject_raw = subject_match.group(1).strip() if subject_match else ''
                # Se subject_raw começar com "Picture" ou outros campos, considerar vazio
                if not subject_raw or re.match(r'^(Picture|Linked Media File|Thumbnail|Description|ID)\b', subject_raw):
                    subject = ''
                else:
                    subject = subject_raw

                grupo = {
                    'group_id': id_match.group(1).strip(),
                    'creation': creation_match.group(1).strip(),
                    'group_size': size_match.group(1).strip(),
                    'subject': subject
                }
                grupos.append(grupo)

        return grupos

    except Exception as e:
        print(f"Erro ao extrair grupos: {e}")
        return []
    
    finally:
        print(f'Arquivo {zip_path} processado com sucesso.')
    

def get_addressbook(zip_path: str) -> Dict[str, List[str]]:
    """
    Extrai contatos simétricos e assimétricos de um arquivo ZIP contendo um arquivo 'records.html' exportado pelo WhatsApp Business.
    Args:
        zip_path (str): Caminho para o arquivo ZIP que contém o arquivo 'records.html'.
    
    Returns:
        Dict[str, List[str]]: Um dicionário com duas listas de strings:
            - 'symetric_contacts': Lista de contatos simétricos (números de telefone).
            - 'assymetric_contacts': Lista de contatos assimétricos (números de telefone).
    
    Exemplo:
        {
        'symetric_contacts': ['5518999999999', '5518999999999'],
        'assymetric_contacts': ['5518999999999', '5518999999999']
        }
        
    Observações:
        - O arquivo ZIP deve conter um arquivo chamado 'records.html' no formato exportado pelo WhatsApp Business.
        - Os contatos são extraídos utilizando expressões regulares após a limpeza do texto.
        - Em caso de erro, retorna um dicionário vazio.

    """
    
    try:
        with zipfile.ZipFile(zip_path, 'r') as myzip:
            with myzip.open('records.html') as myfile:
                content = myfile.read().decode('utf-8', errors='replace')
                soup = BeautifulSoup(content, 'html.parser')
                texto_limpo = soup.get_text(separator='\n')

        # Remover divisores de página antes de aplicar regex
        texto_limpo = re.sub(r'WhatsApp Business Record Page \d+', '', texto_limpo)

        contatos = {
            'symetric_contacts': [],
            'assymetric_contacts': []
        }

        # Extrair bloco de contatos simétricos
        sim_match = re.search(
            r'Symmetric contacts\s+\d+\s+Total\n(.*?)Asymmetric contacts',
            texto_limpo,
            re.DOTALL
        )
        if sim_match:
            blocosim = sim_match.group(1)
            contatos['symetric_contacts'] = re.findall(r'\d{11,}', blocosim)

        # Extrair bloco de contatos assimétricos com menos restrições
        assim_match = re.search(
            r'Asymmetric contacts\s+\d+\s+Total\n(.*?)(?:\n[A-Z][a-z]+|\Z)',
            texto_limpo,
            re.DOTALL
        )

        if assim_match:
            blocoassim = assim_match.group(1)
            contatos['assymetric_contacts'] = re.findall(r'\d{11,}', blocoassim)

        return contatos

    except Exception as e:
        print(f"Erro ao extrair contatos: {e}")
        return {}

    finally:
        print(f'Arquivo {zip_path} processado com sucesso.')


def exportar_mensagens_para_excel(lista_mensagens, caminho_arquivo="mensagens.xlsx"):
    """

    Exporta uma lista de mensagens para um arquivo Excel.

    Esta função recebe uma lista de mensagens, converte em um DataFrame do pandas,
    normaliza o campo 'Recipients' (caso exista, transformando listas em strings separadas por vírgula)
    e exporta o resultado para um arquivo Excel no caminho especificado.

    Parâmetros:
        lista_mensagens (list): Lista de dicionários contendo os dados das mensagens.
        caminho_arquivo (str, opcional): Caminho do arquivo Excel a ser gerado. Padrão é 'mensagens.xlsx'.

    Retorna:
        None

    Exemplo:
        exportar_mensagens_para_excel(mensagens, "saida.xlsx")

    """

    # Converter em DataFrame
    df = pd.DataFrame(lista_mensagens)

    # Normalizar lista de recipients (transformar lista em string separada por vírgula)
    if 'Recipients' in df.columns:
        df['Recipients'] = df['Recipients'].apply(lambda x: ', '.join(x) if isinstance(x, list) else x)

    # Exportar para Excel
    df.to_excel(caminho_arquivo, index=False)
    print(f"Arquivo Excel exportado para: {caminho_arquivo}")


def get_contacts_and_groups(zip_path: str) -> Dict[str, any]:
    """
    Extrai contatos (simétricos e assimétricos) e grupos de um arquivo ZIP contendo 
    um arquivo 'records.html' exportado do WhatsApp Business.
    
    Esta função combina os resultados de get_addressbook() e get_groups() em uma 
    única resposta estruturada.
    
    Args:
        zip_path (str): Caminho para o arquivo ZIP que contém o 'records.html'.
    
    Returns:
        Dict[str, any]: Dicionário contendo:
            - 'contacts': Dict com 'symetric_contacts' e 'assymetric_contacts'
            - 'groups': Lista de dicionários com informações dos grupos
    
    Exemplo:
        {
            'contacts': {
                'symetric_contacts': ['5518999999999', '5518888888888'],
                'assymetric_contacts': ['5518777777777']
            },
            'groups': [
                {
                    'ID': '12333333333333306',
                    'Creation': '2024-07-09 18:49:06 UTC',
                    'Size': '11',
                    'Subject': 'ARAÇATUBA 018'
                }
            ]
        }
    """
    
    try:
        # Extrair contatos
        contacts_data = get_addressbook(zip_path)
        
        # Extrair grupos
        groups_data = get_groups(zip_path)
        
        # Preparar resposta consolidada
        result = {
            'contacts': contacts_data,
            'groups': groups_data
        }
        
        return result
        
    except Exception as e:
        print(f"Erro ao extrair contatos e grupos: {e}")
        return {
            'contacts': {'symetric_contacts': [], 'assymetric_contacts': []},
            'groups': []
        }
    
    finally:
        print(f'Extração de contatos e grupos de {zip_path} concluída.')
