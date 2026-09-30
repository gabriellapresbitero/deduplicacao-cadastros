"""Blocagem: escolhe quais pares de registros vale a pena comparar.

Comparar todos com todos é caro: 100 mil registros dariam quase
5 bilhões de pares (n × (n − 1) / 2). Na prática, dois registros só têm
chance de ser a mesma pessoa se compartilham ALGUMA coisa: o CPF, o
e-mail, o telefone, ou o nome junto com a data de nascimento.

Então agrupamos os registros por essas "chaves" e só comparamos quem cai
no mesmo grupo (bloco). O número de comparações cai drasticamente.
"""

from __future__ import annotations

from collections import defaultdict
from itertools import combinations

# Blocos gigantes (ex.: um telefone de empresa usado em 500 cadastros)
# gerariam pares demais e quase nunca são a mesma pessoa. Ficam de fora.
TAMANHO_MAXIMO_BLOCO = 50


def chaves_do_registro(registro: dict) -> list[str]:
    chaves = []
    if registro["cpf"]:
        chaves.append("cpf:" + registro["cpf"])
    if registro["email"]:
        chaves.append("email:" + registro["email"])
    if registro["telefone"]:
        chaves.append("tel:" + registro["telefone"])

    palavras = registro["nome_norm"].split()
    if palavras:
        primeiro_e_ultimo = f"{palavras[0]} {palavras[-1]}"
        if registro["nascimento"]:
            chaves.append(f"nome_nasc:{primeiro_e_ultimo}|{registro['nascimento']}")
        # Nome parecido sem nenhum outro dado em comum ainda pode ser a mesma pessoa
        # (ex.: cadastro antigo sem e-mail). As 3 primeiras letras toleram erros no fim.
        chaves.append(f"nome:{palavras[0][:3]}|{palavras[-1][:3]}")
    return chaves


def gerar_pares(registros: list[dict]) -> set[tuple[int, int]]:
    """Devolve os pares (i, j), com i < j, de posições na lista que devem ser comparadas."""
    blocos: dict[str, list[int]] = defaultdict(list)
    for posicao, registro in enumerate(registros):
        for chave in chaves_do_registro(registro):
            blocos[chave].append(posicao)

    pares = set()
    for membros in blocos.values():
        if 2 <= len(membros) <= TAMANHO_MAXIMO_BLOCO:
            pares.update(combinations(sorted(membros), 2))
    return pares
