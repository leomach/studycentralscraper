#!/usr/bin/env python3
"""Importa questões de um CSV para a Central de Estudos, criando eixos,
bancas e concursos automaticamente conforme aparecem no arquivo.

Não é parte da API — é um cliente HTTP dela: só chama os endpoints REST que
já existem (POST /subjects, /bancas, /exams, /questions). Pensado para
alimentar o banco a partir de um CSV gerado por outro projeto (ex.: um
scraper de provas), não para rodar dentro do servidor Go.

Uso:
    python3 scripts/import_questions.py caminho/para.csv
    python3 scripts/import_questions.py caminho/para.csv --dry-run
    python3 scripts/import_questions.py caminho/para.csv --base-url http://localhost:8080

Autenticação: o backend exige login + plano premium em todas as rotas de
catálogo/questões (CLAUDE.md do backend, multi-tenancy). Passe as credenciais
por variável de ambiente — não por argumento de linha de comando, que fica
gravado no histórico do shell e visível em `ps`:

    STUDYCENTRAL_EMAIL=voce@exemplo.com STUDYCENTRAL_PASSWORD=senha \
      python3 import_questions.py caminho/para.csv

--dry-run também precisa das credenciais: só a escrita é simulada, a
leitura inicial do catálogo (pro fuzzy-match de banca/eixo/concurso) é
sempre real.

Formato do CSV — ver scripts/sample.csv e scripts/README.md para o detalhe
de cada coluna.
"""

from __future__ import annotations

import argparse
import csv
import difflib
import os
import re
import sys
import unicodedata
from dataclasses import dataclass

import requests

DEFAULT_BASE_URL = "http://localhost:8080"

# Abaixo desse score (0..1) duas strings normalizadas são consideradas
# "coisas diferentes", não "provável erro de digitação".
FUZZY_THRESHOLD = 0.82
# Nomes muito curtos (ex.: siglas de banca como "FCC") têm similaridade
# instável por difflib — abaixo disso, só aceitamos igualdade exata.
MIN_FUZZY_LEN = 4


def normalize(s: str) -> str:
    """minúsculo, sem acento, sem espaço duplicado — para comparar nomes
    ignorando a variação mais comum entre uma digitação e outra."""
    s = s.strip().lower()
    s = unicodedata.normalize("NFKD", s).encode("ascii", "ignore").decode("ascii")
    return re.sub(r"\s+", " ", s)


class ApiError(Exception):
    pass


class Client:
    """Fino sobre requests. --dry-run intercepta aqui: todo POST vira só um
    print, e devolve um id fictício para o resto do script continuar
    coerente (ex.: um concurso "criado" em dry-run pode servir de parent_id
    fictício para o próximo eixo)."""

    def __init__(self, base_url: str, dry_run: bool):
        self.base_url = base_url.rstrip("/")
        self.dry_run = dry_run
        self.session = requests.Session()
        self._dry_run_next_id = -1
        # --dry-run só simula ESCRITA (ver post() abaixo) — a leitura inicial
        # do catálogo (Catalog.__init__, mais abaixo neste arquivo) é sempre
        # de verdade, mesmo em dry-run, porque é dela que vem o "achei algo
        # parecido, é a mesma coisa?" do fuzzy match. Por isso login roda
        # sempre, não só fora de dry-run.
        self._login()

    def _login(self) -> None:
        """Troca email/senha (variáveis de ambiente) por um access token e o
        anexa a toda requisição daqui em diante. Sem isto, todo GET/POST
        deste script toma 401 — o backend exige sessão premium em
        /api/subjects, /api/bancas, /api/exams e /api/questions."""
        email = os.environ.get("STUDYCENTRAL_EMAIL")
        password = os.environ.get("STUDYCENTRAL_PASSWORD")
        if not email or not password:
            print(
                "faltam credenciais: defina STUDYCENTRAL_EMAIL e "
                "STUDYCENTRAL_PASSWORD — necessárias mesmo em --dry-run, "
                "que só simula a escrita, não a leitura do catálogo.",
                file=sys.stderr,
            )
            sys.exit(1)
        r = self.session.post(
            f"{self.base_url}/api/auth/login",
            json={"email": email, "password": password},
            timeout=10,
        )
        if not r.ok:
            try:
                detail = r.json().get("error", r.text)
            except ValueError:
                detail = r.text
            print(f"login falhou: {r.status_code}: {detail}", file=sys.stderr)
            sys.exit(1)
        access_token = r.json()["access_token"]
        self.session.headers.update({"Authorization": f"Bearer {access_token}"})

    def get(self, path: str, params: dict | None = None):
        r = self.session.get(f"{self.base_url}{path}", params=params, timeout=10)
        r.raise_for_status()
        return r.json()

    def post(self, path: str, payload: dict):
        if self.dry_run:
            print(f"    [dry-run] POST {path} {payload}")
            fake = {"id": self._dry_run_next_id, **payload}
            self._dry_run_next_id -= 1
            return fake

        r = self.session.post(f"{self.base_url}{path}", json=payload, timeout=10)
        if not r.ok:
            try:
                body = r.json()
                detail = body.get("error", body)
            except ValueError:
                detail = r.text
            raise ApiError(f"{path} -> {r.status_code}: {detail}")
        return r.json()


def ask_confirm(question: str) -> bool:
    while True:
        resp = input(f"{question} [S/n] ").strip().lower()
        if resp in ("", "s", "sim", "y", "yes"):
            return True
        if resp in ("n", "nao", "não", "no"):
            return False


class Catalog:
    """Cache em memória do catálogo (eixos, bancas, concursos), carregado uma
    vez no início e atualizado conforme o script cria itens novos — evita uma
    consulta HTTP por linha do CSV, e é contra ESTE snapshot que o difflib
    compara nomes."""

    def __init__(self, client: Client):
        self.client = client
        self.bancas: list[dict] = client.get("/api/bancas")
        self.exams: list[dict] = client.get("/api/exams")
        self.subjects: list[dict] = client.get("/api/subjects")

    def find_or_create_banca(self, name: str) -> int:
        return self._find_or_create(
            self.bancas, name, label="banca",
            create=lambda n: self.client.post("/api/bancas", {"name": n}),
        )

    def find_or_create_exam(self, name: str, banca_id: int, year: int) -> int:
        siblings = [e for e in self.exams if e["banca_id"] == banca_id]
        return self._find_or_create(
            siblings, name, label="concurso", all_list=self.exams,
            create=lambda n: self.client.post(
                "/api/exams", {"name": n, "banca_id": banca_id, "year": year}
            ),
        )

    def find_or_create_subject_path(self, path: list[str]) -> int:
        """Anda a árvore nível a nível (ex.: "Direito > Tributário > Impostos
        Federais"), criando só o que faltar. Cada nível busca entre os
        IRMÃOS do parent atual — dois eixos com o mesmo nome sob pais
        diferentes não colidem."""
        parent_id: int | None = None
        for level_name in path:
            # parent_id some do JSON (em vez de vir null) quando é raiz — o
            # backend usa omitempty num ponteiro Go. .get() cobre os dois casos.
            siblings = [s for s in self.subjects if s.get("parent_id") == parent_id]
            parent_id = self._find_or_create(
                siblings, level_name, label="eixo", all_list=self.subjects,
                # pid=parent_id força a captura do valor NESTA iteração — sem
                # isso a lambda fecha sobre a variável, não o valor, e todo
                # nível criado apontaria para o parent_id da ÚLTIMA iteração
                # do loop (aqui não muda o resultado, já que create() sempre
                # roda antes do laço avançar, mas fica frágil e engana quem
                # ler depois).
                create=lambda n, pid=parent_id: self.client.post(
                    "/api/subjects", {"name": n, "parent_id": pid}
                ),
            )
        return parent_id  # type: ignore[return-value]

    def _find_or_create(self, candidates, name, label, create, all_list=None) -> int:
        all_list = all_list if all_list is not None else candidates
        target = normalize(name)

        # 1) igualdade exata após normalizar: resolve acento/maiúscula sem
        # perguntar nada — não é "parecido", é o mesmo nome escrito diferente.
        for c in candidates:
            if normalize(c["name"]) == target:
                return c["id"]

        # 2) parecido (difflib): pode ser erro de digitação — só o humano
        # decide se é o mesmo ou coisa nova, então pergunta.
        if len(target) >= MIN_FUZZY_LEN and candidates:
            scored = sorted(
                (
                    (difflib.SequenceMatcher(None, target, normalize(c["name"])).ratio(), c)
                    for c in candidates
                ),
                key=lambda t: t[0],
                reverse=True,
            )
            score, match = scored[0]
            if score >= FUZZY_THRESHOLD and ask_confirm(
                f'{label.capitalize()} "{name}" parece igual a "{match["name"]}" '
                f"já cadastrado (similaridade {score:.0%}). Usar o existente?"
            ):
                return match["id"]

        # 3) nada bateu (ou você disse "não" acima): cria de verdade.
        created = create(name)
        all_list.append(created)
        return created["id"]


@dataclass
class Row:
    lineno: int
    banca: str
    concurso: str
    ano: int
    eixo_path: list[str]
    formato: str
    enunciado: str
    alternativas: list[dict]
    gabarito: str


def parse_row(lineno: int, raw: dict[str, str]) -> Row:
    def required(col: str) -> str:
        v = (raw.get(col) or "").strip()
        if not v:
            raise ValueError(f'coluna "{col}" vazia')
        return v

    formato = required("formato")
    if formato not in ("certo_errado", "multipla_escolha"):
        raise ValueError(
            f"formato inválido: {formato!r} (use certo_errado ou multipla_escolha)"
        )

    alternativas: list[dict] = []
    if formato == "multipla_escolha":
        for key in "abcde":
            text = (raw.get(f"alternativa_{key}") or "").strip()
            if text:
                alternativas.append({"key": key, "text": text})
        if len(alternativas) < 2:
            raise ValueError(
                "múltipla escolha precisa de ao menos 2 alternativas preenchidas"
            )

    gabarito = required("gabarito").strip().lower()
    if formato == "certo_errado" and gabarito not in ("certo", "errado"):
        raise ValueError(f"gabarito inválido para certo_errado: {gabarito!r}")
    if formato == "multipla_escolha":
        keys = {a["key"] for a in alternativas}
        if gabarito not in keys:
            raise ValueError(
                f"gabarito {gabarito!r} não corresponde a nenhuma alternativa "
                f"preenchida ({sorted(keys)})"
            )

    # Ano tolera "2024" e "2024.0" (comum em CSV exportado de planilha).
    ano = int(float(required("ano")))

    return Row(
        lineno=lineno,
        banca=required("banca"),
        concurso=required("concurso"),
        ano=ano,
        eixo_path=[p.strip() for p in required("eixo").split(">") if p.strip()],
        formato=formato,
        enunciado=required("enunciado"),
        alternativas=alternativas,
        gabarito=gabarito,
    )


def main() -> None:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("csv_path")
    ap.add_argument("--base-url", default=DEFAULT_BASE_URL, help=f"default: {DEFAULT_BASE_URL}")
    ap.add_argument(
        "--dry-run", action="store_true",
        help="mostra o que seria feito, sem gravar nada no banco",
    )
    ap.add_argument(
        "--continue-on-error", action="store_true",
        help="não para na primeira linha com erro; reporta todas ao final",
    )
    args = ap.parse_args()

    client = Client(args.base_url, dry_run=args.dry_run)
    try:
        catalog = Catalog(client)
    except requests.RequestException as e:
        print(f"não consegui falar com o backend em {args.base_url}: {e}", file=sys.stderr)
        sys.exit(1)

    # Enunciados já existentes por eixo, carregados sob demanda — protege
    # contra reimportar o mesmo CSV duas vezes e duplicar questão.
    existing_statements: dict[int, set[str]] = {}

    def statements_for(subject_id: int) -> set[str]:
        if subject_id not in existing_statements:
            qs = client.get("/api/questions", params={"subject_id": subject_id, "limit": 1000})
            existing_statements[subject_id] = {normalize(q["statement"]) for q in qs}
        return existing_statements[subject_id]

    created = skipped = 0
    errors: list[str] = []

    with open(args.csv_path, newline="", encoding="utf-8-sig") as f:
        reader = csv.DictReader(f)
        for lineno, raw in enumerate(reader, start=2):  # linha 1 = cabeçalho
            try:
                row = parse_row(lineno, raw)
                banca_id = catalog.find_or_create_banca(row.banca)
                exam_id = catalog.find_or_create_exam(row.concurso, banca_id, row.ano)
                subject_id = catalog.find_or_create_subject_path(row.eixo_path)

                if normalize(row.enunciado) in statements_for(subject_id):
                    print(f"linha {lineno}: já existe questão igual neste eixo — pulando")
                    skipped += 1
                    continue

                client.post(
                    "/api/questions",
                    {
                        "subject_id": subject_id,
                        "banca_id": banca_id,
                        "exam_id": exam_id,
                        "format": row.formato,
                        "statement": row.enunciado,
                        "alternatives": row.alternativas,
                        "correct_answer": row.gabarito,
                    },
                )
                statements_for(subject_id).add(normalize(row.enunciado))
                created += 1
                print(f"linha {lineno}: ok")

            except (ValueError, ApiError, requests.RequestException) as e:
                msg = f"linha {lineno}: {e}"
                print(f"ERRO {msg}", file=sys.stderr)
                if not args.continue_on_error:
                    print(
                        "\nParando na primeira falha. Use --continue-on-error "
                        "para importar o resto e reportar tudo ao final.",
                        file=sys.stderr,
                    )
                    sys.exit(1)
                errors.append(msg)

    print(f"\n{created} criadas, {skipped} puladas (duplicadas), {len(errors)} com erro.")
    if errors:
        print("\n".join(errors), file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
