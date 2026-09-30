"""Junta todas as etapas: normalizar, comparar, agrupar e consolidar."""

from __future__ import annotations

from dataclasses import dataclass

import pandas as pd

from . import normalizacao as norm
from .agrupamento import agrupar
from .blocagem import gerar_pares
from .registro_mestre import consolidar
from .similaridade import pontuar_par

COLUNAS_OBRIGATORIAS = ["id", "nome"]
COLUNAS_OPCIONAIS = ["cpf", "email", "telefone", "data_nascimento", "cidade", "atualizado_em"]


@dataclass
class Resultado:
    unificados: pd.DataFrame  # um registro por pessoa
    mapa: pd.DataFrame  # id original -> id mestre
    revisao: pd.DataFrame  # pares na "zona cinzenta", para uma pessoa decidir
    pares_comparados: int
    pares_possiveis: int
    estatisticas: dict


def normalizar(cadastro: pd.DataFrame) -> pd.DataFrame:
    faltando = [c for c in COLUNAS_OBRIGATORIAS if c not in cadastro.columns]
    if faltando:
        raise ValueError(f"Colunas obrigatórias ausentes: {faltando}")
    if cadastro["id"].duplicated().any():
        raise ValueError("A coluna 'id' tem valores repetidos. Cada linha precisa de um id único.")

    tabela = cadastro.copy()
    for coluna in COLUNAS_OPCIONAIS:
        if coluna not in tabela.columns:
            tabela[coluna] = ""
    tabela = tabela.fillna("")

    tabela["nome_norm"] = tabela["nome"].map(norm.normalizar_nome)
    tabela["cpf"] = tabela["cpf"].map(norm.normalizar_cpf)
    tabela["email"] = tabela["email"].map(norm.normalizar_email)
    tabela["telefone"] = tabela["telefone"].map(norm.normalizar_telefone)
    tabela["nascimento"] = tabela["data_nascimento"].map(norm.normalizar_data)
    tabela["cidade"] = tabela["cidade"].map(lambda c: norm.normalizar_nome(c).title())
    tabela["atualizado_em"] = pd.to_datetime(tabela["atualizado_em"].map(norm.normalizar_data), errors="coerce")
    return tabela.reset_index(drop=True)


def deduplicar(cadastro: pd.DataFrame, limiar: float = 0.75, limiar_revisao: float = 0.6) -> Resultado:
    if not 0 < limiar_revisao <= limiar <= 1:
        raise ValueError("Os limiares precisam respeitar 0 < limiar_revisao <= limiar <= 1.")

    tabela = normalizar(cadastro)
    registros = tabela.to_dict("records")
    pares = gerar_pares(registros)

    duplicados, revisao = [], []
    for i, j in pares:
        pontuacao, motivo = pontuar_par(registros[i], registros[j])
        if pontuacao >= limiar:
            duplicados.append((pontuacao, i, j))
        elif pontuacao >= limiar_revisao:
            revisao.append((pontuacao, i, j, motivo))

    # Ligações mais fortes primeiro (veja agrupamento.agrupar).
    duplicados.sort(reverse=True)
    representantes = agrupar(tabela["cpf"].tolist(), [(i, j) for _, i, j in duplicados])
    tabela["grupo"] = representantes

    unificados = pd.DataFrame([consolidar(grupo) for _, grupo in tabela.groupby("grupo", sort=False)])
    unificados = unificados.sort_values("id_mestre").reset_index(drop=True)

    id_mestre_por_grupo = tabela.groupby("grupo")["id"].min()
    mapa = pd.DataFrame({"id_original": tabela["id"], "id_mestre": tabela["grupo"].map(id_mestre_por_grupo)})

    # Para revisão, só interessam pares que NÃO acabaram no mesmo grupo por outro caminho.
    linhas_revisao = [
        {
            "id_a": registros[i]["id"], "nome_a": registros[i]["nome"],
            "id_b": registros[j]["id"], "nome_b": registros[j]["nome"],
            "pontuacao": pontuacao, "motivo": motivo,
        }
        for pontuacao, i, j, motivo in sorted(revisao, reverse=True)
        if representantes[i] != representantes[j]
    ]

    n = len(tabela)
    return Resultado(
        unificados=unificados,
        mapa=mapa.sort_values("id_original").reset_index(drop=True),
        revisao=pd.DataFrame(linhas_revisao, columns=["id_a", "nome_a", "id_b", "nome_b", "pontuacao", "motivo"]),
        pares_comparados=len(pares),
        pares_possiveis=n * (n - 1) // 2,
        estatisticas={
            "registros_entrada": n,
            "pessoas_unicas": len(unificados),
            "duplicatas_removidas": n - len(unificados),
            "pares_para_revisao": len(linhas_revisao),
        },
    )
