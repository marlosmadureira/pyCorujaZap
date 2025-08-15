import streamlit as st
from db.models import File, Target, Operation
from db.session import get_session
from db.queries import insert_groups_and_contacts, insert_target_into_targets, insert_data_into_files, insert_messages
from settings import get_operacao, PROJECT_ROOT
from pathlib import Path
import os, time
import uuid
import pandas as pd
from extractor import get_account_data_from_buffer
from extractor.ip_api_client import IPEnricher

BASE_DIR = Path(__file__).absolute().parent.parent.parent.parent

################## FUNÇÕES DE PROCESSAMENTO ##################
################## FUNÇÕES DE PROCESSAMENTO ##################
################## FUNÇÕES DE PROCESSAMENTO ##################

def processar_arquivo_completo(archive_path, operation_id, nome_operacao, telefone_alvo, account_data):
    try:
        insert_target_into_targets(operation_id, nome_operacao, telefone_alvo)
        insert_data_into_files(operation_id, archive_path, account_data)

        if account_data['file_type'] == 'DADOS':
            # insere grupos e agenda
            insert_groups_and_contacts(operation_id, archive_path)
            
        elif account_data['file_type'] == 'PRTT':
            # insere mensagens
            insert_messages(operation_id, archive_path)
        
        # Enriquecer IPs após inserção com feedback visual
        enricher = IPEnricher()
        
        # Verificar quantos IPs precisam ser processados
        pending_ips = enricher.get_pending_ips()
        if pending_ips:
            enricher.process_pending_ips()
            print(f"{len(pending_ips)} IPs enriquecidos com sucesso!")
        else:
            print("Todos os IPs já estão enriquecidos")

        print("Arquivo processado com sucesso!")
        
    except Exception as e:
        print(f"Erro no processamento: {str(e)}")


################## lÓGICA DA SIDEBAR ##################
################## lÓGICA DA SIDEBAR ##################
################## lÓGICA DA SIDEBAR ##################

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
    if "uploader_key" not in st.session_state:
        st.session_state["uploader_key"] = str(uuid.uuid4())
    
    if "uploader_visible" not in st.session_state:
        st.session_state["uploader_visible"] = False

    if "upload_msg" not in st.session_state:
        st.session_state["upload_msg"] = False
    
    if "show_dialog" not in st.session_state:
      st.session_state['show_dialog'] = False

    if "processing" not in st.session_state:
        st.session_state["processing"] = False
    
    if "files_to_process" not in st.session_state:
        st.session_state["files_to_process"] = []

    @st.dialog("_Aviso_", width="small")
    def show_upload_dialog():
        st.success("Arquivo(s) carregado com sucesso!", icon="✅")
        st.session_state.show_dialog = False
    
    @st.dialog("_Atenção ao excluir os pacotes_", width="small")
    def show_excluir_dialog():
        st.error("Exclua somente com certeza.")
        st.error("Os registros atrelados também serão excluídos.")
        
    
    st.header('Faça upload dos arquivos ZIP', divider='red')
    # Verificar se existe operação SEM bloquear a execução
    try:
        nome_operacao = get_operacao()
        has_operacao = bool(nome_operacao)
    except:
        # Se get_operacao() falha/bloqueia, assumir que não há operação
        has_operacao = False
        nome_operacao = None
    
    # Sempre mostrar o file_uploader, mas com estado condicional
    if not has_operacao:
        # Mostrar file_uploader DESATIVADO quando não há operação
        uploaded_file = st.file_uploader(
            "Upload", 
            type=["zip"], 
            accept_multiple_files=True, 
            key=st.session_state["uploader_key"] + '_disabled',
            disabled=True,
        )

        st.divider()
        st.header('Selecione o(s) telefone(s) dos alvos para visualizar os pacotes importados.')
        telefones = st.multiselect(
            "Opções", 
            options=['a', 'b'], 
            max_selections=1, 
            placeholder='Telefones', 
            key='tel_disabled', 
            disabled=True
        )

        st.divider()
        st.header('Selecione o pacote para excluí-lo')
        pacotes = st.multiselect(
            "Opções", 
            options=['a', 'b'], 
            placeholder='Pacotes',
            key='pac_disabled',
            disabled=True
            )
        excluir_pacotes = st.button("Excluir Pacote", type="primary", key='btnexcl_disabled', disabled=True)

    else:
        # Mostrar file_uploader e filtros ATIVO quando há operação
        operation_id = st.session_state.get("current_op_id", None)
        uploaded_file = st.file_uploader(
            "Upload", 
            type=["zip"], 
            accept_multiple_files=True, 
            key=st.session_state["uploader_key"]
        )

        st.divider()
        # Buscar todos os targets APENAS da operação atual
        with get_session() as session:
            if operation_id:
                targets = session.query(Target.target).join(
                    Target.operations
                ).filter(
                    Operation.operation_id == operation_id
                ).distinct().all()
                telefone_options = [row.target for row in targets] if targets else []
            else:
                telefone_options = []
            telefone_options.insert(0, 'Todos')

        st.header('Selecione o(s) telefone(s) dos alvos para visualizar os pacotes importados.')
        telefones = st.selectbox("Opções", options=telefone_options, index=0, placeholder='Telefones')

        st.divider()
        st.header('Selecione o pacote para excluí-lo')

        with get_session() as session:
            # Consultar os dados da tabela File relacionado aos alvos da operação corrente
            if operation_id:
                # Query com JOIN para filtrar arquivos apenas dos targets da operação atual
                file_query = session.query(File.archive_name).join(
                    Target, File.target_id == Target.target_id
                ).join(
                    Target.operations
                ).filter(
                    Operation.operation_id == operation_id
                ).distinct().all()

                exclude_options = [f[0] for f in file_query]
            else:
                exclude_options = []

        pacotes = st.multiselect("Opções", options=exclude_options, placeholder='Pacotes')
        excluir_pacotes = st.button("Excluir Pacote", type="primary", disabled=False)
        
        if pacotes and not excluir_pacotes:
            show_excluir_dialog()
            
        if excluir_pacotes:
            if not pacotes:
                st.error("Nenhum pacote selecionado para exclusão.")
            else:
                try:
                    with get_session() as session:
                        total_excluidos = 0
                        
                        for nome_pacote in pacotes:
                            # Buscar o arquivo específico da operação atual
                            file_record = session.query(File).join(
                                Target, File.target_id == Target.target_id
                            ).join(
                                Target.operations
                            ).filter(
                                File.archive_name == nome_pacote,
                                Operation.operation_id == operation_id
                            ).first()
                            
                            if file_record:
                                print(f"Excluindo arquivo: {nome_pacote} (ID: {file_record.file_id})")
                                
                                # Excluir arquivo físico se existir
                                try:
                                    target = session.query(Target).filter_by(target_id=file_record.target_id).first()
                                    if target:
                                        nome_operacao = get_operacao()
                                        arquivo_fisico = BASE_DIR / "data" / str(nome_operacao) / target.target / nome_pacote
                                        if arquivo_fisico.exists():
                                            arquivo_fisico.unlink()
                                            print(f"Arquivo físico excluído: {arquivo_fisico}")
                                except Exception as e:
                                    print(f"Erro ao excluir arquivo físico: {e}")
                                
                                # Excluir o arquivo do banco - CASCADE fará o resto automaticamente! 🎯
                                session.delete(file_record)
                                total_excluidos += 1
                                print(f"Arquivo {nome_pacote} marcado para exclusão (CASCADE ativo)")
                            else:
                                print(f"Arquivo {nome_pacote} não encontrado na operação")
                        
                        session.commit()
                        print(f"✅ Exclusão completa - {total_excluidos} arquivos")
                        
                        # LIMPEZA: Verificar e remover targets órfãos (sem arquivos)
                        targets_orfaos = session.query(Target).join(
                            Target.operations
                        ).filter(
                            Operation.operation_id == operation_id,
                            ~Target.files.any()  # Target que NÃO tem nenhum arquivo
                        ).all()
                        
                        targets_removidos = 0
                        pastas_removidas = []
                        for target_orfao in targets_orfaos:
                            print(f"Removendo target órfão: {target_orfao.target} (ID: {target_orfao.target_id})")
                            
                            # 📁 REMOVER PASTA FÍSICA DO TARGET SE ESTIVER VAZIA
                            try:
                                pasta_target = BASE_DIR / "data" / str(nome_operacao) / target_orfao.target
                                if pasta_target.exists():
                                    # Verificar se a pasta está vazia (ou só tem arquivos ocultos)
                                    arquivos_restantes = list(pasta_target.glob("*"))
                                    if not arquivos_restantes:  # Pasta vazia
                                        pasta_target.rmdir()
                                        pastas_removidas.append(target_orfao.target)
                                        print(f"📁 Pasta física removida: {pasta_target}")
                                    else:
                                        print(f"📁 Pasta {pasta_target} não estava vazia - mantida")
                                else:
                                    print(f"📁 Pasta {pasta_target} não existe fisicamente")
                            except Exception as e:
                                print(f"❌ Erro ao remover pasta física {target_orfao.target}: {e}")
                            
                            # Remover associações operation-target
                            target_orfao.operations.clear()
                            
                            # Excluir o target
                            session.delete(target_orfao)
                            targets_removidos += 1
                        
                        if targets_removidos > 0:
                            session.commit()
                            print(f"{targets_removidos} target(s) órfão(s) removido(s)")
                            print(f"{len(pastas_removidas)} pasta(s) física(s) removida(s): {pastas_removidas}")
                        
                    st.success(f"{total_excluidos} pacote(s) excluído(s) com sucesso!", icon="✅")
                    
                except Exception as e:
                    print(f"Erro na exclusão: {str(e)}")
                    st.error(f"Erro ao excluir pacotes: {str(e)}")

        if uploaded_file and not st.session_state["processing"]:
            # Preparar dados para processamento
            uploaded_File_data = []
            
            for file in uploaded_file:
                account_data = get_account_data_from_buffer(file.getbuffer(), file.name)
                telefone_alvo = account_data.get('account_identifier', 'identificador_nao_encontrado')
                
                uploaded_File_data.append({
                    'file': file,
                    'telefone_alvo': telefone_alvo,
                    'account_data': account_data
                })
            
            # Armazenar no session_state e iniciar processamento
            st.session_state["files_to_process"] = uploaded_File_data
            st.session_state["processing"] = True
            st.rerun()

        if st.session_state.show_dialog:
            show_upload_dialog()



################## lÓGICA DA ÁREA CENTRAL ##################
################## lÓGICA DA ÁREA CENTRAL ##################
################## lÓGICA DA ÁREA CENTRAL ##################

try:
    nome_operacao = get_operacao()
    has_operacao = bool(nome_operacao)
except:
    has_operacao = False
    nome_operacao = None

# ESTADO 1: SEM OPERAÇÃO - Ocultar dataframe
if not has_operacao:
    st.error("Por favor, selecione uma Operação para habilitar os filtros na barra lateral.", icon="🚨")
    st.error("Administração > Configurações > Selecionar operação.", icon="🚨")
    st.stop()

# ESTADO 2: PROCESSANDO - Mostrar progress na área central
elif st.session_state.get("processing", False):
    text_header = f'Gerenciador de Pacotes - Operação: **"{nome_operacao}"**'
    st.header(text_header, divider='red')
    st.write('')
    
    # PROGRESS NA ÁREA CENTRAL
    if st.session_state["files_to_process"]:
        uploaded_File_data = st.session_state["files_to_process"]
        total_files = len(uploaded_File_data)
        
        # Usar Progress Bar na área central
        st.write('')
        progress_text = "🔄 Processando arquivos e enriquecendo dados de geolocalização..."
        progress_bar = st.progress(0, text=progress_text)
        
        for i, data in enumerate(uploaded_File_data):
            file = data['file']
            telefone_alvo = data['telefone_alvo']
            account_data = data['account_data']
            
            # Atualizar progress bar
            progress = (i + 1) / total_files
            progress_bar.progress(progress, text=f"📁 Processando {file.name} ({i+1}/{total_files})")
            
            # Salvar arquivo
            operation_id = st.session_state.get("current_op_id", None)
            destino_dir = BASE_DIR / "data" / str(nome_operacao) / telefone_alvo
            archive_path = destino_dir / file.name
            os.makedirs(destino_dir, exist_ok=True)
            
            with open(archive_path, "wb") as f:
                f.write(file.getbuffer())
            print(f"Arquivo salvo diretamente em: {archive_path}")
            
            processar_arquivo_completo(archive_path, operation_id, nome_operacao, telefone_alvo, account_data)
        
        # Finalizar processamento
        progress_bar.progress(1.0, text="✅ Processamento concluído!")
        
        # Limpar estados
        st.session_state["processing"] = False
        st.session_state["files_to_process"] = []
        st.session_state.show_dialog = True
        st.session_state.uploader_key = str(uuid.uuid4())
        
        # Aguardar 2 segundos para mostrar conclusão, depois rerun
        import time
        time.sleep(1)
        st.rerun()

# ESTADO 3: NORMAL - Mostrar dataframe atualizado
else:
    text_header = f'Gerenciador de Pacotes - Operação: **"{nome_operacao}"**'
    st.header(text_header)
    st.subheader(f'Pacotes importados de: {telefones}', divider='red')
    st.write('')

    operation_id = st.session_state.get("current_op_id", None)

    if telefones == 'Todos':
        # Obter sessão do banco e filtrar por operação + alvo
        with get_session() as session:
            if operation_id:
                # Consultar os dados da tabela File usando operation_id diretamente
                file_query = session.query(
                    File.archive_name,
                    File.generated_timestamp,
                    File.date_range_start,
                    File.date_range_end,
                    File.uploaded_at,
                    File.process_status,
                    File.file_type
                ).filter_by(operation_id=operation_id).all()
            else:
                file_query = []

            # Converter para DataFrame
            df_file = pd.DataFrame(file_query, columns=[
                "Nome do pacote",
                "Gerado em",
                "Start",
                "End",
                "Processado em",
                "Status",
                "Tipo"
            ])

        # Exibir o DataFrame na tela
        st.dataframe(df_file, hide_index=True)
    else:
        with get_session() as session:
            if operation_id:
                # Buscar target que pertence à operação atual
                target = session.query(Target).join(
                    Target.operations
                ).filter(
                    Target.target == telefones,
                    Operation.operation_id == operation_id
                ).first()

                if target:
                    # Query direta usando FK composta
                    file_query = session.query(
                        File.archive_name,
                        File.generated_timestamp,
                        File.date_range_start,
                        File.date_range_end,
                        File.uploaded_at,
                        File.process_status,
                        File.file_type
                    ).filter_by(
                        operation_id=operation_id, #FK composta
                        target_id=target.target_id #FK composta
                    ).order_by(File.generated_timestamp.desc()).all()
                else:
                    file_query = []
            else:
                file_query = []

            # Converter para DataFrame
            df_file = pd.DataFrame(file_query, columns=[
                "Nome do pacote",
                "Gerado em",
                "Start",
                "End",
                "Processado em",
                "Status",
                "Tipo"
            ])

        st.dataframe(df_file, hide_index=True)

    # Mostrar dialog de sucesso se necessário
    if st.session_state.get("show_dialog", False):
        st.success("✅ Arquivo(s) processado(s) com sucesso!")
        st.session_state.show_dialog = False
