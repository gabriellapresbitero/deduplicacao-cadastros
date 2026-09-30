"""Perfil de qualidade do cadastro: o quanto de cada campo está preenchido e válido."""

from __future__ import annotations

import pandas as pd

# coluna original -> coluna normalizada (vazia quando o valor é inválido)
CAMPOS = {
    "nome": "nome_norm",
    "cpf": "cpf",
    "email": "email",
    "telefone": "telefone",
    "data_nascimento": "nascimento",
}


def perfil(original: pd.DataFrame, normalizado: pd.DataFrame) -> pd.DataFrame:
    """Para cada campo: % preenchido, % válido e quantos estão preenchidos mas inválidos."""
    linhas = []
    total = len(original)
    for coluna, coluna_norm in CAMPOS.items():
        if coluna in original.columns:
            preenchidos = original[coluna].fillna("").astype(str).str.strip().ne("").sum()
        else:
            preenchidos = 0
        validos = normalizado[coluna_norm].ne("").sum()
        linhas.append({
            "campo": coluna,
            "preenchidos_pct": round(100 * preenchidos / total, 1) if total else 0.0,
            "validos_pct": round(100 * validos / total, 1) if total else 0.0,
            "invalidos": int(preenchidos - validos),
        })
    return pd.DataFrame(linhas)
