#!/usr/bin/env python3
"""Parser genérico de cadernos de prova em PDF (2 colunas, questões de
múltipla escolha numeradas, alternativas (A)-(E) ou A)-E)).

Cobre o padrão comum a FGV e IBFC (os dois já usados neste projeto) — provas
de outras bancas podem ter layout diferente o bastante para precisar de
ajuste, então sempre rode com --preview antes de confiar no resultado.

Uso:
    python3 pdf_prova_parser.py prova.pdf --preview
    python3 pdf_prova_parser.py prova.pdf --gabarito gabarito.json > questoes.json

O gabarito é um dict simples {"1": "e", "2": "c", ...} — normalmente mais
fácil de montar lendo o PDF do gabarito com o Read (visão) uma vez, já que o
layout de tabela do gabarito varia mais entre bancas do que o da prova em si.
"""

from __future__ import annotations

import argparse
import json
import re
import sys

import pdfplumber

QUESTION_RE = re.compile(r"(?m)^(\d{1,3})\s*$\n(.*?)(?=^\d{1,3}\s*$\n|\Z)", re.DOTALL)
ALT_RE = re.compile(r"\(([A-E])\)\s*(.*?)(?=\s*\([A-E]\)|\Z)", re.DOTALL)

# FGV/IBFC costumam agrupar várias questões de Língua Portuguesa em torno de
# um texto-base ("Texto I.", "Texto II.") citado só uma vez, antes da
# primeira questão do grupo — sem isso capturado à parte, a questão que só
# diz "o texto acima..." fica sem contexto nenhum e vira pergunta sem
# resposta possível. EVENT_RE trata "Texto N." como um evento à parte do
# fluxo de questões (não como sobra grudada na alternativa anterior).
# Cabeçalho de seção ("Conhecimentos Específicos", "Língua Portuguesa"...)
# aparece como linha solta entre a última alternativa de uma questão e o
# número da próxima — sem tratar isso como evento à parte, ele fica colado
# no fim da alternativa E da última questão da seção anterior (mesma classe
# de bug do cabeçalho/rodapé de página, só que entre seções em vez de entre
# páginas).
SECTION_HEADER_RE = (
    r"conhecimentos\s+(b[áa]sicos|espec[íi]ficos(\s+(b[áa]sicos|avan[çc]ados))?)|"
    r"l[íi]ngua\s+portuguesa|racioc[íi]nio\s+l[óo]gico(\s+(e\s+)?matem[áa]tico)?|"
    r"matem[áa]tica|inform[áa]tica|conhecimentos\s+de\s+inform[áa]tica|"
    r"legisla[çc][ãa]o|direito\s+(constitucional|administrativo|penal|processual\w*|do\s+trabalho)|"
    r"est[áa]tistica|atualidades|no[çc][õo]es\s+de\s+direito"
)
# Além de "Texto N.", a FGV também introduz passagem compartilhada com uma
# frase tipo "Atenção: o texto a seguir refere-se às duas próximas questões."
# — vista numa prova diferente da que originou o padrão "Texto N." (MP-SP,
# Analista de Promotoria). Mesmo tratamento: linha-evento própria, texto que
# vem depois dela é o texto-base até a próxima fronteira.
PASSAGE_MARKER_RE = r"Texto\s+[IVXLCDM0-9]+\.?|Aten[çc][ãa]o:.{0,120}?refere(m)?-se.{0,80}?quest(ão|ões)\.?"
EVENT_RE = re.compile(
    r"(?im)^(?:(?P<qnum>\d{1,3})|(?P<passage>" + PASSAGE_MARKER_RE + r")|"
    r"(?P<section>" + SECTION_HEADER_RE + r"))\s*$"
)

# Só prefixamos o texto-base quando a própria questão dá o sinal explícito de
# que depende dele — evita colar contexto irrelevante em questão que já é
# autossuficiente (comum nas provas da FGV, onde cada questão cita seu
# próprio trecho entre aspas).
PASSAGE_CUE_RE = re.compile(
    r"(?i)\btexto[s]?\s+(acima|a seguir)\b|\btrecho[s]?\s+a seguir\b|"
    r"\bsegmento\s+a seguir\b|\bfragmento\s+a seguir\b|"
    r"\bno fragmento\s+(acima|a seguir)\b|"
    r"\bleia\s+o\s+(texto|trecho|segmento|fragmento)\b|"
    r"\bconforme\s+o\s+texto\b|\bsegundo\s+o\s+texto\b|"
    r"\bcom base no texto\b|\bde acordo com o texto\b|"
    r"\b(o|os|esse|nesse|no)\s+trecho\b|\ba\s+not[íi]cia\b|\ba\s+reportagem\b|"
    r"\ba\s+cr[ôo]nica\b|\ba\s+tirinha\b|\ba\s+charge\b|\bo\s+poema\b|"
    r"\bo\s+conto\b|\ba\s+f[áa]bula\b"
)


def extract_two_column_text(
    pdf_path: str,
    skip_first_page: bool = True,
    margin_top: float = 55,
    margin_bottom: float = 55,
) -> str:
    """Concatena o texto de todas as páginas, coluna esquerda antes da
    direita — sem isto, extract_text() comum intercala as duas colunas linha
    a linha e embaralha o conteúdo (testado e confirmado neste projeto).

    Recorta também uma margem de topo/rodapé: cabeçalho ("Tribunal ... FGV
    CONHECIMENTO") e rodapé ("Cargo - Especialidade - TARDE   PÁGINA n")
    repetem em toda página, e sem cortar isso a última alternativa de cada
    página acaba com o rodapé colado no final do texto (bug real, visto e
    corrigido durante o desenvolvimento deste parser). Os valores default
    (55pt) foram calibrados numa prova A4 da FGV — confira com --preview em
    provas de outras bancas/tamanhos antes de confiar cegamente."""
    chunks = []
    with pdfplumber.open(pdf_path) as pdf:
        pages = pdf.pages[1:] if skip_first_page else pdf.pages
        for page in pages:
            w, h = page.width, page.height
            top, bottom = margin_top, h - margin_bottom
            left = page.crop((0, top, w / 2, bottom)).extract_text() or ""
            right = page.crop((w / 2, top, w, bottom)).extract_text() or ""
            chunks.append(left)
            chunks.append(right)
    return "\n".join(chunks)


def parse_questions(text: str) -> list[dict]:
    """Extrai {numero, enunciado, alternativas: {A:..,B:..,...}} de cada
    bloco. Enunciado é tudo antes da primeira "(A)" — texto de cabeçalho de
    seção (ex.: "Língua Portuguesa") que sobrar no fim do bloco anterior é
    cortado junto (fica só como ruído sem alternativa nenhuma associada, ver
    validação no main()).

    Usa EVENT_RE em vez de QUESTION_RE puro para tratar marcadores "Texto N."
    como evento próprio — sem isso, o texto-base ficaria grudado no final da
    alternativa E da questão anterior (mesma classe de bug do cabeçalho de
    página) em vez de virar o contexto da(s) questão(ões) seguinte(s)."""
    events = list(EVENT_RE.finditer(text))

    # Notação de base numérica ("A = 16" seguido de um "16" solto de
    # subscrito) e listagens de código com linha numerada ("9\n" de HTML/CSS
    # exibido no enunciado) também batem no regex de "número sozinho na
    # linha" — sem filtrar isso, a questão é cortada no lugar errado e a
    # numeração real (ex.: Q50, Q53 de uma prova real deste projeto) some.
    # Fronteira de questão só é aceita se continuar a sequência 1, 2, 3...;
    # qualquer "número solto" fora de sequência vira conteúdo do bloco atual.
    filtered = []
    last_num: int | None = None
    for ev in events:
        if ev.group("qnum") is not None:
            n = int(ev.group("qnum"))
            if last_num is not None and n != last_num + 1:
                continue
            last_num = n
        filtered.append(ev)
    events = filtered

    out = []
    current_passage: str | None = None
    for i, ev in enumerate(events):
        content_start = ev.end()
        content_end = events[i + 1].start() if i + 1 < len(events) else len(text)
        content = text[content_start:content_end]

        if ev.group("passage"):
            current_passage = content.strip()
            continue
        if ev.group("section"):
            current_passage = None  # nova seção: texto-base anterior não vale mais
            continue

        num = int(ev.group("qnum"))
        body = content.strip()

        alts_match = list(ALT_RE.finditer(body))
        if not alts_match:
            continue  # bloco sem alternativa reconhecível — não é questão de múltipla escolha, ou o regex não bateu

        enunciado = body[: alts_match[0].start()].strip()
        if current_passage and PASSAGE_CUE_RE.search(enunciado[:250]):
            enunciado = f"{current_passage}\n\n{enunciado}"
        # A última alternativa da última questão do documento não tem evento
        # seguinte que a delimite, então vai até o fim bruto do texto — se
        # sobrar rodapé de fim de caderno ("Realização..." etc.) depois de
        # uma quebra dupla de linha, ele fica colado nela. Alternativa nunca
        # tem esse tipo de salto no meio de verdade, então cortar aí é seguro.
        alternativas = {
            am.group(1): re.split(r"\n{2,}", am.group(2).strip(), maxsplit=1)[0].strip().rstrip(".")
            for am in alts_match
        }

        out.append({"numero": num, "enunciado": enunciado, "alternativas": alternativas})
    return out


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("pdf_path")
    ap.add_argument("--gabarito", help="JSON {numero: letra} para anexar correct_answer")
    ap.add_argument("--preview", action="store_true", help="imprime as primeiras questões pra conferência manual")
    ap.add_argument("--keep-first-page", action="store_true", help="não pula a página de capa/instruções")
    ap.add_argument("--margin-top", type=float, default=55, help="pt a cortar do topo de cada página (cabeçalho)")
    ap.add_argument("--margin-bottom", type=float, default=55, help="pt a cortar do rodapé de cada página")
    args = ap.parse_args()

    text = extract_two_column_text(
        args.pdf_path,
        skip_first_page=not args.keep_first_page,
        margin_top=args.margin_top,
        margin_bottom=args.margin_bottom,
    )
    questions = parse_questions(text)

    gabarito = {}
    if args.gabarito:
        with open(args.gabarito, encoding="utf-8") as f:
            gabarito = json.load(f)
        for q in questions:
            letra = gabarito.get(str(q["numero"]))
            q["gabarito"] = letra.lower() if letra else None

    if args.preview:
        for q in questions[:8]:
            print(f"--- Q{q['numero']} (gabarito: {q.get('gabarito', '?')}) ---")
            print(q["enunciado"][:200])
            for k, v in q["alternativas"].items():
                print(f"  {k}) {v[:100]}")
        print(f"\n{len(questions)} questões reconhecidas no total.", file=sys.stderr)
        incompletas = [q["numero"] for q in questions if len(q["alternativas"]) != 5]
        if incompletas:
            print(f"AVISO: questões com != 5 alternativas: {incompletas}", file=sys.stderr)
        return

    print(json.dumps(questions, ensure_ascii=False, indent=2))


if __name__ == "__main__":
    main()
