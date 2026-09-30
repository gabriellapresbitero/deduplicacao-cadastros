"""Gerador de uma base de clientes FICTÍCIA com duplicatas, para testar o projeto.

Cada pessoa inventada recebe de 1 a 3 cadastros com os problemas que aparecem
em bases reais: erros de digitação, nome sem o do meio, CPF com ou sem
máscara, telefone antigo sem o 9, campos vazios...

A coluna `entidade` diz quais cadastros são a mesma pessoa (o "gabarito").
Com ela, dá para medir a precisão e o recall da deduplicação.

Também são criadas duas "armadilhas" comuns:
* homônimos: pessoas diferentes com o mesmo nome;
* pai e filho (Júnior): mesmo nome e mesmo telefone de casa, nascimentos diferentes.
"""

from __future__ import annotations

import random
import unicodedata
from datetime import date, timedelta

import pandas as pd

PRIMEIROS = ["Maria", "José", "Ana", "João", "Antônio", "Francisca", "Carlos", "Paulo", "Adriana",
             "Lucas", "Juliana", "Marcos", "Luiz", "Fernanda", "Gabriel", "Patrícia", "Rafael",
             "Aline", "Pedro", "Camila", "Severino", "Josefa", "Mateus", "Beatriz", "Thiago",
             "Larissa", "Rodrigo", "Vanessa", "Bruno", "Letícia", "Felipe", "Amanda", "Diego",
             "Jéssica", "Gustavo", "Priscila", "Leonardo", "Renata", "Vinícius", "Tatiane"]
MEIOS = ["Clara", "Eduarda", "Luiza", "Vitória", "Henrique", "Augusto", "Cristina", "Aparecida",
         "Roberto", "Miguel", "Helena", "Gabriela"]
SOBRENOMES = ["Silva", "Santos", "Oliveira", "Souza", "Lima", "Pereira", "Ferreira", "Costa",
              "Rodrigues", "Almeida", "Nascimento", "Alves", "Carvalho", "Araújo", "Ribeiro",
              "Cavalcanti", "Barbosa", "Albuquerque", "Melo", "Gomes", "Monteiro", "Freitas"]
PARTICULAS = ["da", "de", "dos", "do"]
CIDADES = ["Recife", "Olinda", "Jaboatão dos Guararapes", "Paulista", "Camaragibe", "Caruaru",
           "Petrolina", "Cabo de Santo Agostinho"]
DOMINIOS = ["gmail.com", "hotmail.com", "outlook.com", "yahoo.com.br"]


def _sem_acento(texto: str) -> str:
    return "".join(c for c in unicodedata.normalize("NFKD", texto) if not unicodedata.combining(c))


def _cpf(rng: random.Random) -> str:
    numeros = [rng.randint(0, 9) for _ in range(9)]
    for tamanho in (9, 10):
        soma = sum(n * p for n, p in zip(numeros, range(tamanho + 1, 1, -1)))
        numeros.append((soma * 10) % 11 % 10)
    return "".join(map(str, numeros))


def _nome(rng: random.Random) -> str:
    partes = [rng.choice(PRIMEIROS)]
    if rng.random() < 0.5:
        partes.append(rng.choice(MEIOS))
    if rng.random() < 0.4:
        partes.append(rng.choice(PARTICULAS))
    partes += rng.sample(SOBRENOMES, rng.choice([1, 2]))
    return " ".join(partes)


def _pessoa(rng: random.Random, nome: str | None = None) -> dict:
    nome = nome or _nome(rng)
    partes = nome.split()
    usuario = _sem_acento(f"{partes[0]}.{partes[-1]}{rng.randint(1, 999)}").lower()
    return {
        "nome": nome,
        "cpf": _cpf(rng),
        "email": f"{usuario}@{rng.choice(DOMINIOS)}",
        "telefone": f"81{rng.choice('9')}{rng.randint(8000_0000, 9999_9999)}",
        "data_nascimento": date(1950, 1, 1) + timedelta(days=rng.randint(0, 365 * 55)),
        "cidade": rng.choice(CIDADES),
    }


# ----- variações que simulam problemas de cadastro ----------------------------------

def _variar_nome(nome: str, rng: random.Random) -> str:
    palavras = nome.split()
    escolha = rng.random()
    if escolha < 0.2 and len(palavras) > 2:  # tira um nome do meio
        del palavras[rng.randint(1, len(palavras) - 2)]
    elif escolha < 0.4:  # erro de digitação: troca duas letras vizinhas
        i = rng.randrange(len(palavras))
        p = palavras[i]
        if len(p) > 3:
            k = rng.randint(1, len(p) - 2)
            palavras[i] = p[:k] + p[k + 1] + p[k] + p[k + 2:]
    elif escolha < 0.5:  # letra faltando
        i = rng.randrange(len(palavras))
        if len(palavras[i]) > 3:
            k = rng.randint(1, len(palavras[i]) - 1)
            palavras[i] = palavras[i][:k] + palavras[i][k + 1:]
    texto = " ".join(palavras)
    estilo = rng.random()
    if estilo < 0.3:
        texto = texto.upper()
    elif estilo < 0.5:
        texto = _sem_acento(texto)
    elif estilo < 0.6:
        texto = "  " + texto.lower() + " "
    return texto


def _formatar_cpf(cpf: str, rng: random.Random) -> str:
    if rng.random() < 0.4:
        return ""
    if rng.random() < 0.03:  # erro de digitação: um dígito trocado (CPF fica inválido)
        k = rng.randrange(11)
        return cpf[:k] + str((int(cpf[k]) + 1) % 10) + cpf[k + 1:]
    escolha = rng.random()
    if escolha < 0.4:
        return f"{cpf[:3]}.{cpf[3:6]}.{cpf[6:9]}-{cpf[9:]}"
    if escolha < 0.5:
        return cpf.lstrip("0")  # planilha que "comeu" o zero à esquerda
    return cpf


def _formatar_telefone(telefone: str, rng: random.Random) -> str:
    if rng.random() < 0.2:
        return ""
    ddd, numero = telefone[:2], telefone[2:]
    escolha = rng.random()
    if escolha < 0.25:
        return f"({ddd}) {numero[1:5]}-{numero[5:]}"  # formato antigo, sem o 9
    if escolha < 0.5:
        return f"+55 {ddd} {numero[:5]}-{numero[5:]}"
    if escolha < 0.75:
        return f"({ddd}) {numero[:5]}-{numero[5:]}"
    return telefone


def _formatar_email(email: str, rng: random.Random) -> str:
    if rng.random() < 0.3:
        return ""
    escolha = rng.random()
    if escolha < 0.03:
        return email.replace("@", "")  # e-mail inválido, sem @
    if escolha < 0.2:
        return email.upper()
    return email


def _formatar_data(data: date, rng: random.Random) -> str:
    if rng.random() < 0.2:
        return ""
    return data.strftime("%d/%m/%Y") if rng.random() < 0.6 else data.isoformat()


def _registro(pessoa: dict, entidade: int, rng: random.Random, original: bool) -> dict:
    return {
        "nome": pessoa["nome"] if original else _variar_nome(pessoa["nome"], rng),
        "cpf": _formatar_cpf(pessoa["cpf"], rng),
        "email": _formatar_email(pessoa["email"], rng),
        "telefone": _formatar_telefone(pessoa["telefone"], rng),
        "data_nascimento": _formatar_data(pessoa["data_nascimento"], rng),
        "cidade": pessoa["cidade"] if rng.random() < 0.8 else pessoa["cidade"].upper(),
        "atualizado_em": (date(2019, 1, 1) + timedelta(days=rng.randint(0, 2400))).isoformat(),
        "entidade": entidade,
    }


def gerar_base(pessoas: int = 500, semente: int = 42) -> pd.DataFrame:
    rng = random.Random(semente)
    registros = []
    entidade = 0
    for _ in range(pessoas):
        pessoa = _pessoa(rng)
        entidade += 1
        copias = rng.choices([1, 2, 3], weights=[60, 28, 12])[0]
        registros += [_registro(pessoa, entidade, rng, original=(k == 0)) for k in range(copias)]

        armadilha = rng.random()
        if armadilha < 0.03:  # homônimo: outra pessoa com o mesmo nome
            outra = _pessoa(rng, nome=pessoa["nome"])
            entidade += 1
            registros.append(_registro(outra, entidade, rng, original=True))
        elif armadilha < 0.05:  # pai e filho Júnior: mesmo nome e telefone, sem CPF
            filho = {**_pessoa(rng, nome=pessoa["nome"]), "telefone": pessoa["telefone"],
                     "data_nascimento": pessoa["data_nascimento"] + timedelta(days=365 * 25)}
            entidade += 1
            registro = _registro(filho, entidade, rng, original=True)
            registro["cpf"] = ""
            registros.append(registro)

    base = pd.DataFrame(registros).sample(frac=1, random_state=semente).reset_index(drop=True)
    base.insert(0, "id", range(1, len(base) + 1))
    return base
