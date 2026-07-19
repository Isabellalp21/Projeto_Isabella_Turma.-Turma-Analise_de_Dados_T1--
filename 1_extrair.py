"""
Baixa o .zip do Google Drive, le os 4 CSVs em blocos e carrega a camada Raw.
"""

from __future__ import annotations

import csv
import sys
import zipfile
from pathlib import Path

import gdown

from banco import conectar, executar, inserir_em_lote
from config import (
    ARQUIVOS,
    CSV_ENCODING,
    CSV_SEPARADOR,
    DRIVE_FILE_ID,
    PASTA_DADOS,
    TAMANHO_BLOCO,
)

# Colunas na mesma ordem das tabelas raw (0_criar_banco.sql)
COLUNAS_RAW = {
    "raw_viagem": [
        "identificador_processo_viagem",
        "numero_proposta_pcdp",
        "situacao",
        "viagem_urgente",
        "justificativa_urgencia_viagem",
        "codigo_orgao_superior",
        "nome_orgao_superior",
        "codigo_orgao_solicitante",
        "nome_orgao_solicitante",
        "cpf_viajante",
        "nome",
        "cargo",
        "funcao",
        "descricao_funcao",
        "periodo_data_inicio",
        "periodo_data_fim",
        "destinos",
        "motivo",
        "valor_diarias",
        "valor_passagens",
        "valor_devolucao",
        "valor_outros_gastos",
    ],
    "raw_pagamento": [
        "identificador_processo_viagem",
        "numero_proposta_pcdp",
        "codigo_orgao_superior",
        "nome_orgao_superior",
        "codigo_orgao_pagador",
        "nome_orgao_pagador",
        "codigo_unidade_gestora_pagadora",
        "nome_unidade_gestora_pagadora",
        "tipo_pagamento",
        "valor",
    ],
    "raw_passagem": [
        "identificador_processo_viagem",
        "numero_proposta_pcdp",
        "meio_transporte",
        "pais_origem_ida",
        "uf_origem_ida",
        "cidade_origem_ida",
        "pais_destino_ida",
        "uf_destino_ida",
        "cidade_destino_ida",
        "pais_origem_volta",
        "uf_origem_volta",
        "cidade_origem_volta",
        "pais_destino_volta",
        "uf_destino_volta",
        "cidade_destino_volta",
        "valor_passagem",
        "taxa_servico",
        "data_emissao_compra",
        "hora_emissao_compra",
    ],
    "raw_trecho": [
        "identificador_processo_viagem",
        "numero_proposta_pcdp",
        "sequencia_trecho",
        "origem_data",
        "origem_pais",
        "origem_uf",
        "origem_cidade",
        "destino_data",
        "destino_pais",
        "destino_uf",
        "destino_cidade",
        "meio_transporte",
        "numero_diarias",
        "missao",
    ],
}


def baixar_zip() -> Path:
    """Baixa o arquivo do Drive para PASTA_DADOS/viagens.zip."""
    if not DRIVE_FILE_ID or DRIVE_FILE_ID.startswith("COLE_AQUI"):
        raise RuntimeError("DRIVE_FILE_ID nao configurado em config.py")

    PASTA_DADOS.mkdir(parents=True, exist_ok=True)
    destino = PASTA_DADOS / "viagens.zip"
    url = f"https://drive.google.com/uc?id={DRIVE_FILE_ID}"

    print(f"Baixando zip do Drive ({DRIVE_FILE_ID})...")
    saida = gdown.download(url, str(destino), quiet=False)
    if not saida:
        raise RuntimeError(
            "Falha ao baixar o arquivo. Confira o DRIVE_FILE_ID e o "
            "compartilhamento do Drive (qualquer pessoa com o link)."
        )
    return Path(saida)


def extrair_zip(arquivo_zip: Path) -> None:
    """Extrai o conteudo do zip em PASTA_DADOS."""
    print(f"Extraindo {arquivo_zip.name} em {PASTA_DADOS}...")
    with zipfile.ZipFile(arquivo_zip, "r") as zf:
        zf.extractall(PASTA_DADOS)


def localizar_csv(nome_arquivo: str) -> Path:
    """Procura o CSV na pasta data (inclusive em subpastas)."""
    direto = PASTA_DADOS / nome_arquivo
    if direto.exists():
        return direto

    encontrados = list(PASTA_DADOS.rglob(nome_arquivo))
    if not encontrados:
        raise FileNotFoundError(
            f"Arquivo {nome_arquivo} nao encontrado em {PASTA_DADOS}"
        )
    return encontrados[0]


def sql_insert(tabela: str, colunas: list[str]) -> str:
    cols = ", ".join(colunas)
    placeholders = ", ".join(["%s"] * len(colunas))
    return f"INSERT INTO {tabela} ({cols}) VALUES ({placeholders})"


def limpar_celula(valor: str | None) -> str | None:
    if valor is None:
        return None
    texto = valor.strip().strip('"')
    return texto if texto else None


def carregar_csv_na_raw(conexao, caminho_csv: Path, tabela: str) -> int:
    """Le o CSV em blocos e insere na tabela raw. Retorna total de linhas."""
    colunas = COLUNAS_RAW[tabela]
    insert = sql_insert(tabela, colunas)
    total = 0
    bloco: list[tuple] = []

    executar(conexao, f"TRUNCATE TABLE {tabela}")

    with caminho_csv.open("r", encoding=CSV_ENCODING, newline="") as arquivo:
        leitor = csv.reader(arquivo, delimiter=CSV_SEPARADOR)
        next(leitor, None)

        for linha in leitor:
            while len(linha) < len(colunas):
                linha.append("")
            valores = tuple(limpar_celula(c) for c in linha[: len(colunas)])
            bloco.append(valores)

            if len(bloco) >= TAMANHO_BLOCO:
                inserir_em_lote(conexao, insert, bloco)
                total += len(bloco)
                print(f"  {tabela}: {total} linhas...")
                bloco = []

        if bloco:
            inserir_em_lote(conexao, insert, bloco)
            total += len(bloco)

    return total


def garantir_csvs() -> None:
    """Baixa o zip do Drive e extrai os CSVs em data/."""
    arquivo_zip = baixar_zip()
    extrair_zip(arquivo_zip)


def main() -> None:
    try:
        garantir_csvs()

        conexao = conectar()
        try:
            for chave, info in ARQUIVOS.items():
                csv_path = localizar_csv(info["csv"])
                tabela = info["tabela_raw"]
                print(f"Carregando {csv_path.name} -> {tabela}")
                total = carregar_csv_na_raw(conexao, csv_path, tabela)
                print(f"  OK: {total} linhas em {tabela}")
        finally:
            conexao.close()

        print("Extracao concluida.")
    except Exception as erro:
        print(f"Erro na extracao: {erro}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
