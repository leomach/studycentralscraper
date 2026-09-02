# Concursos-alvo (TI, Tribunais/Judiciário) — verificação da pesquisa

> Este documento audita `pesquisa.txt` (relatório de IA sobre oportunidades de
> concurso) contra fontes reais (sites oficiais dos órgãos, editais publicados
> em PDF, notícias de portais de concurso) e traduz o que sobrou de concreto
> em dados prontos para o scraper: banca, cargo, estrutura de prova e eixos
> temáticos (conteúdo programático) — a hierarquia que alimenta `subjects` no
> banco do studycentralback.

## Atualização 2: escopo ampliado — não só TI, não só tribunais (6 concursos, 649 questões)

A pedido explícito do usuário, o escopo deixou de ser "só TI, só Tribunal" e
passou a cobrir qualquer área presente nas provas (Português, Direito
Constitucional/Administrativo/Penal/Trabalho, Raciocínio Lógico, Estatística,
Informática Básica, Direito Aduaneiro/Tributário) e qualquer tipo de órgão
(Receita Federal, Senado Federal, Ministério Público, não só Judiciário).
Estado atual do banco (verificado direto no Postgres):

```
questions: 649
```
```
FGV   TJ-AP                       208  (Segurança da Informação, Telecom, Banco de
                                         Dados, Desenvolvimento de Sistemas, Técnico
                                         em Informática — 5 cadernos do mesmo concurso)
FGV   Senado Federal              152  (10 cargos: Administração, Arquivologia,
                                         Assistência Social, Contabilidade, Enfermagem,
                                         Eng. Eletrônica/Telecom, Eng. do Trabalho,
                                         Processo Legislativo, TI-Análise, TI-Suporte)
FGV   Receita Federal do Brasil   100  (Analista Tributário, Auditor Fiscal —
                                         Direito Aduaneiro/Tributário/Processo Fiscal)
FGV   MP-SP                        83  (Analista de Promotoria, Oficial de Promotoria)
FGV   TRT-24 Região                58  (Técnico Judiciário — TI + Gerais)
IBFC  TRF-5 Região                 48  (Técnico Judiciário — TI)
```

Por eixo-pai: Conhecimentos Gerais 287, TI - Analista de Sistemas/Programador
287, Área Fiscal e Tributária 75.

**Pipeline evoluiu bastante nesta rodada** (`scrapers/pdf_prova_parser.py`,
`scrapers/classify_eixo.py`, `scrapers/build_csv.py`):
- Texto-base compartilhado de Português ("Texto I."/"Texto II." e também a
  variante "Atenção: o texto a seguir refere-se às N próximas questões",
  achada numa prova do MP-SP) agora é detectado e anexado automaticamente à
  questão que depende dele — sem isso, Português inteiro tinha que ficar de
  fora (era a limitação documentada na Atualização 1).
- Cabeçalho de seção ("Conhecimentos Específicos", "Raciocínio Lógico
  Matemático", "Atualidades"...) parava de contaminar a última alternativa
  da questão anterior — corrigido tratando esses cabeçalhos como fronteira
  própria, não como texto de questão.
- Números soltos de subscrito (notação de base numérica, tipo "16" logo
  abaixo de "A = 16") e linhas de código-fonte numeradas dentro do
  enunciado quebravam a numeração real das questões — corrigido validando
  que toda fronteira de questão continue a sequência 1, 2, 3... estritamente.
- `eixo-pai` deixou de ser um parâmetro fixo por chamada — agora é derivado
  automaticamente por questão (`classify_eixo.EIXO_PAI`), porque uma única
  prova de cargo genérico pode misturar folhas de Conhecimentos Gerais e de
  TI na mesma faixa de questões.
- Taxonomia de eixos cresceu de 7 para 20+ categorias: Língua Portuguesa,
  Língua Inglesa, Raciocínio Lógico, Estatística, Informática Básica,
  Direito Constitucional/Administrativo/Penal/do Trabalho, Legislação (TI)
  e Legislação do Judiciário (separadas — mesma sigla CNJ aparece nos dois
  sentidos), Direito Aduaneiro/Tributário/Processo Administrativo Fiscal/
  Escrituração Fiscal e Contábil (eixo-pai novo: "Área Fiscal e Tributária"),
  além das 7 de TI já existentes.
- Trabalho paralelizado: 3 agentes rodaram em paralelo (Receita Federal,
  MP-SP, Senado Federal), cada um baixando PDFs oficiais e gerando CSVs
  prontos — eu revisei/reconciliei os ajustes que cada um fez nos scripts
  compartilhados (checagem de regressão em todos os PDFs já validados antes
  de importar) e serializei os imports de verdade (o backend tem rate limit
  de 5 logins/15min por IP, então import não paraleliza).

### Sobre a meta de 100.000 questões — números reais desta sessão

Nesta sessão, com o pipeline já pronto (fruto da Atualização 1) e escopo
liberado para qualquer área/órgão, o rendimento real foi **~650 questões em
6 concursos**, incluindo o tempo gasto evoluindo o próprio pipeline (suporte
a texto-base compartilhado, correção de bugs de numeração, taxonomia nova).
Rodando só a parte de reuso do pipeline (sem novas correções), 3 concursos
em paralelo renderam ~335 questões em cerca de 15-20 minutos de trabalho de
agente. Extrapolando esse ritmo (otimista, assumindo que a maioria dos
próximos concursos não vai exigir ajuste novo no parser): **dezenas de
milhares de questões são alcançáveis ao longo de várias sessões
adicionais**, processando as centenas de concursos "Realizados" já
listados em `conhecimento.fgv.br/concursos` (14 páginas de índice, só nessa
banca) mais outras bancas (IBFC, FCC, CEBRASPE, VUNESP, CESGRANRIO — cada
uma exigiria seu próprio parser, já que o layout de prova varia por banca).
**100.000 continua sendo uma meta de escala muito maior que "algumas
sessões de scraping"** — é da ordem do catálogo inteiro de concorrentes
estabelecidos, construído ao longo de anos com equipe dedicada. O caminho
realista daqui pra frente é: continuar processando concursos em lotes
(cada lote de 3-5 concursos em paralelo rende na faixa de 300-500 questões
verificadas), banca por banca, sessão por sessão.

## Atualização 1: banco já populado com questões reais (2 bancas, 3 levas)

Fui atrás das provas de verdade (não só dos editais) e populei o banco de
produção, em três levas. Estado atual (verificado direto no banco):

```
bancas:      2  (IBFC, FGV)
exams:       3  (TRF-5 Região/2024, TRT-24 Região/2025, TJ-AP/2024)
questions: 182  (todas com gabarito oficial)
```

Distribuição por banca/concurso (consulta direta ao banco):
```
FGV   TJ-AP          2024   107
FGV   TRT-24 Região  2025    27
IBFC  TRF-5 Região   2024    48
```

**Leva 1 — TRF-5ª Região, Edital nº 17/2023 (IBFC)**, cargo Técnico
Judiciário — Apoio Especializado — Tecnologia da Informação. 60 questões,
gabarito pós-recurso oficial. Escolhida no lugar da prova específica do
TJ-PE (mesma banca, IBFC) porque essa não está indexada em nenhum agregador
público ainda (poucos candidatos — vagas só em Recife); cobre exatamente os
mesmos eixos técnicos. Arquivos: `fontes/trf5-ti-prova.pdf`,
`fontes/trf5-ti-gabarito-final.pdf`, `fontes/trf5-2024-ibfc-tecnico-ti.csv`.

**Leva 2 — TRT-24ª Região (MS), prova de 09/03/2025 (FGV)**, cargo Técnico
Judiciário — Apoio Especializado — Tecnologia da Informação. 60 questões,
gabarito definitivo oficial. Banca **diferente** da leva 1 de propósito —
FGV tem estilo de redação de questão bem distinto do IBFC (mais situacional,
menos "decoreba de sigla"), e treinar contra os dois deixa o usuário menos
vulnerável a "decorar o estilo de uma banca só". Arquivos:
`fontes/trt24-ti-prova.pdf`, `fontes/trt24-gabarito-definitivo.pdf`,
`fontes/trt24-2025-fgv-tecnico-ti.csv`.

Em ambas as levas, ficaram de fora: **Língua Portuguesa** (texto de apoio
compartilhado entre várias questões — ver observação abaixo) e as questões
de **Direito/legislação institucional genérica do órgão** (Regimento
Interno, Lei 8.112/1990 etc. — são sobre o órgão em si, não sobre TI, então
não servem ao eixo que este scraping está priorizando) e as **2-4 questões
anuladas** de cada prova (marcadas "*" no gabarito oficial — sem resposta
correta definida, não fazem sentido num app de estudo).

**Leva 3 — TJ-AP, prova de 2024 (FGV)**, cinco cadernos de especialidade de
um único concurso (Segurança da Informação, Telecomunicações, Banco de
Dados, Desenvolvimento de Sistemas, Técnico de Informática), todos com faixa
"Conhecimentos Específicos" em Q41-80. Construí um pipeline automatizado
(`scrapers/pdf_prova_parser.py` → `scrapers/gabarito_parser.py` →
`scrapers/build_csv.py`) que extrai e classifica por eixo sem transcrição
manual — validado por conferência linha a linha contra o conteúdo já
transcrito à mão das levas 1-2 (bateu exato, inclusive blocos de código
SQL/Python). Das 5 provas, processei 3 com sucesso de primeira (Segurança,
Telecomunicações, Banco de Dados: 111 questões brutas → 107 novas + 4
duplicadas corretamente detectadas — a mesma questão sobre a Resolução CNJ
335 aparece igual em duas provas do concurso). As outras 2 (Desenvolvimento
de Sistemas, Técnico de Informática) tiveram problemas de extração
(números de questão sumindo, contagem de alternativas errada) — ficaram de
fora desta leva, não descartadas: ver item abaixo. Arquivos:
`fontes/tjap-2024-fgv-{seguranca-informacao,telecomunicacoes,banco-dados,
desenvolvimento-sistemas,tecnico-informatica}-prova.pdf`,
`fontes/tjap-2024-fgv-gabarito-definitivo.pdf`,
`fontes/tjap-2024-fgv-analista-ti.csv`.

**Ajuste feito no `import_questions.py`**: o script nunca tinha sido
atualizado para o sistema de login que o backend passou a exigir — toda
chamada dava 401 (inclusive em `--dry-run`, que só simula a escrita, não a
leitura do catálogo). Adicionei autenticação por variável de ambiente
(`STUDYCENTRAL_EMAIL`/`STUDYCENTRAL_PASSWORD`, nunca por argumento de linha
de comando) — ver o cabeçalho do script para o uso exato. Também criei uma
conta de serviço dedicada (`scraper@studycentral.local`, plano premium) só
para rodar imports — não usa login pessoal de ninguém.

### Sobre a meta de "centenas de milhares de questões"

Pedido explícito: importar o máximo possível, mirando um volume comparável
ao de concorrentes estabelecidos (que citam a faixa de centenas de milhares
de questões). Vale registrar aqui, com números, a distância entre esse
alvo e o que este pipeline consegue entregar com integridade de dado:

- Cada questão que entra no banco precisa vir de uma prova real, com
  gabarito oficial real — é o que garante que o app está ensinando a
  resposta certa. Não há atalho de "gerar" questão sem essa base.
  Bancas que citam centenas de milhares de questões normalmente somam
  décadas de provas de milhares de concursos diferentes (todas as áreas,
  não só TI/Tribunal) e mantêm equipes dedicadas a digitação/curadoria
  continuamente — não é um número que um pipeline de scraping de nicho
  replica em uma sessão de trabalho.
  Este projeto, por instrução explícita, filtra deliberadamente para um
  escopo estreito (TI, cargo de Tribunal/MP, dois eixos gerais) — o que já
  reduz o universo disponível em ordens de grandeza frente a "todas as
  áreas de todos os concursos".
- Ritmo real observado nesta sessão: ~150-200 questões por hora de trabalho
  automatizado (uma vez com o pipeline pronto) — um concurso FGV/IBFC típico
  rende 20-110 questões utilizáveis (depois de excluir Português, direito
  institucional genérico e anuladas), e a etapa de gargalo é achar fonte
  com PDF de prova + gabarito público, não o processamento em si.
- Alvo honesto e alcançável nesta linha de trabalho: **milhares** de
  questões (não centenas de milhares) processando dezenas de concursos
  FGV/IBFC/FCC/CESPE de TI já publicados — ainda assim uma base de estudo
  sólida e sem enchimento (toda questão com gabarito oficial verificável).
  Chegar a "centenas de milhares" exigiria abrir o escopo para muito além
  de TI/Tribunal (outras áreas, outros cargos, décadas de concursos
  antigos) — uma decisão de produto, não só de scraping, que vale alinhar
  antes de investir mais tempo nessa direção.

### O que ainda falta (próxima rodada de scraping)

- **`des` e `tec` (TJ-AP, Desenvolvimento de Sistemas e Técnico de
  Informática)** falharam na extração automática — números de questão
  sumindo (50/53 em `des`, 27 em `tec`) e blocos com contagem de
  alternativas errada. Ainda não investigado a fundo; suspeita é alguma
  particularidade de layout (imagem/diagrama embutido, ou texto de
  passagem compartilhada) que atrapalha o corte por coluna. Representa
  mais ~160 questões potenciais deixadas na mesa deste mesmo concurso.
- **Língua Portuguesa** ficou de fora de propósito, em todas as levas: as
  questões dependem de um texto de apoio compartilhado entre várias
  questões, e o modelo de dados atual (`Question.statement`) não tem como
  linkar um texto a várias questões — cada uma precisaria do texto inteiro
  duplicado no enunciado. Fazer isso direito (sem duplicar errado ou cortar
  contexto) merece uma rodada própria, não uma pressa.
- **MP-AL 2026 e TRF-4 2025 (ambos FCC)** — identificados como fontes boas
  (mesmos eixos, uma terceira banca — mais variedade de estilo ainda), mas
  o portal da FCC não expõe os cadernos de prova/gabarito em link direto
  como IBFC e FGV fazem (parece exigir login no "Portal do Candidato"); não
  processados ainda. Esta é a lacuna mais importante em aberto: FCC é a
  banca que a pesquisa original aponta como mais provável de aparecer nos
  concursos-alvo reais do usuário (MP-PE, TJ-AL, TRT-6/19) — hoje o banco
  tem zero questões dessa banca. Vale tentar de novo com outra abordagem
  (ex.: achar quem já subiu o PDF em algum agregador, uma vez que a prova
  "esfrie").
- **Mais concursos FGV já identificados, PDF ainda não baixado**: TJ-RN
  2023 (`conhecimento.fgv.br/concursos/tjrn2023/02`), TJ-SE 2023
  (`tjseservidor23`), TRF-1 2024 (`trf1servidor24` — tem Técnico e
  Analista de TI), TJ-MT (`tjmtservidor`), TJ-RJ 2025 (`tjrjservidores25`).
- **A prova específica do TJ-PE (Analista de Sistemas / Programador)**
  continua sem PDF público localizado — só o conteúdo programático (via
  edital, já no corpo deste documento). Vale tentar de novo mais pra frente,
  quando mais gente já tiver feito a prova e ela aparecer nos agregadores.

## Veredito direto da sua pergunta

**Você estava certo em desconfiar.** O TJ-PE **já teve** um concurso com
cargo de TI em 2025/2026 — não é uma "oportunidade de 2027" como a pesquisa
sugere. O resultado final saiu em julho de 2026. `pesquisa.txt` erra ao tratar
TI no TJ-PE como algo futuro; na verdade é algo que **já aconteceu e cujo
cadastro de reserva ainda está válido** (2 anos a partir da homologação,
prorrogável por mais 2 — ou seja, até ~2028, podendo chegar a ~2030).

**TJ-AL, por outro lado, é o oposto do que a pesquisa afirma.** O concurso que
está de fato em preparação agora (a Portaria 922/2026 citada na pesquisa é
real) é para **Analista Judiciário — Oficial de Justiça Avaliador**, cargo
que exige diploma de **Direito**, sem nenhuma relação com TI. Não encontrei
nenhuma fonte confirmando uma trilha de Apoio Especializado/TI no próximo
edital do TJ-AL. A pesquisa apresenta isso como mais certo do que realmente é.

## Tabela: o que a pesquisa acertou, errou ou exagerou

| Órgão | Afirmação da pesquisa | Situação real (verificada) | Veredito |
|---|---|---|---|
| **TJ-PE** | TI é oportunidade futura, "2027", 115 vagas | Concurso **já ocorreu** (Edital 01/2025, IBFC): cargos de TI existiram (Analista de Sistemas, Programador), resultado final jul/2026. Não achei fonte para "115 vagas 2027" — número não bate com o edital real (82 vagas no total, entre todos os cargos) | **Desatualizada/errada** — trocar o alvo por "o cadastro de reserva já existe, acompanhar convocações" |
| **TJ-AL** | Próximo edital inclui Apoio Especializado/TI | Comissão ativa (Portaria 922/2026, confirmada) é para **Oficial de Justiça Avaliador** (exige Direito) — nenhuma fonte aponta trilha de TI | **Errada quanto ao cargo** — não é alvo de TI no momento |
| **MP-PE** | Comissão formada, 35 cargos (10 analista + 25 técnico), iminente 2027 | Confirmado: Lei 19.275/2026 (35 cargos) e Portaria PGJ 2.940/2026 (31/ago/2026) são reais. Mas fontes oficiais dizem explicitamente que **ainda não há** número de vagas por especialidade, remuneração atualizada nem data de edital definidos | **Correta na direção, otimista demais no prazo** — mais embrionário do que a pesquisa sugere |
| **MP-AL** | Edital fev/2026, provas maio/2026, FCC, 27 vagas | Confirmado em todos os pontos. Inscrições 02/02 a 19/03/2026, provas objetivas 17/05/2026 | **Correta** |
| **TRT-6 / TRT-19** | Validade expira ago/2027, banca historicamente FCC, TI presente | Confirmado: validade do TRT-19 (AL) prorrogada até agosto/2027; especialidade de TI já existe no quadro atual (salários batem: R$9.776,74 técnico / R$16.041,21 analista) | **Correta** |
| **TCE-PE / ATI-PE** | Não são alvo de curto prazo, mas balizam o "teto" de exigência | Não priorizei re-verificação linha a linha (não é candidato de estudo imediato segundo a própria pesquisa) — tratar como referência de nível, não como alvo |  |

## O concurso mais útil para o scraper agora: TJ-PE (Edital 01/2025, IBFC)

Peguei o edital oficial completo
(`https://portal.tjpe.jus.br/documents/d/portal/edital_01_2025_concurso_servidores-pdf`,
44 páginas; cópia local salva em `fontes/tjpe-edital-01-2025-ibfc.pdf` — o
site bloqueia acesso automatizado direto sem um User-Agent de navegador,
então guardei uma cópia aqui para não depender de baixar de novo). É o
material mais concreto disponível — já aconteceu, tem PDF público, e cobre
exatamente os dois cargos de TI que interessam.

### Dados gerais
- **Banca**: Instituto Brasileiro de Formação e Capacitação (IBFC)
- **Tipo**: formação de cadastro de reserva (não é vaga imediata garantida)
- **Validade**: 2 anos a partir da homologação do resultado final, prorrogável uma vez por igual período (a critério do TJPE) — resultado final saiu jul/2026, então validade previsível até ~2028, podendo ir a ~2030
- **Estrutura da prova objetiva**: 60 questões, múltipla escolha, 4 alternativas — **15 de Conhecimentos Gerais** + **45 de Conhecimentos Específicos**
- **Prova discursiva**: 1 questão de conhecimentos específicos, 20 a 30 linhas, nota mínima 6/10, critérios: Estrutura (3 pts) + Conteúdo (5 pts) + Expressão (2 pts)
- **Cargos de TI e requisitos**:
  - **Analista Judiciário — Apoio Especializado/Analista de Sistemas** (nível superior, R$ 7.634,45 inicial): diploma superior em Informática, ou em Engenharia/Física/Mecânica + pós-graduação em Informática (mín. 360h)
  - **Técnico Judiciário — Apoio Especializado/Programador de Computador** (nível médio, R$ 5.858,86 inicial): certificado de Técnico em Informática (nível médio)
  - Ambos os cargos de TI só têm vaga no polo **01-Recife** (os demais cargos/funções têm vagas em 7 polos regionais)

### Conhecimentos Gerais (comum a todos os cargos)
- **Língua Portuguesa** (17 tópicos: modalidade culta, ortografia/acentuação/pontuação, vocabulário, pronomes, concordância nominal/verbal, flexão nominal/verbal, regência, vozes do verbo, correlação de tempos/modos verbais, coordenação/subordinação, morfossintaxe, semântica, formação de palavras, compreensão/interpretação textual, linguística/literatura/estilística, redação — reconhecimento de frases corretas/incorretas, redação oficial)
- **Raciocínio Lógico** (8 tópicos: lógica proposicional, argumentação lógica, raciocínio sequencial, raciocínio lógico quantitativo, raciocínio lógico analítico, diagramas lógicos, análise combinatória, probabilidade)

### Conhecimentos Específicos — Analista Judiciário / Analista de Sistemas
1. **Metodologias de Desenvolvimento e Arquitetura de Software**: especificação de requisitos funcionais/não funcionais; BPMN; metodologias ágeis (Scrum, Kanban); metodologias de inovação (Design Thinking, Lean Startup, Open Innovation)
2. **Programação, Computação em Nuvem e Microsserviços**: POO (Java); computação em nuvem; arquitetura de microsserviços; DevOps/CI (Git, GitLab CI/CD, Jenkins); API RESTful/JSON; ecossistema Spring (Cloud, Boot, Eureka, Zuul), Map Struct, Swagger, Service Discovery, API Gateway; JPA 2.0, Hibernate 4.3+, Hibernate Envers, Flyway; mensageria (RabbitMQ, Kafka); containers (Docker), orquestração (Kubernetes, Rancher), Git; CD/CI; autenticação SSO/Single Sign-On, Keycloak, OAuth2 (RFC 6749); webhooks e APIs reversas
3. **Banco de Dados**: modelagem conceitual/lógica/física; normalização e integridade referencial; linguagens de definição/manipulação de dados; PostgreSQL, Oracle DB (PL/SQL), MySQL/MariaDB, H2, MongoDB; integração via JDBC/ODBC e ORM
4. **Ciências de Dados, BI e Analytics**: fundamentos de ciência de dados; ética/privacidade no uso de dados públicos; estatística aplicada (descritiva/inferencial, correlação, testes de hipótese); Power BI e Metabase; dashboards; storytelling com dados; Python (pandas, numpy, matplotlib, seaborn) e SQL para análise; ETL; Big Data, Data Lakes, Data Warehouses; governança/qualidade de dados
5. **Inteligência Artificial e Automação**: fundamentos de IA e IA generativa; machine learning (supervisionado, não supervisionado, por reforço; regressão, redes neurais, SVM, k-NN, clustering); avaliação de modelos (acurácia, precisão, recall, F1-score); NLP (tokenização, stemming, lematização, TF-IDF, Word2Vec, transformers); engenharia de prompt e RAG; bibliotecas (scikit-learn, TensorFlow, Keras, PyTorch, spaCy, NLTK, Hugging Face); plataformas de IA generativa (ChatGPT, Claude, Amazon Bedrock, Google Vertex, Gemini, Llhama, Ollama, Deepseek); ética/responsabilidade em IA; RPA
6. **Segurança da Informação**: tríade CIA, ISO/IEC 27001/27002, PSI; criptografia simétrica/assimétrica, AES, RSA, SHA-2, HMAC, ICP-Brasil; firewalls, IDS/IPS, VPNs, HTTPS/TLS/SSH; OWASP Top 10, SQL Injection, XSS, CSRF, DevSecOps; modelos de responsabilidade compartilhada em nuvem (IaaS/PaaS/SaaS), IAM
7. **Gestão e Governança de TIC no Setor Público**: planejamento estratégico e Plano Diretor de TIC; governança, gestão de riscos e de projetos
8. **Legislação**: Lei de Governo Digital (14.129/2021); Lei de Acesso à Informação (12.527/2011); LGPD (13.709/2018); Resoluções do CNJ (185/2013, 335/2020, 370/2021, 396/2021, 455/2022, 468/2022, 615/2022, Portarias 162/2021 e 252/2020); Resolução 395/2017 (Regimento Interno TJPE); Lei Complementar 100/2007 (Código de Organização Judiciária de PE, arts. 17-47); Lei Estadual 6.123/1968 (Regime Jurídico dos Servidores de PE); Lei 11.419/2006 (Informatização do Processo Judicial); Lei 14.133/21 (Licitações e Contratos)

### Conhecimentos Específicos — Técnico Judiciário / Programador de Computador
Mesmos eixos 1 (Desenvolvimento de Software), 2 (Banco de Dados), 3 (Ciências
de Dados/BI), 4 (IA e Automação), 5 (Segurança da Informação) do Analista de
Sistemas, com escopo um pouco mais enxuto (sem o eixo de Gestão/Governança de
TIC) — ver PDF para a lista exata linha a linha; os tópicos técnicos
(linguagens, frameworks, ferramentas) são idênticos aos do Analista.

### Como isso deveria virar `subjects` no catálogo
Sugestão de hierarquia (eixo pai → subeixos), já no formato que
`studycentralback`/`studycentralfront` esperam (`parent_id`):

```
Conhecimentos Gerais (TJ-PE)
├── Língua Portuguesa
└── Raciocínio Lógico

TI — Analista de Sistemas / Programador (TJ-PE)
├── Engenharia de Software e Metodologias Ágeis
├── Programação, Nuvem e Microsserviços
├── Banco de Dados
├── Ciência de Dados, BI e Analytics
├── Inteligência Artificial e Automação
├── Segurança da Informação
├── Governança de TIC (só Analista)
└── Legislação (LGPD, Governo Digital, CNJ, PJe)
```

## O que falta verificar antes de investir tempo de scraping em cada órgão

- **MP-PE**: ainda não há edital, nem conteúdo programático, nem número de
  vagas por área — não há nada de concreto pra raspar ainda. Acompanhar; não
  é candidato a scraper agora.
- **TJ-AL**: idem — e o cargo em preparação não é de TI. Não é candidato a
  scraper agora, a menos que surja confirmação de uma trilha de TI separada.
- **MP-AL**: já rodou (provas 17/05/2026), banca FCC — o edital publicado
  deve ter conteúdo programático completo de TI (Técnico e Analista). Não
  consegui abrir o PDF do edital nesta pesquisa (bloqueado/não localizado
  diretamente); vale a pena buscar diretamente no site da FCC
  (concursosfcc.org.br) ou portal do MP-AL para extrair o Anexo de conteúdo
  programático, no mesmo formato que fiz para o TJ-PE.
- **TRT-6 / TRT-19**: nenhum edital novo publicado ainda (só a validade do
  atual, até ago/2027). O edital anterior (o que criou o quadro atual) é a
  melhor fonte de conteúdo programático disponível hoje — vale localizar o
  PDF do último edital de cada um (FCC) para extrair os eixos de TI, já que
  a própria pesquisa aponta que a FCC tende a repetir o padrão.

## Fontes consultadas

- [Edital TJPE 01/2025 (PDF oficial, 44 páginas)](https://portal.tjpe.jus.br/documents/d/portal/edital_01_2025_concurso_servidores-pdf)
- [TJPE — divulgação da data de reaplicação de provas de Técnico Judiciário](https://portal.tjpe.jus.br/-/data-das-provas-objetiva-e-discursiva-para-o-cargo-de-t%C3%A9cnico-judici%C3%A1rio-%C3%A9-divulgada)
- [Correio Braziliense — edital TJPE 2025 (analista e técnico judiciário)](https://www.correiobraziliense.com.br/euestudante/2025/07/7194830-edital-do-concurso-tjpe-e-para-analista-e-tecnico-judiciario.html)
- [Direção Concursos — reaplicação Técnico Judiciário TJPE (Operação Chiado)](https://www.direcaoconcursos.com.br/noticias/concurso-tj-pe-reaplicacao-tecnico-judiciario-abril)
- [Estratégia Concursos — comissão TJ-AL alterada (Oficial de Justiça Avaliador)](https://www.estrategiaconcursos.com.br/blog/concurso-tj-al-2026-comissao-alterada/)
- [Folha Dirigida — TJ-AL, conheça o cargo de oficial de justiça avaliador](https://folha.qconcursos.com/n/concurso-tj-al-oficial-de-justica-2026)
- [Portal de Prefeitura — MP-PE comissão formada (Lei 19.275/2026, Portaria PGJ 2.940/2026)](https://portaldeprefeitura.com.br/oportunidades/concurso-mppe-comissao-novo-edital-tecnicos-analistas/631223/)
- [Direção Concursos — edital MP-AL 2026 publicado](https://www.direcaoconcursos.com.br/noticias/concurso-mp-al-edital-publicado-2026)
- [Estratégia Concursos — TRT-AL (19ª Região), validade prorrogada até 2027](https://www.estrategiaconcursos.com.br/blog/concurso-trt-al/)

---

*Documento gerado por análise assistida — cruza `pesquisa.txt` com fontes
públicas datadas de 2026. Refazer a verificação se este documento tiver mais
de ~2-3 meses, dado o ritmo de mudança dessas comissões.*
