"""Compara dois registros e diz o quanto eles parecem ser a mesma pessoa."""

from __future__ import annotations

from difflib import SequenceMatcher

# Pesos da pontuação quando não há CPF para decidir (somam 1,0).
PESO_NOME = 0.5
PESO_EMAIL = 0.2
PESO_TELEFONE = 0.2
PESO_NASCIMENTO = 0.1
PENALIDADE_NASCIMENTO_DIFERENTE = 0.3


def similaridade_nomes(a: str, b: str) -> float:
    """Nota de 0 a 1 para dois nomes JÁ normalizados.

    Usa o SequenceMatcher (biblioteca padrão do Python), que tolera erros
    de digitação: "MARIA SILVA" x "MARIA SILVAA" dá ~0,95.

    Também trata dois casos comuns em cadastros:
    * nomes em outra ordem ("SILVA MARIA");
    * nome do meio faltando ou abreviado ("MARIA SILVA" x "MARIA JOSE SILVA").
      Se o primeiro e o último nome batem, a nota é pelo menos 0,9.
    """
    if not a or not b:
        return 0.0
    if a == b:
        return 1.0

    direta = SequenceMatcher(None, a, b).ratio()
    ordenada = SequenceMatcher(None, " ".join(sorted(a.split())), " ".join(sorted(b.split()))).ratio()
    nota = max(direta, ordenada)

    palavras_a, palavras_b = a.split(), b.split()
    if palavras_a[0] == palavras_b[0] and palavras_a[-1] == palavras_b[-1]:
        nota = max(nota, 0.9)
    return round(nota, 3)


def pontuar_par(r1: dict, r2: dict) -> tuple[float, str]:
    """Devolve (pontuação de 0 a 1, explicação).

    Os registros já devem estar normalizados, com as chaves
    `cpf`, `nome_norm`, `email`, `telefone` e `nascimento`.
    """
    # 1) O CPF decide sozinho, quando os dois registros têm um CPF válido.
    if r1["cpf"] and r2["cpf"]:
        if r1["cpf"] == r2["cpf"]:
            return 1.0, "mesmo CPF"
        return 0.0, "CPFs diferentes"

    # 2) Sem CPF nos dois, somamos evidências.
    nome = similaridade_nomes(r1["nome_norm"], r2["nome_norm"])
    pontos = PESO_NOME * nome
    motivos = [f"nome {nome:.0%} parecido"]

    if r1["email"] and r1["email"] == r2["email"]:
        pontos += PESO_EMAIL
        motivos.append("mesmo e-mail")
    if r1["telefone"] and r1["telefone"] == r2["telefone"]:
        pontos += PESO_TELEFONE
        motivos.append("mesmo telefone")
    if r1["nascimento"] and r2["nascimento"]:
        if r1["nascimento"] == r2["nascimento"]:
            pontos += PESO_NASCIMENTO
            motivos.append("mesma data de nascimento")
        else:
            # Ex.: pai e filho "Júnior" com o mesmo nome e o mesmo telefone de casa.
            pontos -= PENALIDADE_NASCIMENTO_DIFERENTE
            motivos.append("datas de nascimento diferentes")

    return round(max(pontos, 0.0), 3), ", ".join(motivos)
