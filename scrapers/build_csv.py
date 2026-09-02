#!/usr/bin/env python3
"""Junta prova (JSON do pdf_prova_parser.py) + gabarito (JSON do
gabarito_parser.py), classifica o eixo por palavra-chave (classify_eixo.py)
e escreve linhas no formato CSV que import_questions.py espera.

Usa csv.writer (nunca concatenação de string) para o quoting sair sempre
correto — a leva anterior deste projeto quebrou 4 vezes por vírgula solta
escrita à mão; isto elimina a classe inteira de bug.

Uso:
    python3 build_csv.py prova.json gabarito.json \
        --banca FGV --concurso "TJ-AP" --ano 2024 \
        --range 41-80 --eixo-pai "TI - Analista de Sistemas / Programador" \
        >> saida.csv
"""

from __future__ import annotations

import argparse
import csv
import json
import sys

from classify_eixo import EIXO_PAI, classify


def parse_range(spec: str) -> tuple[int, int]:
    a, b = spec.split("-")
    return int(a), int(b)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("prova_json")
    ap.add_argument("gabarito_json")
    ap.add_argument("--banca", required=True)
    ap.add_argument("--concurso", required=True)
    ap.add_argument("--ano", required=True, type=int)
    ap.add_argument("--range", required=True, help="ex.: 41-80 — só questões nesse intervalo (1-based, inclusivo)")
    ap.add_argument(
        "--eixo-pai",
        default=None,
        help="fixa o eixo-pai pra todo o range — por padrão é derivado por questão via "
        "classify_eixo.EIXO_PAI (uma prova de Técnico em Informática, por exemplo, mistura "
        "folhas de Conhecimentos Gerais e de TI na mesma faixa de questões)",
    )
    ap.add_argument("--fallback-eixo", help="eixo pra quem não bateu em nenhuma regra (default: pula a questão)")
    ap.add_argument("--eixo-fixo", help="eixo-folha fixo pra todo o range, sem rodar o classificador — pra blocos que já são conhecidos de antemão pela estrutura da prova (ex.: Língua Portuguesa)")
    ap.add_argument("--header", action="store_true", help="escreve a linha de cabeçalho do CSV")
    args = ap.parse_args()

    lo, hi = parse_range(args.range)

    with open(args.prova_json, encoding="utf-8") as f:
        questions = json.load(f)
    with open(args.gabarito_json, encoding="utf-8") as f:
        gabarito = json.load(f)

    writer = csv.writer(sys.stdout)
    if args.header:
        writer.writerow([
            "banca", "concurso", "ano", "eixo", "formato", "enunciado",
            "alternativa_a", "alternativa_b", "alternativa_c", "alternativa_d", "alternativa_e",
            "gabarito",
        ])

    written = skipped_no_eixo = skipped_anulada = skipped_incompleta = 0
    for q in questions:
        n = q["numero"]
        if not (lo <= n <= hi):
            continue

        letra = gabarito.get(str(n))
        if not letra or letra == "*":
            skipped_anulada += 1
            continue

        alts = q["alternativas"]
        if len(alts) != 5 or letra.upper() not in alts:
            skipped_incompleta += 1
            print(f"AVISO: Q{n} incompleta ou gabarito fora das alternativas — pulando", file=sys.stderr)
            continue

        if args.eixo_fixo:
            eixo_folha = args.eixo_fixo
        else:
            eixo_folha = classify(q["enunciado"] + " " + " ".join(alts.values()))
        if not eixo_folha:
            if args.fallback_eixo:
                eixo_folha = args.fallback_eixo
            else:
                skipped_no_eixo += 1
                print(f"AVISO: Q{n} sem eixo reconhecido — pulando (use --fallback-eixo pra não perder): {q['enunciado'][:80]!r}", file=sys.stderr)
                continue

        eixo_pai = args.eixo_pai or EIXO_PAI.get(eixo_folha, "TI - Analista de Sistemas / Programador")
        eixo = f"{eixo_pai} > {eixo_folha}"
        writer.writerow([
            args.banca,
            args.concurso,
            args.ano,
            eixo,
            "multipla_escolha",
            q["enunciado"],
            alts.get("A", ""),
            alts.get("B", ""),
            alts.get("C", ""),
            alts.get("D", ""),
            alts.get("E", ""),
            letra.lower(),
        ])
        written += 1

    print(
        f"{written} escritas, {skipped_anulada} anuladas, "
        f"{skipped_incompleta} incompletas, {skipped_no_eixo} sem eixo reconhecido.",
        file=sys.stderr,
    )


if __name__ == "__main__":
    main()
