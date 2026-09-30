"""Linha de comando.

Uso:
    # gera uma base fictícia para testar
    python -m deduplicacao --gerar-exemplo dados/clientes_exemplo.csv

    # deduplica um CSV
    python -m deduplicacao dados/clientes_exemplo.csv --saida saida
"""

from __future__ import annotations

import argparse
import sys
import time
from pathlib import Path

import pandas as pd

from . import exemplo, qualidade
from .avaliacao import avaliar
from .pipeline import deduplicar, normalizar


def ler_argumentos(argv: list[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(prog="deduplicacao", description="Encontra e unifica cadastros duplicados.")
    parser.add_argument("arquivo", nargs="?", type=Path, help="CSV com os cadastros.")
    parser.add_argument("--saida", type=Path, default=Path("saida"), help="Pasta dos resultados.")
    parser.add_argument("--limiar", type=float, default=0.75,
                        help="Pontuação mínima para juntar dois cadastros automaticamente. Padrão: 0.75")
    parser.add_argument("--limiar-revisao", type=float, default=0.6,
                        help="Pontuação mínima para mandar um par para revisão humana. Padrão: 0.6")
    parser.add_argument("--gerar-exemplo", type=Path, metavar="CSV",
                        help="Gera uma base fictícia com duplicatas nesse caminho e sai.")
    parser.add_argument("--pessoas", type=int, default=1000, help="Pessoas na base fictícia. Padrão: 1000")
    return parser.parse_args(argv)


def ler_cadastro(caminho: Path) -> pd.DataFrame:
    # sep=None: o pandas descobre sozinho se o separador é vírgula ou ponto e vírgula.
    return pd.read_csv(caminho, sep=None, engine="python", dtype=str, keep_default_na=False, encoding="utf-8-sig")


def salvar_csv(tabela: pd.DataFrame, caminho: Path) -> None:
    tabela.to_csv(caminho, index=False, sep=";", encoding="utf-8-sig")


def br(numero: float, casas: int = 0) -> str:
    """Formata números no padrão brasileiro: 1186570 -> "1.186.570"; 0.16 -> "0,16"."""
    return f"{numero:,.{casas}f}".replace(",", "X").replace(".", ",").replace("X", ".")


def montar_relatorio(resultado, perfil: pd.DataFrame, metricas: dict | None, segundos: float) -> str:
    est = resultado.estatisticas
    reducao = 100 * resultado.pares_comparados / resultado.pares_possiveis if resultado.pares_possiveis else 0
    linhas = [
        "# Relatório de deduplicação",
        "",
        f"- Cadastros recebidos: **{br(est['registros_entrada'])}**",
        f"- Pessoas únicas: **{br(est['pessoas_unicas'])}**",
        f"- Duplicatas unificadas: **{br(est['duplicatas_removidas'])}**",
        f"- Pares para revisão humana: **{br(est['pares_para_revisao'])}**",
        f"- Comparações feitas: {br(resultado.pares_comparados)} de {br(resultado.pares_possiveis)} possíveis "
        f"({br(reducao, 2)}%, graças à blocagem)",
        f"- Tempo: {br(segundos, 1)} s",
        "",
        "## Qualidade dos campos",
        "",
        "| Campo | Preenchido | Válido | Preenchido mas inválido |",
        "|---|---:|---:|---:|",
        *[f"| {p.campo} | {br(p.preenchidos_pct, 1)}% | {br(p.validos_pct, 1)}% | {p.invalidos} |"
          for p in perfil.itertuples()],
    ]
    if metricas:
        linhas += [
            "",
            "## Avaliação (a base tem gabarito na coluna `entidade`)",
            "",
            f"- Precisão: **{br(100 * metricas['precisao'], 1)}%** (dos pares unidos, quantos estavam certos)",
            f"- Recall: **{br(100 * metricas['recall'], 1)}%** (das duplicatas reais, quantas foram encontradas)",
            f"- F1: **{br(metricas['f1'], 3)}**",
        ]
    if not resultado.revisao.empty:
        linhas += [
            "",
            "## Primeiros pares para revisão",
            "",
            "| Cadastro A | Cadastro B | Pontuação | Motivo |",
            "|---|---|---:|---|",
            *[f"| {r.id_a}: {r.nome_a} | {r.id_b}: {r.nome_b} | {r.pontuacao:.2f} | {r.motivo} |"
              for r in resultado.revisao.head(10).itertuples()],
        ]
    return "\n".join(linhas) + "\n"


def executar(args: argparse.Namespace) -> None:
    if args.gerar_exemplo:
        base = exemplo.gerar_base(args.pessoas)
        args.gerar_exemplo.parent.mkdir(parents=True, exist_ok=True)
        base.to_csv(args.gerar_exemplo, index=False)
        print(f"Base fictícia com {len(base)} cadastros de {args.pessoas} pessoas salva em {args.gerar_exemplo}")
        return
    if not args.arquivo:
        raise ValueError("Informe o CSV de entrada (ou use --gerar-exemplo).")

    cadastro = ler_cadastro(args.arquivo)
    gabarito = cadastro.pop("entidade") if "entidade" in cadastro.columns else None

    inicio = time.perf_counter()
    resultado = deduplicar(cadastro, args.limiar, args.limiar_revisao)
    segundos = time.perf_counter() - inicio

    perfil = qualidade.perfil(cadastro, normalizar(cadastro))
    metricas = None
    if gabarito is not None:
        grupos = cadastro["id"].map(dict(zip(resultado.mapa["id_original"], resultado.mapa["id_mestre"])))
        metricas = avaliar(gabarito, grupos)

    args.saida.mkdir(parents=True, exist_ok=True)
    salvar_csv(resultado.unificados, args.saida / "clientes_unificados.csv")
    salvar_csv(resultado.mapa, args.saida / "mapa_ids.csv")
    salvar_csv(resultado.revisao, args.saida / "pares_para_revisao.csv")
    salvar_csv(perfil, args.saida / "qualidade_campos.csv")
    (args.saida / "relatorio.md").write_text(montar_relatorio(resultado, perfil, metricas, segundos), encoding="utf-8")

    est = resultado.estatisticas
    print(f"{est['registros_entrada']} cadastros -> {est['pessoas_unicas']} pessoas únicas "
          f"({est['duplicatas_removidas']} duplicatas, {est['pares_para_revisao']} pares para revisão)")
    if metricas:
        print(f"Precisão {metricas['precisao']:.1%} | Recall {metricas['recall']:.1%} | F1 {metricas['f1']:.3f}")
    print(f"Resultados em: {args.saida}")


def main(argv: list[str] | None = None) -> int:
    try:
        executar(ler_argumentos(argv))
    except (ValueError, FileNotFoundError) as erro:
        print(f"Erro: {erro}", file=sys.stderr)
        return 1
    return 0


if __name__ == "__main__":
    sys.exit(main())
