"""Agrupamento dos pares duplicados com Union-Find.

Se A é duplicata de B, e B é duplicata de C, então A, B e C são a mesma
pessoa, mesmo que A e C nunca tenham sido comparados diretamente.

O Union-Find (ou "conjuntos disjuntos") resolve isso de forma eficiente:
cada registro aponta para um "representante" do seu grupo, e unir dois
grupos é só fazer um representante apontar para o outro.
"""

from __future__ import annotations


class UnionFind:
    def __init__(self, cpfs: list[str]):
        self.pai = list(range(len(cpfs)))  # no começo, cada um é o próprio representante
        # CPF conhecido de cada grupo ("" = nenhum), guardado no representante.
        self.cpf = list(cpfs)

    def encontrar(self, x: int) -> int:
        """Acha o representante do grupo de x."""
        raiz = x
        while self.pai[raiz] != raiz:
            raiz = self.pai[raiz]
        # Compressão de caminho: todos no caminho passam a apontar direto
        # para a raiz, deixando as próximas buscas mais rápidas.
        while self.pai[x] != raiz:
            self.pai[x], x = raiz, self.pai[x]
        return raiz

    def unir(self, a: int, b: int) -> bool:
        """Une os grupos de a e b. Devolve False se a união foi recusada."""
        raiz_a, raiz_b = self.encontrar(a), self.encontrar(b)
        if raiz_a == raiz_b:
            return True
        cpf_a, cpf_b = self.cpf[raiz_a], self.cpf[raiz_b]
        # Nunca junta dois grupos com CPFs diferentes. Isso evita que um registro
        # sem CPF sirva de "ponte" entre duas pessoas diferentes.
        if cpf_a and cpf_b and cpf_a != cpf_b:
            return False
        # O menor índice vira o representante, para o resultado ser previsível.
        menor, maior = sorted((raiz_a, raiz_b))
        self.pai[maior] = menor
        self.cpf[menor] = cpf_a or cpf_b
        return True


def agrupar(cpfs: list[str], pares: list[tuple[int, int]]) -> list[int]:
    """Devolve, para cada posição, a posição do representante do seu grupo.

    `pares` deve vir do mais forte para o mais fraco: assim, em caso de
    conflito de CPF, prevalecem as ligações mais confiáveis.
    """
    grupos = UnionFind(cpfs)
    for a, b in pares:
        grupos.unir(a, b)
    return [grupos.encontrar(i) for i in range(len(cpfs))]
