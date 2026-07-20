# Pipeline de Viagens a Serviço — Portal da Transparência

Projeto avaliativo (arquitetura Medallion: **Raw → Silver → Gold**) sobre dados de viagens a serviço do Governo Federal (jan–jun/2025).

## Escopo

Consultoria de dados para organizar o fluxo de informação de viagens:

1. **Raw** — cópia fiel dos CSVs (sem tipagem, sem constraints)
2. **Silver** — limpeza, tipagem, integridade referencial e colunas calculadas
3. **Gold** — agregações (`JOIN` + `GROUP BY`) em tabela e VIEW, com análises e gráficos

## Tecnologias

- Python 3
- PostgreSQL 16 (Docker)
- `psycopg2`, `gdown`, `pandas`, `matplotlib`, `seaborn`, Jupyter

## Estrutura

| Arquivo | Função |
|---------|--------|
| `config.py` | Parâmetros e leitura do `.env` |
| `banco.py` | Conexão e helpers SQL |
| `0_criar_banco.sql` | 4 tabelas Raw + 4 Silver (PK/FK/constraints) |
| `1_extrair.py` | Download do Drive + carga Raw (blocos + `TRUNCATE`) |
| `2_transformar.py` | Raw → Silver (tipagem + `valor_total` / `duracao_dias`) |
| `3_analise.ipynb` | Gold + 6 perguntas de negócio + gráficos |
| `docker-compose.yaml` | Postgres local na porta **5433** |

## Como executar

### 1. Ambiente

```bash
python -m venv .venv
source .venv/bin/activate   # Windows: .venv\Scripts\activate
pip install -r requirements.txt
cp .env.example .env        # ajuste senha/porta se precisar
```

### 2. Banco

```bash
docker compose up -d
# aguardar o Postgres subir, depois:
PGPASSWORD=postgres psql -h localhost -p 5433 -U postgres -d transparencia -f 0_criar_banco.sql
```

### 3. Pipeline

```bash
python 1_extrair.py      # baixa o zip do Drive e carrega a Raw
python 2_transformar.py  # limpa/tipa e grava a Silver
jupyter notebook 3_analise.ipynb
```

O `DRIVE_FILE_ID` já está em `config.py`. Os CSVs ficam em `data/` (ignorada pelo Git).

## Camada Silver — constraints

| Tabela | Constraints extras |
|--------|--------------------|
| `silver_viagem` | `NOT NULL nome_orgao_superior`, `CHECK (valor_diarias >= 0)` |
| `silver_pagamento` | `NOT NULL tipo_pagamento`, `CHECK (valor >= 0)` |
| `silver_passagem` | `CHECK (valor_passagem >= 0)`, `CHECK (taxa_servico >= 0)` |
| `silver_trecho` | `CHECK (numero_diarias >= 0)`, `UNIQUE (id_viagem, sequencia_trecho)` |

Colunas calculadas em `silver_viagem`: `valor_total` e `duracao_dias`.

## Melhorias futuras

- Particionar carga por mês
- Camada trusted intermediária com qualidade de dados
- Dashboard Streamlit / Power BI em cima da Gold
- Testes automatizados de idempotência do pipeline

## Insights (após rodar o notebook)

- Órgãos no topo concentram boa parte do gasto com pagamentos.
- Destinos com alto custo médio misturam deslocamentos longos e diárias.
- Duração máxima aponta outliers (afastamentos longos).
- Tipo de pagamento e meio de transporte mostram o perfil operacional.
- UFs de destino mais frequentes indicam a concentração geográfica no período.