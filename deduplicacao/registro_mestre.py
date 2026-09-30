"""Monta o "registro mestre" de cada grupo de duplicatas.

Quando três cadastros são a mesma pessoa, precisamos decidir qual valor
fica em cada campo. As regras:

* o registro mais recente (`atualizado_em`) tem prioridade;
* um campo vazio ou inválido nunca vence um campo preenchido e válido;
* para o nome, fica o mais completo (com mais palavras), porque cadastros
  antigos costumam ter o nome abreviado.
"""

from __future__ import annotations

import pandas as pd

CAMPOS = ["cpf", "email", "telefone", "nascimento", "cidade"]


def consolidar(grupo: pd.DataFrame) -> dict:
    """Recebe as linhas (já normalizadas) de um mesmo grupo e devolve um único registro."""
    ordenado = grupo.sort_values("atualizado_em", ascending=False, na_position="last")

    mestre = {
        "id_mestre": int(grupo["id"].min()),
        "registros_unidos": len(grupo),
        "ids_originais": ",".join(str(i) for i in sorted(grupo["id"])),
    }

    # Nome: o que tiver mais palavras; empate -> o mais recente (o primeiro após ordenar).
    candidatos = ordenado[ordenado["nome_norm"] != ""]
    if candidatos.empty:
        mestre["nome"] = ""
    else:
        posicao = candidatos["nome_norm"].str.split().str.len().idxmax()
        mestre["nome"] = formatar_nome(candidatos.loc[posicao, "nome"])

    for campo in CAMPOS:
        preenchidos = ordenado[ordenado[campo] != ""][campo]
        mestre[campo] = preenchidos.iloc[0] if not preenchidos.empty else ""
    return mestre


def formatar_nome(nome: str) -> str:
    """ "MARIA DA SILVA" -> "Maria da Silva" """
    palavras = str(nome).split()
    minusculas = {"da", "das", "de", "di", "do", "dos", "e"}
    return " ".join(p.lower() if p.lower() in minusculas else p.capitalize() for p in palavras)
