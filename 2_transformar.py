"""
Le a camada Raw, tipa/limpa os dados e grava na camada Silver.
"""

from __future__ import annotations

import sys
from datetime import datetime
from decimal import Decimal, InvalidOperation

from banco import conectar, executar, inserir_em_lote


# Funções de conversão (tratamento de dados)
VALORES_SEM_INFO = {
    "",
    "sem informacao",
    "sem informação",
    "nao informado",
    "não informado",
    "-1",
    "n/a",
    "na",
}


def limpar_texto(valor: str | None) -> str | None:
    if valor is None:
        return None
    texto = valor.strip()
    if not texto or texto.lower() in VALORES_SEM_INFO:
        return None
    return texto


def para_decimal(valor: str | None) -> Decimal | None:
    """Converte texto no padrao BR (1272,97) para Decimal."""
    texto = limpar_texto(valor)
    if texto is None:
        return None
    texto = texto.replace(".", "").replace(",", ".")
    try:
        return Decimal(texto)
    except (InvalidOperation, ValueError):
        return None


def para_data(valor: str | None):
    """Converte DD/MM/AAAA para date."""
    texto = limpar_texto(valor)
    if texto is None:
        return None
    for fmt in ("%d/%m/%Y", "%d/%m/%y"):
        try:
            return datetime.strptime(texto, fmt).date()
        except ValueError:
            continue
    return None


def para_int(valor: str | None) -> int | None:
    texto = limpar_texto(valor)
    if texto is None:
        return None
    try:
        return int(Decimal(texto.replace(",", ".")))
    except (InvalidOperation, ValueError):
        return None


def decimal_ou_zero(valor: Decimal | None) -> Decimal:
    return valor if valor is not None else Decimal("0")


# Transformacoes por tabela
SQL_INSERT_VIAGEM = """
INSERT INTO silver_viagem (
    id_viagem, num_proposta, situacao, viagem_urgente,
    nome_orgao_superior, nome_orgao_solicitante, nome_viajante, cargo,
    data_inicio, data_fim, destinos, motivo,
    valor_diarias, valor_passagens, valor_devolucao, valor_outros_gastos,
    valor_total, duracao_dias
) VALUES (
    %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s
)
"""

SQL_INSERT_PAGAMENTO = """
INSERT INTO silver_pagamento (
    id_viagem, num_proposta, nome_orgao_pagador, nome_ug_pagadora,
    tipo_pagamento, valor
) VALUES (%s, %s, %s, %s, %s, %s)
"""

SQL_INSERT_PASSAGEM = """
INSERT INTO silver_passagem (
    id_viagem, meio_transporte,
    pais_origem_ida, uf_origem_ida, cidade_origem_ida,
    pais_destino_ida, uf_destino_ida, cidade_destino_ida,
    valor_passagem, taxa_servico, data_emissao
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""

SQL_INSERT_TRECHO = """
INSERT INTO silver_trecho (
    id_viagem, sequencia_trecho,
    origem_data, origem_uf, origem_cidade,
    destino_data, destino_uf, destino_cidade,
    meio_transporte, numero_diarias
) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
"""


def carregar_ids_viagem(conexao) -> set[str]:
    cursor = conexao.cursor()
    cursor.execute("SELECT id_viagem FROM silver_viagem")
    ids = {row[0] for row in cursor.fetchall()}
    cursor.close()
    return ids


def transformar_viagem(conexao) -> int:
    cursor = conexao.cursor()
    cursor.execute(
        """
        SELECT
            identificador_processo_viagem, numero_proposta_pcdp, situacao,
            viagem_urgente, nome_orgao_superior, nome_orgao_solicitante,
            nome, cargo, periodo_data_inicio, periodo_data_fim, destinos,
            motivo, valor_diarias, valor_passagens, valor_devolucao,
            valor_outros_gastos
        FROM raw_viagem
        """
    )
    linhas = cursor.fetchall()
    cursor.close()

    lote = []
    vistos = set()
    ignoradas = 0

    for row in linhas:
        id_viagem = limpar_texto(row[0])
        nome_orgao = limpar_texto(row[4])

        # PK e NOT NULL obrigatorios
        if not id_viagem or not nome_orgao:
            ignoradas += 1
            continue
        if id_viagem in vistos:
            ignoradas += 1
            continue
        vistos.add(id_viagem)

        diarias = para_decimal(row[12])
        passagens = para_decimal(row[13])
        devolucao = para_decimal(row[14])
        outros = para_decimal(row[15])

        diarias = decimal_ou_zero(diarias)
        passagens = decimal_ou_zero(passagens)
        devolucao = decimal_ou_zero(devolucao)
        outros = decimal_ou_zero(outros)
        if diarias < 0:
            diarias = Decimal("0")
        if passagens < 0:
            passagens = Decimal("0")
        if devolucao < 0:
            devolucao = Decimal("0")
        if outros < 0:
            outros = Decimal("0")

        data_inicio = para_data(row[8])
        data_fim = para_data(row[9])
        duracao = None
        if data_inicio and data_fim:
            duracao = (data_fim - data_inicio).days
            if duracao < 0:
                duracao = None

        valor_total = diarias + passagens + outros - devolucao

        lote.append(
            (
                id_viagem,
                limpar_texto(row[1]),
                limpar_texto(row[2]),
                limpar_texto(row[3]),
                nome_orgao,
                limpar_texto(row[5]),
                limpar_texto(row[6]),
                limpar_texto(row[7]),
                data_inicio,
                data_fim,
                limpar_texto(row[10]),
                limpar_texto(row[11]),
                diarias,
                passagens,
                devolucao,
                outros,
                valor_total,
                duracao,
            )
        )

    inserir_em_lote(conexao, SQL_INSERT_VIAGEM, lote)
    print(f"  silver_viagem: {len(lote)} linhas (ignoradas: {ignoradas})")
    return len(lote)


def transformar_pagamento(conexao, ids_validos: set[str]) -> int:
    cursor = conexao.cursor()
    cursor.execute(
        """
        SELECT
            identificador_processo_viagem, numero_proposta_pcdp,
            nome_orgao_pagador, nome_unidade_gestora_pagadora,
            tipo_pagamento, valor
        FROM raw_pagamento
        """
    )
    linhas = cursor.fetchall()
    cursor.close()

    lote = []
    ignoradas = 0
    for row in linhas:
        id_viagem = limpar_texto(row[0])
        tipo = limpar_texto(row[4])
        valor = para_decimal(row[5])

        if not id_viagem or id_viagem not in ids_validos:
            ignoradas += 1
            continue
        if not tipo:
            ignoradas += 1
            continue
        if valor is None or valor < 0:
            valor = Decimal("0")

        lote.append(
            (
                id_viagem,
                limpar_texto(row[1]),
                limpar_texto(row[2]),
                limpar_texto(row[3]),
                tipo,
                valor,
            )
        )

    inserir_em_lote(conexao, SQL_INSERT_PAGAMENTO, lote)
    print(f"  silver_pagamento: {len(lote)} linhas (ignoradas: {ignoradas})")
    return len(lote)


def transformar_passagem(conexao, ids_validos: set[str]) -> int:
    cursor = conexao.cursor()
    cursor.execute(
        """
        SELECT
            identificador_processo_viagem, meio_transporte,
            pais_origem_ida, uf_origem_ida, cidade_origem_ida,
            pais_destino_ida, uf_destino_ida, cidade_destino_ida,
            valor_passagem, taxa_servico, data_emissao_compra
        FROM raw_passagem
        """
    )
    linhas = cursor.fetchall()
    cursor.close()

    lote = []
    ignoradas = 0
    for row in linhas:
        id_viagem = limpar_texto(row[0])
        if not id_viagem or id_viagem not in ids_validos:
            ignoradas += 1
            continue

        valor_passagem = para_decimal(row[8])
        taxa = para_decimal(row[9])
        if valor_passagem is None or valor_passagem < 0:
            valor_passagem = Decimal("0")
        if taxa is None or taxa < 0:
            taxa = Decimal("0")

        lote.append(
            (
                id_viagem,
                limpar_texto(row[1]),
                limpar_texto(row[2]),
                limpar_texto(row[3]),
                limpar_texto(row[4]),
                limpar_texto(row[5]),
                limpar_texto(row[6]),
                limpar_texto(row[7]),
                valor_passagem,
                taxa,
                para_data(row[10]),
            )
        )

    inserir_em_lote(conexao, SQL_INSERT_PASSAGEM, lote)
    print(f"  silver_passagem: {len(lote)} linhas (ignoradas: {ignoradas})")
    return len(lote)


def transformar_trecho(conexao, ids_validos: set[str]) -> int:
    cursor = conexao.cursor()
    cursor.execute(
        """
        SELECT
            identificador_processo_viagem, sequencia_trecho,
            origem_data, origem_uf, origem_cidade,
            destino_data, destino_uf, destino_cidade,
            meio_transporte, numero_diarias
        FROM raw_trecho
        """
    )
    linhas = cursor.fetchall()
    cursor.close()

    lote = []
    vistos = set()
    ignoradas = 0
    for row in linhas:
        id_viagem = limpar_texto(row[0])
        seq = para_int(row[1])
        if not id_viagem or id_viagem not in ids_validos:
            ignoradas += 1
            continue
        if seq is None:
            ignoradas += 1
            continue

        chave = (id_viagem, seq)
        if chave in vistos:
            ignoradas += 1
            continue
        vistos.add(chave)

        diarias = para_decimal(row[9])
        if diarias is None or diarias < 0:
            diarias = Decimal("0")

        lote.append(
            (
                id_viagem,
                seq,
                para_data(row[2]),
                limpar_texto(row[3]),
                limpar_texto(row[4]),
                para_data(row[5]),
                limpar_texto(row[6]),
                limpar_texto(row[7]),
                limpar_texto(row[8]),
                diarias,
            )
        )

    inserir_em_lote(conexao, SQL_INSERT_TRECHO, lote)
    print(f"  silver_trecho: {len(lote)} linhas (ignoradas: {ignoradas})")
    return len(lote)


def limpar_silver(conexao) -> None:
    """TRUNCATE nas silver (filhas primeiro) para reexecucao segura."""
    executar(conexao, "TRUNCATE TABLE silver_trecho RESTART IDENTITY CASCADE")
    executar(conexao, "TRUNCATE TABLE silver_passagem RESTART IDENTITY CASCADE")
    executar(conexao, "TRUNCATE TABLE silver_pagamento RESTART IDENTITY CASCADE")
    executar(conexao, "TRUNCATE TABLE silver_viagem CASCADE")


def main() -> None:
    try:
        conexao = conectar()
        try:
            print("Limpando camada Silver...")
            limpar_silver(conexao)

            print("Transformando viagens...")
            transformar_viagem(conexao)
            ids = carregar_ids_viagem(conexao)

            print("Transformando pagamentos...")
            transformar_pagamento(conexao, ids)

            print("Transformando passagens...")
            transformar_passagem(conexao, ids)

            print("Transformando trechos...")
            transformar_trecho(conexao, ids)

            print("Transformacao concluida.")
        finally:
            conexao.close()
    except Exception as erro:
        print(f"Erro na transformacao: {erro}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
