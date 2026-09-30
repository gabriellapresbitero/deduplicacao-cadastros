"""Normalização dos campos de um cadastro.

Antes de comparar dois registros, colocamos todos os campos no mesmo
formato. "José da Silva", "JOSE  DA SILVA" e "jose da silva " precisam
virar exatamente o mesmo texto, senão nunca serão reconhecidos como iguais.
"""

from __future__ import annotations

import re
import unicodedata
from datetime import date, datetime

# Palavras que não ajudam a diferenciar nomes ("Maria DA Silva" = "Maria Silva").
PARTICULAS = {"DA", "DAS", "DE", "DI", "DO", "DOS", "E"}

REGEX_EMAIL = re.compile(r"^[a-z0-9._%+-]+@[a-z0-9-]+(\.[a-z0-9-]+)*\.[a-z]{2,}$")


def remover_acentos(texto: str) -> str:
    decomposto = unicodedata.normalize("NFKD", texto)
    return "".join(c for c in decomposto if not unicodedata.combining(c))


def normalizar_nome(nome: str | None) -> str:
    """ "  José  da Silva " -> "JOSE SILVA" """
    if not nome:
        return ""
    texto = remover_acentos(str(nome)).upper()
    texto = re.sub(r"[^A-Z ]", " ", texto)  # tira pontos, números e símbolos
    palavras = [p for p in texto.split() if p not in PARTICULAS]
    return " ".join(palavras)


def somente_digitos(texto: str | None) -> str:
    return re.sub(r"\D", "", str(texto or ""))


def cpf_valido(cpf: str) -> bool:
    numeros = [int(c) for c in somente_digitos(cpf)]
    if len(numeros) != 11 or len(set(numeros)) == 1:
        return False
    for posicao in (9, 10):
        soma = sum(n * p for n, p in zip(numeros[:posicao], range(posicao + 1, 1, -1)))
        digito = (soma * 10) % 11 % 10
        if numeros[posicao] != digito:
            return False
    return True


def normalizar_cpf(cpf: str | None) -> str:
    """Devolve os 11 dígitos do CPF, ou "" se o CPF for inválido.

    CPFs com zeros à esquerda costumam perder esses zeros em planilhas
    ("01234567890" vira "1234567890"). Por isso completamos com zeros.
    """
    digitos = somente_digitos(cpf)
    if not digitos or len(digitos) > 11:
        return ""
    digitos = digitos.zfill(11)
    return digitos if cpf_valido(digitos) else ""


def normalizar_email(email: str | None) -> str:
    texto = str(email or "").strip().lower()
    return texto if REGEX_EMAIL.match(texto) else ""


def normalizar_telefone(telefone: str | None) -> str:
    """Devolve DDD + número (10 ou 11 dígitos), ou "" se não der para aproveitar.

    Regras:
    * remove o código do país (+55) e o zero de operadora na frente do DDD;
    * celulares antigos com 8 dígitos ganham o 9 na frente (padrão desde 2016).
    """
    digitos = somente_digitos(telefone)
    if len(digitos) in (12, 13) and digitos.startswith("55"):
        digitos = digitos[2:]
    if len(digitos) in (11, 12) and digitos.startswith("0"):
        digitos = digitos[1:]
    if len(digitos) == 10 and digitos[2] in "6789":  # celular sem o nono dígito
        digitos = digitos[:2] + "9" + digitos[2:]
    if len(digitos) not in (10, 11) or digitos.startswith("0"):
        return ""
    return digitos


def normalizar_data(valor: str | None) -> str:
    """Aceita "31/12/1990", "1990-12-31" ou "31-12-1990" e devolve "1990-12-31"."""
    texto = str(valor or "").strip()
    for formato in ("%d/%m/%Y", "%Y-%m-%d", "%d-%m-%Y", "%d/%m/%y"):
        try:
            data = datetime.strptime(texto, formato).date()
        except ValueError:
            continue
        if date(1900, 1, 1) <= data <= date.today():
            return data.isoformat()
    return ""
