# Central de Estudos — Scraper

Projeto irmão de `studycentralback` e `studycentralfront`, e independente dos
dois: só fala com o backend pela API pública dele (`GET`/`POST` em
`/api/...`), nunca importa código Go nem toca o banco direto. Mudança aqui
nunca exige mudança lá, e vice-versa.

Responsabilidade: extrair questões de provas de fontes externas e importá-las
para a Central de Estudos.

## Fluxo

1. **(a construir)** Um scraper raspa uma fonte — site, PDF, o que for — e
   gera um CSV estruturado: uma linha por questão, já separada por eixo
   temático, banca e concurso. Cada scraper de fonte nova vive em
   `scrapers/`.
2. **Revisão humana do CSV.** Dado raspado erra — OCR errado, alternativa
   cortada, gabarito trocado — e revisar um arquivo antes de importar é bem
   mais barato do que corrigir 300 questões já dentro do banco de produção.
3. **`import_questions.py`** lê o CSV revisado e povoa `studycentralback` via
   HTTP: cria eixo temático, banca e concurso automaticamente na primeira vez
   que o nome aparece, e pergunta antes de criar um quase-duplicado (erro de
   digitação, ver seção abaixo).

## Estrutura

```
studycentralscraper/
├── import_questions.py   # passo 3: CSV -> API do studycentralback
├── sample.csv             # formato de exemplo, usado nos testes do importer
├── requirements.txt
└── scrapers/              # passo 1, um módulo por fonte (nenhum ainda)
```

## Formato do CSV que o importer espera

Ver `sample.csv` para um exemplo completo. Colunas:

| Coluna | Obrigatória | Formato |
| --- | --- | --- |
| `banca` | sim | nome (ex.: `Cebraspe`) |
| `concurso` | sim | nome (ex.: `SEFAZ-PE`) |
| `ano` | sim | inteiro (ex.: `2025`) |
| `eixo` | sim | caminho hierárquico separado por `>` (ex.: `Direito > Direito Tributário > Impostos Estaduais`) |
| `formato` | sim | `certo_errado` ou `multipla_escolha` |
| `enunciado` | sim | texto |
| `alternativa_a`..`alternativa_e` | só para `multipla_escolha` | texto; deixe vazio o que não existir |
| `gabarito` | sim | `certo`/`errado` (certo_errado) ou a letra da alternativa correta (multipla_escolha) |

Cada scraper novo em `scrapers/` deve gerar um CSV nesse formato — é o
contrato entre o passo 1 e o passo 3, então qualquer fonte nova encaixa sem
mudar o importer.

## Uso do importer

```sh
pip install -r requirements.txt

# sempre rode com --dry-run primeiro para ver o que seria criado, sem gravar nada
python3 import_questions.py meu_arquivo.csv --dry-run

# depois de conferir, roda de verdade
python3 import_questions.py meu_arquivo.csv

# backend em outro host/porta
python3 import_questions.py meu_arquivo.csv --base-url http://localhost:8080

# não parar na primeira linha com erro — importa o resto e reporta tudo ao final
python3 import_questions.py meu_arquivo.csv --continue-on-error
```

## Prevenção de nomes quase iguais (erro de digitação)

Antes de criar uma banca, concurso ou eixo novo, o script compara o nome
contra o catálogo já existente no backend:

1. **Igual após normalizar** (sem acento, minúsculo, espaços colapsados) →
   reaproveita direto, sem perguntar. `"Tributário"` e `"tributario"` são o
   mesmo eixo.
2. **Parecido, mas não igual** (via `difflib`, similaridade ≥ 82%) → pergunta
   no terminal antes de decidir, porque só um humano sabe se
   `"Direito Tributario"` e `"Direito Tributário"` são a mesma coisa ou dois
   eixos diferentes de propósito.
3. **Nada parecido** → cria um registro novo.

Nomes com menos de 4 caracteres (siglas de banca como `FCC`) pulam a etapa 2:
comparação aproximada em string curta dá falso positivo com frequência maior
do que ajuda.

## O que o importer NÃO faz

- Não corrige duplicata de **questão** por similaridade — só por enunciado
  idêntico (após normalizar), para não arriscar pular uma questão diferente
  por engano. Se o texto vier levemente diferente entre duas execuções do
  mesmo CSV, ela entra de novo.
- Não apaga nem edita nada no backend — só cria o que falta.
- Não faz scraping nem OCR — isso é trabalho de cada módulo em `scrapers/`.
# studycentralscraper
