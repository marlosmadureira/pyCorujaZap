-- Criação do banco
CREATE DATABASE IF NOT EXISTS corujazap_db;
USE corujazap_db;

-- Tabela de operações
CREATE TABLE IF NOT EXISTS operations (
  operation_id INT AUTO_INCREMENT PRIMARY KEY,
  name VARCHAR(255) NOT NULL,
  description TEXT,
  created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tabela de alvos (targets)
CREATE TABLE IF NOT EXISTS targets (
  target_id INT AUTO_INCREMENT PRIMARY KEY,
  target VARCHAR(255) NOT NULL,
  owner VARCHAR(255),
  external_id VARCHAR(255)
);

-- Tabela intermediária para relação N:N entre operations e targets
CREATE TABLE IF NOT EXISTS operation_targets (
  operation_id INT NOT NULL,
  target_id INT NOT NULL,
  PRIMARY KEY (operation_id, target_id),
  FOREIGN KEY (operation_id) REFERENCES operations(operation_id)
    ON DELETE CASCADE,
  FOREIGN KEY (target_id) REFERENCES targets(target_id)
    ON DELETE CASCADE
);

-- Tabela de arquivos
CREATE TABLE IF NOT EXISTS files (
  file_id INT AUTO_INCREMENT PRIMARY KEY,
  operation_id INT NOT NULL,
  target_id INT NOT NULL,
  archive_name VARCHAR(255),
  internal_ticket_number VARCHAR(255),
  generated_timestamp TIMESTAMP,
  date_range_start TIMESTAMP, 
  date_range_end TIMESTAMP,
  uploaded_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
  process_status VARCHAR(255),
  file_type VARCHAR(255),
  FOREIGN KEY (operation_id, target_id) REFERENCES operation_targets(operation_id, target_id)
    ON DELETE CASCADE
);

-- Tabela de grupos
CREATE TABLE IF NOT EXISTS whats_groups (
  group_id VARCHAR(255) PRIMARY KEY,
  creation TIMESTAMP NULL,
  UNIQUE (group_id)
);

-- Tabela de metadados dos grupos (1:N)
CREATE TABLE IF NOT EXISTS group_metadata (
  id INT AUTO_INCREMENT PRIMARY KEY,
  group_id VARCHAR(255) NOT NULL,
  group_size INT,
  subject TEXT,
  generated_timestamp TIMESTAMP,
  FOREIGN KEY (group_id) REFERENCES whats_groups(group_id)
    ON DELETE CASCADE
);

-- Tabela intermediária para relação N:N entre arquivos e grupos
CREATE TABLE IF NOT EXISTS file_groups (
  file_id INT NOT NULL,
  group_id VARCHAR(255) NOT NULL,
  PRIMARY KEY (file_id, group_id),
  FOREIGN KEY (file_id) REFERENCES files(file_id)
    ON DELETE CASCADE,
  FOREIGN KEY (group_id) REFERENCES whats_groups(group_id)
    ON DELETE CASCADE
);

-- Tabela de contatos (sem FK para files)
CREATE TABLE IF NOT EXISTS contacts (
  contact_id INT AUTO_INCREMENT PRIMARY KEY,
  contact_phone VARCHAR(255) NOT NULL,
  contact_type VARCHAR(255) NOT NULL,
  UNIQUE (contact_phone, contact_type)
);

-- Tabela intermediária para relação N:N entre arquivos e contatos
CREATE TABLE IF NOT EXISTS file_contacts (
  file_id INT NOT NULL,
  contact_id INT NOT NULL,
  PRIMARY KEY (file_id, contact_id),
  FOREIGN KEY (file_id) REFERENCES files(file_id)
    ON DELETE CASCADE,
  FOREIGN KEY (contact_id) REFERENCES contacts(contact_id)
    ON DELETE CASCADE
);

-- Tabela de IPs
CREATE TABLE IF NOT EXISTS ips (
  sender_ip VARCHAR(255) PRIMARY KEY,
  continent VARCHAR(255),
  country VARCHAR(255),
  country_code VARCHAR(255),
  region VARCHAR(255),
  region_name VARCHAR(255),
  city VARCHAR(255),
  district VARCHAR(255),
  zipcode_ip VARCHAR(255),
  latitude VARCHAR(255),
  longitude VARCHAR(255),
  timezone_ip VARCHAR(255),
  isp TEXT,
  org TEXT,
  as_name TEXT,
  mobile TINYINT(1)
);

-- Tabela de mensagens (sem FK para whats_groups)
CREATE TABLE IF NOT EXISTS messages (
  message_id VARCHAR(255) PRIMARY KEY,
  file_id INT NOT NULL,
  timestamp TIMESTAMP,
  sender VARCHAR(255),
  group_id VARCHAR(255),
  sender_ip VARCHAR(255),
  sender_port VARCHAR(255),
  sender_device VARCHAR(255),
  message_type VARCHAR(255),
  message_style VARCHAR(255),
  message_size INT,
  FOREIGN KEY (file_id) REFERENCES files(file_id)
    ON DELETE CASCADE,
  FOREIGN KEY (sender_ip) REFERENCES ips(sender_ip)
);

-- Destinatários das mensagens (sem FK para whats_groups)
CREATE TABLE IF NOT EXISTS message_recipients (
  id INT AUTO_INCREMENT PRIMARY KEY,
  message_id VARCHAR(255) NOT NULL,
  recipient_phone VARCHAR(255) NOT NULL,
  FOREIGN KEY (message_id) REFERENCES messages(message_id)
    ON DELETE CASCADE
);

-- Trigger: Após deletar de file_groups
DROP TRIGGER IF EXISTS delete_orphan_groups_after_file_groups;
DELIMITER $$

CREATE TRIGGER delete_orphan_groups_after_file_groups
AFTER DELETE ON file_groups
FOR EACH ROW
BEGIN
    DELETE FROM group_metadata
    WHERE group_id IN (
        SELECT wg.group_id
        FROM whats_groups wg
        LEFT JOIN file_groups fg ON wg.group_id = fg.group_id
        WHERE fg.group_id IS NULL
    );

    DELETE FROM whats_groups
    WHERE group_id NOT IN (
        SELECT group_id FROM file_groups
    );
END$$
DELIMITER ;

-- Trigger: Após deletar de files
DROP TRIGGER IF EXISTS delete_orphan_groups_after_files;
DELIMITER $$

CREATE TRIGGER delete_orphan_groups_after_files
AFTER DELETE ON files
FOR EACH ROW
BEGIN
    DELETE FROM group_metadata
    WHERE group_id IN (
        SELECT wg.group_id
        FROM whats_groups wg
        LEFT JOIN file_groups fg ON wg.group_id = fg.group_id
        WHERE fg.group_id IS NULL
    );

    DELETE FROM whats_groups
    WHERE group_id NOT IN (
        SELECT group_id FROM file_groups
    );
END$$
DELIMITER ;

-- Trigger: Após deletar de targets
DROP TRIGGER IF EXISTS delete_orphan_groups_after_targets;
DELIMITER $$

CREATE TRIGGER delete_orphan_groups_after_targets
AFTER DELETE ON targets
FOR EACH ROW
BEGIN
    DELETE FROM group_metadata
    WHERE group_id IN (
        SELECT wg.group_id
        FROM whats_groups wg
        LEFT JOIN file_groups fg ON wg.group_id = fg.group_id
        WHERE fg.group_id IS NULL
    );

    DELETE FROM whats_groups
    WHERE group_id NOT IN (
        SELECT group_id FROM file_groups
    );
END$$
DELIMITER ;

-- Trigger: Após deletar de operation_targets
DROP TRIGGER IF EXISTS delete_orphan_groups_after_operation_targets;
DELIMITER $$

CREATE TRIGGER delete_orphan_groups_after_operation_targets
AFTER DELETE ON operation_targets
FOR EACH ROW
BEGIN
    DELETE FROM group_metadata
    WHERE group_id IN (
        SELECT wg.group_id
        FROM whats_groups wg
        LEFT JOIN file_groups fg ON wg.group_id = fg.group_id
        WHERE fg.group_id IS NULL
    );

    DELETE FROM whats_groups
    WHERE group_id NOT IN (
        SELECT group_id FROM file_groups
    );
END$$
DELIMITER ;

-- Trigger: Após deletar de operations
DROP TRIGGER IF EXISTS delete_orphan_groups_after_operations;
DELIMITER $$

CREATE TRIGGER delete_orphan_groups_after_operations
AFTER DELETE ON operations
FOR EACH ROW
BEGIN
    DELETE FROM group_metadata
    WHERE group_id IN (
        SELECT wg.group_id
        FROM whats_groups wg
        LEFT JOIN file_groups fg ON wg.group_id = fg.group_id
        WHERE fg.group_id IS NULL
    );

    DELETE FROM whats_groups
    WHERE group_id NOT IN (
        SELECT group_id FROM file_groups
    );
END$$
DELIMITER ;

-- Trigger: Após deletar de file_contacts
DROP TRIGGER IF EXISTS delete_orphan_contacts_after_file_contacts;
DELIMITER $$

CREATE TRIGGER delete_orphan_contacts_after_file_contacts
AFTER DELETE ON file_contacts
FOR EACH ROW
BEGIN
    DELETE FROM contacts
    WHERE contact_id NOT IN (
        SELECT contact_id FROM file_contacts
    );
END$$
DELIMITER ;

-- Trigger: Após deletar de files
DROP TRIGGER IF EXISTS delete_orphan_contacts_after_files;
DELIMITER $$

CREATE TRIGGER delete_orphan_contacts_after_files
AFTER DELETE ON files
FOR EACH ROW
BEGIN
    DELETE FROM contacts
    WHERE contact_id NOT IN (
        SELECT contact_id FROM file_contacts
    );
END$$
DELIMITER ;

-- Trigger: Após deletar de targets
DROP TRIGGER IF EXISTS delete_orphan_contacts_after_targets;
DELIMITER $$

CREATE TRIGGER delete_orphan_contacts_after_targets
AFTER DELETE ON targets
FOR EACH ROW
BEGIN
    DELETE FROM contacts
    WHERE contact_id NOT IN (
        SELECT contact_id FROM file_contacts
    );
END$$
DELIMITER ;

-- Trigger: Após deletar de operation_targets
DROP TRIGGER IF EXISTS delete_orphan_contacts_after_operation_targets;
DELIMITER $$

CREATE TRIGGER delete_orphan_contacts_after_operation_targets
AFTER DELETE ON operation_targets
FOR EACH ROW
BEGIN
    DELETE FROM contacts
    WHERE contact_id NOT IN (
        SELECT contact_id FROM file_contacts
    );
END$$
DELIMITER ;

-- Trigger: Após deletar de operations
DROP TRIGGER IF EXISTS delete_orphan_contacts_after_operations;
DELIMITER $$

CREATE TRIGGER delete_orphan_contacts_after_operations
AFTER DELETE ON operations
FOR EACH ROW
BEGIN
    DELETE FROM contacts
    WHERE contact_id NOT IN (
        SELECT contact_id FROM file_contacts
    );
END$$
DELIMITER ;

-- Trigger: Após deletar de operations - remove targets órfãos
DROP TRIGGER IF EXISTS delete_orphan_targets_after_operations;
DELIMITER $$

CREATE TRIGGER delete_orphan_targets_after_operations
AFTER DELETE ON operations
FOR EACH ROW
BEGIN
    DELETE FROM targets
    WHERE target_id NOT IN (
        SELECT target_id FROM operation_targets
    );
END$$
DELIMITER ;
