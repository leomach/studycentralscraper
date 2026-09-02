#!/usr/bin/env python3
"""Extrai {numero: letra} de um PDF de gabarito no formato de tabela FGV/IBFC
(uma página ou seção por cargo/especialidade, linhas de números seguidas de
linhas de letras, em blocos de até 20).

Uso:
    python3 gabarito_parser.py gabarito.pdf --match "Segurança da Informação"
    python3 gabarito_parser.py gabarito.pdf --page 11
"""

from __future__ import annotations

import argparse
import json
import re
import sys

import pdfplumber

NUM_ROW_RE = re.compile(r"^(\d{1,3}(?:\s+\d{1,3}){0,19})\s*$", re.MULTILINE)
LETTER_ROW_RE = re.compile(r"^([A-E*](?:\s+[A-E*]){0,19})\s*$", re.MULTILINE)


def parse_gabarito_text(text: str) -> dict[str, str]:
    """Varre o texto linha a linha: toda linha que é só números vira a régua
    de posições; a linha seguinte que é só letras/asterisco (anulada) mapeia
    posição -> letra. Robusto a blocos de tamanho variável (10, 20...)."""
    lines = text.splitlines()
    result: dict[str, str] = {}
    pending_numbers: list[str] | None = None
    for line in lines:
        stripped = line.strip()
        if NUM_ROW_RE.match(stripped) and " " in stripped:
            pending_numbers = stripped.split()
            continue
        if pending_numbers and LETTER_ROW_RE.match(stripped) and " " in stripped:
            letters = stripped.split()
            if len(letters) == len(pending_numbers):
                for n, l in zip(pending_numbers, letters):
                    result[n] = l  # "*" fica como está — sinaliza anulada
            pending_numbers = None
    return result


def find_page(pdf_path: str, match: str) -> int:
    with pdfplumber.open(pdf_path) as pdf:
        for i, page in enumerate(pdf.pages):
            text = page.extract_text() or ""
            if match.lower() in text.lower():
                return i
    raise SystemExit(f'nenhuma página contém "{match}"')


def extract_gabarito(pdf_path: str, page_index: int) -> dict[str, str]:
    with pdfplumber.open(pdf_path) as pdf:
        text = pdf.pages[page_index].extract_text() or ""
    return parse_gabarito_text(text)


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf_path")
    ap.add_argument("--match", help="substring do título do cargo/especialidade a procurar")
    ap.add_argument("--page", type=int, help="página (1-based) direto, se já souber")
    args = ap.parse_args()

    if args.page:
        idx = args.page - 1
    elif args.match:
        idx = find_page(args.pdf_path, args.match)
        print(f"achei na página {idx + 1}", file=sys.stderr)
    else:
        raise SystemExit("use --match ou --page")

    gabarito = extract_gabarito(args.pdf_path, idx)
    print(json.dumps(gabarito, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
