"""Mede a qualidade da deduplicação quando existe um gabarito.

Olhamos para PARES de registros:
* precisão: dos pares que o sistema juntou, quantos eram mesmo a mesma pessoa?
  (precisão baixa = juntou pessoas diferentes, o erro mais grave num cadastro)
* recall: dos pares que eram a mesma pessoa, quantos o sistema encontrou?
  (recall baixo = deixou duplicatas para trás)
* F1: média harmônica das duas.
"""

from __future__ import annotations

import pandas as pd


def _pares(tamanhos: pd.Series) -> int:
    """Um grupo com n registros tem n × (n − 1) / 2 pares."""
    return int((tamanhos * (tamanhos - 1) // 2).sum())


def avaliar(gabarito: pd.Series, grupos: pd.Series) -> dict:
    """`gabarito` e `grupos` são alinhados: a posição i dos dois é o mesmo registro."""
    tabela = pd.DataFrame({"real": gabarito.to_numpy(), "previsto": grupos.to_numpy()})
    pares_reais = _pares(tabela.groupby("real").size())
    pares_previstos = _pares(tabela.groupby("previsto").size())
    acertos = _pares(tabela.groupby(["real", "previsto"]).size())

    precisao = acertos / pares_previstos if pares_previstos else 1.0
    recall = acertos / pares_reais if pares_reais else 1.0
    f1 = 2 * precisao * recall / (precisao + recall) if (precisao + recall) else 0.0
    return {
        "pares_reais": pares_reais,
        "pares_previstos": pares_previstos,
        "acertos": acertos,
        "precisao": round(precisao, 4),
        "recall": round(recall, 4),
        "f1": round(f1, 4),
    }
