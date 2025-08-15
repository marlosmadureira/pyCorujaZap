from datetime import datetime
from db.session import get_session
from db.models import Operation, Target, File, Group, Contact, IP, Message, MessageRecipient, GroupMetadata
from extractor import get_account_data, get_messages, get_contacts_and_groups


def insert_target_into_targets(operation_id, nome_operacao, telefone_alvo):
    try:
        with get_session() as session:
            
            # Buscar a operação pelo ID
            operation = session.query(Operation).filter_by(operation_id=operation_id).first()
            if not operation:
                print(f"❌ Operação {operation_id} não encontrada.")
                return False
            
            # Verificar se já existe associação na operação atual
            existing_association = session.query(Target).join(
                Target.operations
            ).filter(
                Target.target == telefone_alvo,
                Operation.operation_id == operation_id
            ).first()
            
            if existing_association:
                print(f"ℹ️  Target {telefone_alvo} já está associado à operação {nome_operacao}.")
                return True
            
            # Buscar target globalmente (pode existir em outras operações)
            existing_target = session.query(Target).filter_by(target=telefone_alvo).first()
            
            if existing_target:
                # Target existe globalmente, apenas associar à operação atual
                print(f"🔗 Target {telefone_alvo} existe. Associando à operação {nome_operacao}...")
                existing_target.operations.append(operation)
                session.commit()
                print(f"✅ Target {telefone_alvo} associado à operação {nome_operacao}.")
                return True
            else:
                # Criar novo target e associar à operação
                print(f"🆕 Criando novo target {telefone_alvo}...")
                new_target = Target(
                    target=telefone_alvo,
                    owner=None,
                    external_id=None
                )
                # Associar à operação através do relacionamento many-to-many
                new_target.operations.append(operation)
                session.add(new_target)
                session.commit()
                print(f"✅ Target {telefone_alvo} criado e associado à operação {nome_operacao}.")
                return True
    
    except Exception as e:
        print(f"❌ Erro ao inserir target {telefone_alvo}: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return False


def insert_data_into_files(operation_id, zip_path: str, account_data: dict):
    """
    Salva dados da conta na tabela 'files' e associa ao target correto.
    """
    zip_path = str(zip_path)
    filename = zip_path.split('/')[-1]

    try:
        with get_session() as session:
            # Buscar o target pelo número de telefone e que esteja associado à operação
            target = session.query(Target).join(
                Target.operations
            ).filter(
                Operation.operation_id == operation_id,
                Target.target == account_data['account_identifier']
            ).first()
            
            if not target:
                return {'status': 'error', 'message': f"Target {account_data['account_identifier']} não encontrado na operação {operation_id}"}
            
            # Verificar se já existe arquivo com mesmo nome para este operation_id + target_id
            existing = session.query(File).filter_by(
                operation_id=operation_id,
                target_id=target.target_id,
                archive_name=filename
            ).first()
            
            if existing:
                return {'status': 'info', 'message': f'Arquivo {filename} já existe para target {target.target} na operação {operation_id}'}
            
            # Preparar dados
            file_data = {
                'operation_id': operation_id,
                'target_id': target.target_id,
                'archive_name': filename,
                'internal_ticket_number': account_data.get('internal_ticket_number'),
                'file_type': account_data.get('file_type'),
                'date_range_start': account_data.get('date_range_start'),
                'date_range_end': account_data.get('date_range_end'),
                'generated_timestamp': account_data.get('generated_timestamp'),
                'process_status': 'PENDING',
            }
            
            new_file = File(**file_data)
            session.add(new_file)
            session.commit()
            
            return {'status': 'success', 'message': 'Dados da conta salvos'}
    except Exception as e:
        print(f"❌ Erro ao inserir arquivo: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {'status': 'error', 'message': str(e)}

    
def insert_groups_and_contacts(operation_id, zip_path: str):
    """
    Processa arquivo e preenche dados dos grupos que já existem ou cria novos.
    """
    zip_path = str(zip_path)
    filename = zip_path.split('/')[-1]
    
    try:
        with get_session() as session:
            # Extrair account_data para identificar o target
            account_data = get_account_data(zip_path)
            if not account_data:
                return {'status': 'error', 'message': 'Não foi possível extrair dados da conta do arquivo'}
            
            # Buscar target
            target = session.query(Target).join(Target.operations).filter(
                Operation.operation_id == operation_id,
                Target.target == account_data['account_identifier']
            ).first()
            
            if not target:
                return {'status': 'error', 'message': f"Target {account_data['account_identifier']} não encontrado na operação {operation_id}"}
            
            # Buscar arquivo com FK composta completa
            file_record = session.query(File).filter_by(
                operation_id=operation_id,
                target_id=target.target_id,
                archive_name=filename
            ).first()
            
            if not file_record:
                return {'status': 'error', 'message': f"Arquivo {filename} não encontrado para target {target.target} na operação {operation_id}"}
            
            # Extrair dados dos grupos e contatos
            data = get_contacts_and_groups(zip_path)
            groups_data = data.get('groups', [])
            contacts_data = data.get('contacts', {})
            
            # Processar grupos
            if groups_data:
                for group_data in groups_data:
                    group_id = group_data.get('group_id')
                    if not group_id:
                        continue
                    
                    # Preparar dados do arquivo
                    creation_datetime = None
                    if group_data.get('creation'):
                        try:
                            creation_datetime = datetime.strptime(group_data['creation'], '%Y-%m-%d %H:%M:%S UTC')
                        except ValueError:
                            pass
                    
                    # Verificar se o grupo já existe na tabela whats_groups
                    existing_group = session.query(Group).filter_by(
                        group_id=group_id
                    ).first()
                    
                    if existing_group and existing_group.creation is None:
                        try:
                            # Atualizar grupo existente que não tem creation
                            existing_group.creation = creation_datetime
                            
                            # Criar nova metadata
                            new_metadata = GroupMetadata(
                                group_id=group_id,
                                group_size=group_data.get('group_size'),
                                subject=group_data.get('subject'),
                                generated_timestamp=creation_datetime
                            )
                            
                            session.add(new_metadata)

                            # Associar grupo ao arquivo usando relacionamento
                            if existing_group not in file_record.groups:
                                file_record.groups.append(existing_group)
                            
                        except Exception as e:
                            print(f"Erro ao atualizar grupo existente: {str(e)}")
                            raise
                                            
                    elif not existing_group:
                        print("Criando novo grupo")
                        try:
                            # Criar novo grupo
                            new_group = Group(
                                group_id=group_id,
                                creation=creation_datetime
                            )
                            session.add(new_group)
                                                        
                            # Criar metadata para o novo grupo
                            new_metadata = GroupMetadata(
                                group_id=group_id,
                                group_size=group_data.get('group_size'),
                                subject=group_data.get('subject'),
                                generated_timestamp=creation_datetime
                            )
                            session.add(new_metadata)
                            
                            # Associar novo grupo ao arquivo
                            file_record.groups.append(new_group)
                            
                        except Exception as e:
                            print(f"Erro ao criar novo grupo: {str(e)}")
                            raise
                    else:
                        # Associar grupo existente ao arquivo se ainda não estiver
                        if existing_group not in file_record.groups:
                            file_record.groups.append(existing_group)

            # Processar contatos
            if contacts_data:
                # Processar contatos simétricos
                if contacts_data.get('symetric_contacts'):
                    for phone in contacts_data['symetric_contacts']:        
                        # Verificar se o contato já existe (globalmente)
                        existing_contact = session.query(Contact).filter_by(
                            contact_phone=phone,
                            contact_type='symmetric_contact'
                        ).first()
                        
                        if not existing_contact:
                            try:
                                new_contact = Contact(
                                    contact_phone=phone,
                                    contact_type='symmetric_contact'
                                )
                                session.add(new_contact)
                                session.flush()  # Para obter o ID
                                file_record.contacts.append(new_contact)
                            except Exception as e:
                                print(f"Erro ao criar contato simétrico {phone}: {str(e)}")
                        else:
                            # Verificar se já está associado ao arquivo
                            if existing_contact not in file_record.contacts:
                                file_record.contacts.append(existing_contact)
                
                # Processar contatos assimétricos
                if contacts_data.get('assymetric_contacts'):
                    for phone in contacts_data['assymetric_contacts']:
                        # Verificar se o contato já existe (globalmente)
                        existing_contact = session.query(Contact).filter_by(
                            contact_phone=phone,
                            contact_type='asymmetric_contact'
                        ).first()
                        
                        if not existing_contact:
                            try:
                                new_contact = Contact(
                                    contact_phone=phone,
                                    contact_type='asymmetric_contact'
                                )
                                session.add(new_contact)
                                session.flush()  # Para obter o ID
                                file_record.contacts.append(new_contact)
                            except Exception as e:
                                print(f"Erro ao criar contato assimétrico {phone}: {str(e)}")
                        else:
                            # Verificar se já está associado ao arquivo
                            if existing_contact not in file_record.contacts:
                                file_record.contacts.append(existing_contact)

            # Atualizar status se campo existir
            if hasattr(file_record, 'process_status') and file_record.process_status == 'PENDING':
                file_record.process_status = 'OK'

            session.commit()
            return {'status': 'success', 'message': 'Grupos e contatos processados com sucesso'}
            
    except Exception as e:
        return {'status': 'error', 'message': f"Erro ao processar grupos e contatos: {str(e)}"}


def insert_messages(operation_id, zip_path: str):
    """
    Processa arquivo e insere mensagens na tabela messages e message_recipients.
    Atualizada para usar FK composta completa.
    """
    zip_path = str(zip_path)
    filename = zip_path.split('/')[-1]
    
    try:
        with get_session() as session:
            
            # PRIMEIRO: Extrair account_data para identificar o target
            account_data = get_account_data(zip_path)
            if not account_data:
                return {'status': 'error', 'message': 'Não foi possível extrair dados da conta do arquivo'}
            
            # SEGUNDO: Buscar target
            target = session.query(Target).join(Target.operations).filter(
                Operation.operation_id == operation_id,
                Target.target == account_data['account_identifier']
            ).first()
            
            if not target:
                return {'status': 'error', 'message': f"Target {account_data['account_identifier']} não encontrado na operação {operation_id}"}
            
            # TERCEIRO: Buscar arquivo com FK composta completa
            file_record = session.query(File).filter_by(
                operation_id=operation_id,
                target_id=target.target_id,  # ✅ FK composta completa
                archive_name=filename
            ).first()
            
            if not file_record:
                return {'status': 'error', 'message': f"Arquivo {filename} não encontrado para target {target.target} na operação {operation_id}"}
            
            # Extrair dados das mensagens
            messages_data = get_messages(zip_path)
            
            if not messages_data:
                return {'status': 'info', 'message': 'Nenhuma mensagem encontrada no arquivo'}
            
            print(f"Processando {len(messages_data)} mensagens")
            
            # Remover duplicatas do próprio dataset
            unique_messages = {}
            for message_data in messages_data:
                message_id = message_data.get('message_id')
                if message_id and message_id not in unique_messages:
                    unique_messages[message_id] = message_data
            
            print(f"Após remover duplicatas: {len(unique_messages)} mensagens únicas")
            
            # Coletar todos os IPs únicos primeiro
            unique_ips = set()
            for message_data in unique_messages.values():
                sender_ip = message_data.get('sender_ip')
                if sender_ip:
                    unique_ips.add(sender_ip)
            
            # Inserir IPs únicos em lote
            if unique_ips:
                existing_ips = session.query(IP.sender_ip).filter(IP.sender_ip.in_(unique_ips)).all()
                existing_ip_set = {ip[0] for ip in existing_ips}
                
                new_ips = []
                for ip in unique_ips:
                    if ip not in existing_ip_set:
                        new_ips.append(IP(
                            sender_ip=ip,
                            continent=None,
                            country=None,
                            country_code=None,
                            region=None,
                            region_name=None,
                            city=None,
                            district=None,
                            zipcode_ip=None,
                            latitude=None,
                            longitude=None,
                            timezone_ip=None,
                            isp=None,
                            org=None,
                            as_name=None,
                            mobile=None
                        ))
                
                if new_ips:
                    session.add_all(new_ips)
                    print(f"{len(new_ips)} novos IPs adicionados")
            
            # Verificar quais mensagens já existem no banco
            existing_message_ids = session.query(Message.message_id).filter(
                Message.message_id.in_(unique_messages.keys())
            ).all()
            existing_message_set = {msg[0] for msg in existing_message_ids}
            
            # Processar apenas mensagens que não existem
            messages_to_process = {
                msg_id: msg_data for msg_id, msg_data in unique_messages.items()
                if msg_id not in existing_message_set
            }
            
            print(f"Mensagens novas para inserir: {len(messages_to_process)}")
            
            # Criar grupos órfãos se necessário (sem FK, apenas referência textual)
            unique_group_ids = set()
            for message_data in messages_to_process.values():
                group_id = message_data.get('group_id')
                if group_id:
                    unique_group_ids.add(group_id)
            
            # Verificar quais grupos existem no banco e criar os que não existem
            if unique_group_ids:
                existing_groups = session.query(Group.group_id).filter(
                    Group.group_id.in_(unique_group_ids)
                ).all()
                existing_group_ids = {group[0] for group in existing_groups}
                
                # Criar grupos que não existem (órfãos temporários)
                missing_group_ids = unique_group_ids - existing_group_ids
                if missing_group_ids:
                    print(f"Criando {len(missing_group_ids)} novos grupos: {missing_group_ids}")
                    new_groups = []
                    for group_id in missing_group_ids:
                        new_group = Group(
                            group_id=group_id,
                            creation=None  # Será preenchido posteriormente pela função de grupos
                        )
                        new_groups.append(new_group)
                    
                    session.add_all(new_groups)
                    session.flush()  # Inserir os grupos antes das mensagens
                    print(f"{len(new_groups)} novos grupos criados")
            
            # Processar mensagens e recipients em lotes
            messages_to_add = []
            recipients_to_add = []
            
            for message_id, message_data in messages_to_process.items():
                try:
                    # Preparar mensagem para inserção em lote
                    new_message = Message(
                        message_id=message_id,
                        file_id=file_record.file_id,
                        timestamp=message_data.get('timestamp'),
                        sender=message_data.get('sender'),
                        group_id=message_data.get('group_id'),  # Agora pode usar diretamente, pois o grupo foi criado - apenas referência textual
                        sender_ip=message_data.get('sender_ip'),
                        sender_port=message_data.get('sender_port'),
                        sender_device=message_data.get('sender_device'),
                        message_type=message_data.get('type'),
                        message_style=message_data.get('message_style'),
                        message_size=message_data.get('message_size')
                    )
                    messages_to_add.append(new_message)
                    
                    # Preparar recipients para inserção em lote
                    recipients = message_data.get('recipients', [])
                    if recipients:
                        for recipient in recipients:
                            new_recipient = MessageRecipient(
                                message_id=message_id,
                                recipient_phone=recipient
                            )
                            recipients_to_add.append(new_recipient)

                except Exception as e:
                    print(f"Erro ao preparar mensagem {message_id}: {str(e)}")
                    raise
            
            # Inserir mensagens em lote
            if messages_to_add:
                try:
                    session.add_all(messages_to_add)
                    print(f"{len(messages_to_add)} mensagens preparadas para inserção")
                    session.flush()
                    print("Mensagens inseridas com sucesso")
                except Exception as e:
                    print(f"Erro ao inserir mensagens: {str(e)}")
                    raise
            
            # Inserir recipients em lote
            if recipients_to_add:
                try:
                    session.add_all(recipients_to_add)
                    print(f"{len(recipients_to_add)} recipients preparados para inserção")
                    session.flush()
                    print("Recipients inseridos com sucesso")
                except Exception as e:
                    print(f"Erro ao inserir recipients: {str(e)}")
                    raise

            # Atualizar o status do arquivo se ainda estiver PENDING
            try:
                if hasattr(file_record, 'process_status') and file_record.process_status == 'PENDING':
                    file_record.process_status = 'OK'
                    print("Status do arquivo atualizado para OK")
            except Exception as e:
                print(f"Erro ao atualizar status do arquivo: {str(e)}")
                raise
            
            try:
                session.commit()
                print("Commit realizado com sucesso")
                return {'status': 'success', 'message': f'{len(messages_to_process)} mensagens processadas com sucesso'}
            except Exception as e:
                print(f"Erro no commit final: {str(e)}")
                raise
                
    except Exception as e:
        print(f"Erro detalhado: {str(e)}")
        import traceback
        print(f"Traceback: {traceback.format_exc()}")
        return {'status': 'error', 'message': f"Erro ao processar mensagens: {str(e)}"}
