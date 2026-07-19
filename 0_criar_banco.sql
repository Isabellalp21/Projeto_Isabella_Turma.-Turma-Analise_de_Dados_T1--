-- 0_criar_banco.sql
-- Cria as 8 tabelas (4 Raw + 4 Silver) no banco transparencia.

-- Remove layers anteriores
DROP TABLE IF EXISTS silver_trecho CASCADE;
DROP TABLE IF EXISTS silver_passagem CASCADE;
DROP TABLE IF EXISTS silver_pagamento CASCADE;
DROP TABLE IF EXISTS silver_viagem CASCADE;
DROP TABLE IF EXISTS raw_trecho CASCADE;
DROP TABLE IF EXISTS raw_passagem CASCADE;
DROP TABLE IF EXISTS raw_pagamento CASCADE;
DROP TABLE IF EXISTS raw_viagem CASCADE;


-- CAMADA RAW — copia fiel do CSV (tudo VARCHAR, sem constraints)
CREATE TABLE raw_viagem (
    identificador_processo_viagem   VARCHAR(50),
    numero_proposta_pcdp            VARCHAR(50),
    situacao                        VARCHAR(50),
    viagem_urgente                  VARCHAR(20),
    justificativa_urgencia_viagem   VARCHAR(4000),
    codigo_orgao_superior           VARCHAR(20),
    nome_orgao_superior             VARCHAR(255),
    codigo_orgao_solicitante        VARCHAR(20),
    nome_orgao_solicitante          VARCHAR(255),
    cpf_viajante                    VARCHAR(30),
    nome                            VARCHAR(255),
    cargo                           VARCHAR(255),
    funcao                          VARCHAR(100),
    descricao_funcao                VARCHAR(255),
    periodo_data_inicio             VARCHAR(20),
    periodo_data_fim                VARCHAR(20),
    destinos                        VARCHAR(1000),
    motivo                          VARCHAR(4000),
    valor_diarias                   VARCHAR(30),
    valor_passagens                 VARCHAR(30),
    valor_devolucao                 VARCHAR(30),
    valor_outros_gastos             VARCHAR(30)
);

CREATE TABLE raw_pagamento (
    identificador_processo_viagem   VARCHAR(50),
    numero_proposta_pcdp            VARCHAR(50),
    codigo_orgao_superior           VARCHAR(20),
    nome_orgao_superior             VARCHAR(255),
    codigo_orgao_pagador            VARCHAR(20),
    nome_orgao_pagador              VARCHAR(255),
    codigo_unidade_gestora_pagadora VARCHAR(20),
    nome_unidade_gestora_pagadora   VARCHAR(255),
    tipo_pagamento                  VARCHAR(50),
    valor                           VARCHAR(30)
);

CREATE TABLE raw_passagem (
    identificador_processo_viagem   VARCHAR(50),
    numero_proposta_pcdp            VARCHAR(50),
    meio_transporte                 VARCHAR(50),
    pais_origem_ida                 VARCHAR(60),
    uf_origem_ida                   VARCHAR(40),
    cidade_origem_ida               VARCHAR(80),
    pais_destino_ida                VARCHAR(60),
    uf_destino_ida                  VARCHAR(40),
    cidade_destino_ida              VARCHAR(80),
    pais_origem_volta               VARCHAR(60),
    uf_origem_volta                 VARCHAR(40),
    cidade_origem_volta             VARCHAR(80),
    pais_destino_volta              VARCHAR(60),
    uf_destino_volta                VARCHAR(40),
    cidade_destino_volta            VARCHAR(80),
    valor_passagem                  VARCHAR(30),
    taxa_servico                    VARCHAR(30),
    data_emissao_compra             VARCHAR(20),
    hora_emissao_compra             VARCHAR(20)
);

CREATE TABLE raw_trecho (
    identificador_processo_viagem   VARCHAR(50),
    numero_proposta_pcdp            VARCHAR(50),
    sequencia_trecho                VARCHAR(20),
    origem_data                     VARCHAR(20),
    origem_pais                     VARCHAR(60),
    origem_uf                       VARCHAR(40),
    origem_cidade                   VARCHAR(80),
    destino_data                    VARCHAR(20),
    destino_pais                    VARCHAR(60),
    destino_uf                      VARCHAR(40),
    destino_cidade                  VARCHAR(80),
    meio_transporte                 VARCHAR(50),
    numero_diarias                  VARCHAR(30),
    missao                          VARCHAR(20)
);


-- CAMADA SILVER — tipada, com PK, FK e constraints extras
CREATE TABLE silver_viagem (
    id_viagem               VARCHAR(20) PRIMARY KEY,
    num_proposta            VARCHAR(50),
    situacao                VARCHAR(50),
    viagem_urgente          VARCHAR(10),
    nome_orgao_superior     VARCHAR(255) NOT NULL,
    nome_orgao_solicitante  VARCHAR(255),
    nome_viajante           VARCHAR(255),
    cargo                   VARCHAR(255),
    data_inicio             DATE,
    data_fim                DATE,
    destinos                VARCHAR(1000),
    motivo                  VARCHAR(4000),
    valor_diarias           DECIMAL(12, 2) CHECK (valor_diarias >= 0),
    valor_passagens         DECIMAL(12, 2) CHECK (valor_passagens >= 0),
    valor_devolucao         DECIMAL(12, 2) CHECK (valor_devolucao >= 0),
    valor_outros_gastos     DECIMAL(12, 2) CHECK (valor_outros_gastos >= 0),
    valor_total             DECIMAL(12, 2), 
    duracao_dias            INTEGER         
);

CREATE TABLE silver_pagamento (
    id_pagamento            SERIAL PRIMARY KEY,
    id_viagem               VARCHAR(20) NOT NULL
        REFERENCES silver_viagem (id_viagem),
    num_proposta            VARCHAR(50),
    nome_orgao_pagador      VARCHAR(255),
    nome_ug_pagadora        VARCHAR(255),
    tipo_pagamento          VARCHAR(50) NOT NULL,
    valor                   DECIMAL(12, 2) CHECK (valor >= 0)
);

CREATE TABLE silver_passagem (
    id_passagem             SERIAL PRIMARY KEY,
    id_viagem               VARCHAR(20) NOT NULL
        REFERENCES silver_viagem (id_viagem),
    meio_transporte         VARCHAR(50),
    pais_origem_ida         VARCHAR(60),
    uf_origem_ida           VARCHAR(40),
    cidade_origem_ida       VARCHAR(80),
    pais_destino_ida        VARCHAR(60),
    uf_destino_ida          VARCHAR(40),
    cidade_destino_ida      VARCHAR(80),
    valor_passagem          DECIMAL(12, 2) CHECK (valor_passagem >= 0),
    taxa_servico            DECIMAL(12, 2) CHECK (taxa_servico >= 0),
    data_emissao            DATE
);

CREATE TABLE silver_trecho (
    id_trecho               SERIAL PRIMARY KEY,
    id_viagem               VARCHAR(20) NOT NULL
        REFERENCES silver_viagem (id_viagem),
    sequencia_trecho        INTEGER,
    origem_data             DATE,
    origem_uf               VARCHAR(40),
    origem_cidade           VARCHAR(80),
    destino_data            DATE,
    destino_uf              VARCHAR(40),
    destino_cidade          VARCHAR(80),
    meio_transporte         VARCHAR(50),
    numero_diarias          DECIMAL(12, 2) CHECK (numero_diarias >= 0),
    CONSTRAINT uq_trecho_viagem_seq UNIQUE (id_viagem, sequencia_trecho)
);

CREATE INDEX idx_silver_pagamento_viagem ON silver_pagamento (id_viagem);
CREATE INDEX idx_silver_passagem_viagem  ON silver_passagem (id_viagem);
CREATE INDEX idx_silver_trecho_viagem    ON silver_trecho (id_viagem);