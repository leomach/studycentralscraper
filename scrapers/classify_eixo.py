#!/usr/bin/env python3
"""Classificador de eixo por palavra-chave — primeira passada automática
para lotes grandes. Não é perfeito: existe para acelerar, não para
substituir uma conferência por amostragem antes de importar (ver README).

As regras são verificadas nesta ordem; a primeira que bater vence. Ajuste a
lista conforme o vocabulário real das provas for aparecendo — cada rodada de
scraping tende a revelar um termo nono que merece entrar aqui.
"""

from __future__ import annotations

import re

## Ordem importa: a primeira categoria que bater vence. Categorias com
## vocabulário mais ESPECÍFICO/menos ambíguo vêm primeiro de propósito —
## "SQL Injection" contém "SQL" mas é Segurança, não Banco de Dados; uma
## questão sobre a Resolução CNJ 335 é Legislação mesmo citando "servidor"
## de passagem. Isso já causou classificação errada uma vez (ver histórico
## do projeto) — não reordenar sem motivo.
RULES: list[tuple[str, list[str]]] = [
    ("Direito Aduaneiro", [
        r"despacho aduaneiro", r"controle aduaneiro", r"fiscaliza[çc][ãa]o aduaneira",
        r"tr[âa]nsito aduaneiro", r"conferência aduaneira", r"declara[çc][ãa]o de importa[çc][ãa]o",
        r"\bdi\b.*(importa[çc][ãa]o)|importa[çc][ãa]o.*\bdi\b", r"\bdu-?e\b",
        r"manifesto de carga", r"gest[ãa]o coordenada de fronteira",
        r"com[ée]rcio exterior", r"miss[ãa]o das aduanas", r"regime aduaneiro",
    ]),
    ("Direito Tributário", [
        r"c[óo]digo tribut[áa]rio nacional", r"\bctn\b", r"cr[ée]dito tribut[áa]rio",
        r"obriga[çc][ãa]o tribut[áa]ria", r"d[íi]vida ativa da uni[ãa]o", r"\bdau\b",
        r"restitui[çc][ãa]o.*ressarcimento|ressarcimento.*restitui[çc][ãa]o",
        r"compensa[çc][ãa]o de cr[ée]ditos tribut[áa]rios", r"imposto sobre produtos industrializados",
        r"\bipi\b", r"benef[íi]cios fiscais", r"direito credit[óo]rio", r"sigilo fiscal",
    ]),
    ("Escrituração Fiscal e Contábil", [
        r"\besocial\b", r"efd-?contribui[çc][õo]es", r"sistema p[úu]blico de escritura[çc][ãa]o digital",
        r"\bsped\b", r"escritura[çc][ãa]o cont[áa]bil digital", r"\becd\b",
        r"escritura[çc][ãa]o fiscal cont[áa]bil", r"\becf\b", r"efd-?icms", r"efd-?reinf",
        r"\be-?financeira\b", r"documentos? fisca(l|is) do sped",
    ]),
    ("Processo Administrativo Fiscal", [
        r"processo administrativo fiscal", r"contencioso administrativo",
        r"formaliza[çc][ãa]o da exig[êe]ncia", r"lan[çc]amento do cr[ée]dito tribut[áa]rio",
        r"recurso volunt[áa]rio", r"auto de infra[çc][ãa]o e imposi[çc][ãa]o de multa",
        r"\baiim\b", r"procedimento fiscal", r"processo de consulta\b",
        # "auto de infração" sozinho é ambíguo demais (existe em trânsito,
        # meio ambiente, trabalhista...) — só conta junto de "tributário" ou
        # "fiscal" por perto (achado real: falso-positivo numa questão de
        # multa de trânsito do concurso do Senado Federal).
        r"auto de infra[çc][ãa]o\b(?=(?:(?!\n\n).){0,120}(tribut[áa]ri|fiscal))",
    ]),
    ("Informática Básica", [
        r"microsoft\s+(word|excel|powerpoint|outlook)", r"\blibreoffice\b",
        r"\b(writer|calc|impress)\b", r"planilha eletr[ôo]nica", r"placa[- ]m[ãa]e",
        r"processador\b.*(computador|caixa|in-a-box)", r"pen[- ]?drives?",
        r"mem[óo]ria\s+(usb|ram|principal)", r"dispositivos?\s+de\s+(entrada|sa[íi]da)",
        r"perif[ée]rico", r"placa\s+de\s+v[íi]deo", r"cooler(s)?\b",
        r"windows\s+1[01]\b", r"navegador\s+de\s+internet", r"correio\s+eletr[ôo]nico",
        r"anexar\s+arquivo", r"barra\s+de\s+ferramentas", r"atalho[s]?\s+de\s+teclado",
    ]),
    ("Direito do Trabalho", [
        r"dissídio", r"reclama[çc][ãa]o trabalhista", r"a[çc][ãa]o rescis[óo]ria",
        r"sociedade empres[áa]ria", r"consolida[çc][ãa]o das leis do trabalho", r"\bclt\b",
        r"justi[çc]a do trabalho", r"rescis[ãa]o (in)?direta", r"aviso pr[ée]vio",
        r"jornada de trabalho", r"horas extras?", r"v[íi]nculo empregat[íi]cio",
        r"empregad[oa]s? numa sociedade", r"acordo coletivo", r"conven[çc][ãa]o coletiva",
    ]),
    ("Raciocínio Lógico", [
        r"nega[çc][ãa]o (l[óo]gica|de)", r"proposi[çc][ãa]o l[óo]gica", r"tabela[- ]verdade",
        r"argumento (l[óo]gico|v[áa]lido)", r"pal[íi]ndromo", r"combina[çc][ãa]o\b",
        r"an[áa]lise combinat[óo]ria", r"comiss[ãa]o de (tr[êe]s|duas|quatro)",
        r"campeonato\b.*(pontos?|vitória)", r"se\s.+,\s*ent[ãa]o\b", r"conectivo l[óo]gico",
        r"diagrama[s]? l[óo]gic",
        # vocabulário geral de matemática/raciocínio quantitativo (problemas de
        # porcentagem, razão, proporção, geometria básica) — bem mais variado
        # em fraseado do que os quebra-cabeças de lógica pura acima, então a
        # rede de termos aqui é propositalmente mais ampla.
        r"regra de tr[êe]s", r"raz[ãa]o e proporcao|propor[çc][ãa]o\b",
        r"m[úu]ltiplo[s]? comum|divisor(es)? comum", r"\bmmc\b", r"\bmdc\b",
        r"tri[âa]ngulo[s]?", r"paralelep[íi]pedo", r"per[íi]metro", r"\b[áa]rea\b",
        r"\bvolume\b.*(cubo|esfera|cilindro|s[óo]lido)", r"raio medindo",
        r"n[úu]meros? inteiros? positivos?", r"dividir.{0,20}(entre|por)",
        r"capital\b.*(rendeu|aplicou|aplica[çc][ãa]o)", r"quantas\s+(pessoas|maneiras|formas)",
    ]),
    ("Estatística", [
        r"\bm[ée]dia\b.*\bmediana\b|\bmediana\b.*\bm[ée]dia\b", r"desvio padr[ãa]o",
        r"probabilidade de\b", r"bolas? (amarela|azul|verde|vermelha)", r"distribui[çc][ãa]o de frequ[êe]ncia",
        r"vari[âa]ncia\b", r"amostra(gem)? estat[íi]stica",
    ]),
    ("Direito Constitucional", [
        r"constitui[çc][ãa]o federal", r"direitos? fundamentai?s", r"controle de constitucionalidade",
        r"a[çc][ãa]o direta de inconstitucionalidade", r"\badi\b", r"\badpf\b", r"mandado de seguran[çc]a",
        r"mandado de injun[çc][ãa]o", r"habeas corpus", r"habeas data", r"separa[çc][ãa]o dos poderes",
        r"processo legislativo", r"emenda constitucional", r"clausula? p[ée]trea",
        r"organiza[çc][ãa]o do estado", r"poder judici[áa]rio\b.*(compet[êe]ncia|organiza[çc][ãa]o)",
        r"assembleia legislativa", r"controle externo", r"tribunal de contas",
        r"recurso especial", r"recurso extraordin[áa]rio", r"supremo tribunal federal",
        r"superior tribunal de justi[çc]a", r"sistem[áa]tica constitucional",
    ]),
    ("Direito Administrativo", [
        r"ato administrativo", r"administra[çc][ãa]o p[úu]blica", r"servidor(a)? p[úu]blic",
        r"provimento efetivo", r"estabilidade\b", r"processo administrativo",
        r"licita[çc][ãa]o", r"lei\s*n[ºo°]?\s*14\.133", r"lei\s*n[ºo°]?\s*8\.666",
        r"poder de pol[íi]cia", r"desapropria[çc][ãa]o", r"improbidade administrativa",
        r"lei\s*n[ºo°]?\s*8\.429", r"descentraliza[çc][ãa]o", r"autarquia", r"funda[çc][ãa]o p[úu]blica",
        r"agente p[úu]blico", r"revoga[çc][ãa]o\b.*(ato|administrativ)", r"anula[çc][ãa]o\b.*(ato|administrativ)",
        r"principio[s]? da administra[çc][ãa]o", r"discricionariedade",
        r"servidor\s+(p[úu]blico|federal|estadual|municipal)", r"\best[áa]vel\b",
        r"aposentad[oa]", r"pessoa com defici[êe]ncia\b.*cargo",
    ]),
    ("Direito Penal", [
        r"infra[çc][ãa]o penal", r"crime\b", r"pena\b", r"sentença transitada em julgado",
        r"pris[ãa]o em flagrante", r"tr[áa]fico il[íi]cito", r"c[óo]digo penal",
        r"c[óo]digo de processo penal", r"a[çc][ãa]o penal", r"inqu[ée]rito policial",
        r"reincid[êe]ncia", r"prescri[çc][ãa]o penal", r"dosimetria da pena",
        r"lei maria da penha", r"lei\s*n[ºo°]?\s*11\.340", r"viol[êe]ncia dom[ée]stica",
    ]),
    # "Resolução CNJ" sozinho é ambíguo: o CNJ regula de tudo (mediação,
    # PJe, LGPD, gestão de acervo...) — só as que citam vocabulário de TI
    # ficam em "Legislação" (eixo TI); resolução genérica do judiciário
    # (ex.: Resolução CNJ 125/2010, sobre mediação/conciliação) é
    # "Legislação do Judiciário", debaixo de Conhecimentos Gerais.
    ("Legislação", [
        r"\blgpd\b", r"lei geral de prote[çc][ãa]o de dados",
        r"resolu[çc][ãa]o.{0,60}\bcnj\b.{0,80}(tecnologia|sistema|dados|seguran[çc]a|\bpje\b|eletr[ôo]nico)",
        r"resolu[çc][ãa]o.{0,60}(tecnologia|sistema|dados|seguran[çc]a|\bpje\b|eletr[ôo]nico).{0,80}\bcnj\b",
        r"lei n[ºo°]\s*14\.133", r"lei n[ºo°]\s*13\.709",
        r"lei de acesso [àa] informa[çc][ãa]o", r"\bgoverno digital\b",
    ]),
    ("Legislação do Judiciário", [
        r"resolu[çc][ãa]o.{0,25}\bcnj\b", r"conselho nacional de justi[çc]a",
        r"meios consensuais", r"media[çc][ãa]o e concilia[çc][ãa]o",
        r"lei\s*n[ºo°]?\s*11\.419", r"processo judicial eletr[ôo]nico",
        r"c[óo]digo de organiza[çc][ãa]o judici[áa]ria", r"regimento interno.{0,20}tribunal",
    ]),
    ("Segurança da Informação", [
        r"seguran[çc]a da informa[çc][ãa]o", r"criptografia", r"autentica[çc][ãa]o",
        r"vulnerabilidade", r"malware", r"\bhash\b", r"certificado digital",
        r"\bvpn\b", r"iso\s*27\d{3}", r"firewall", r"\bransomware\b",
        r"phishing", r"\bataque\b", r"\bantiv[íi]rus\b", r"\bids\b", r"\bips\b",
        r"sql injection", r"cross-site scripting", r"\bxss\b", r"\bcsrf\b",
        r"engenharia social", r"scareware", r"continuidade de neg[óo]cios",
        r"an[áa]lise de impacto nos neg[óo]cios",
    ]),
    ("Gestão e Governança de TIC", [
        r"\bcobit\b", r"\bitil\b", r"governan[çc]a", r"\bpmbok\b",
        r"gerenciamento de projeto", r"planejamento estrat[ée]gico",
        r"\bpert\b", r"\bpeti\b", r"\bpdti\b",
    ]),
    ("Nuvem e Microsserviços", [
        r"computa[çc][ãa]o em nuvem", r"\bcloud\b", r"\biaas\b", r"\bpaas\b",
        r"\bsaas\b", r"cont[êe]iner", r"\bdocker\b", r"kubernetes",
        r"microsservi[çc]o",
    ]),
    ("Desenvolvimento e Arquitetura de Software", [
        r"\bsdlc\b", r"\buml\b", r"engenharia de requisitos", r"caso de uso",
        r"teste de software", r"\bpython\b", r"\bjava\b", r"programa[çc][ãa]o",
        r"\bhtml\b", r"\bcss\b", r"javascript", r"metodologia[s]? [áa]gil",
        r"\bscrum\b", r"\bkanban\b", r"c[óo]digo", r"algoritmo",
        r"\bjson\b", r"\bc#\b", r"\bapi\b", r"framework",
    ]),
    ("Banco de Dados", [
        r"\bsql\b", r"banco de dados", r"\bddl\b", r"\bdml\b", r"\bdcl\b",
        r"chave prim[áa]ria", r"chave estrangeira", r"normaliza[çc][ãa]o",
        r"\bjoin\b", r"tabela", r"postgresql", r"\boracle\b", r"mysql",
        r"transa[çc][ãa]o", r"\bacid\b", r"modelagem de dados", r"\bmer\b",
        r"data warehouse", r"\betl\b",
    ]),
    ("Infraestrutura e Redes", [
        r"\btcp\b", r"\budp\b", r"protocolo", r"endere[çc]o ip", r"roteador",
        r"\bswitch\b", r"\bdns\b", r"\bdhcp\b", r"sistema operacional",
        r"windows server", r"\blinux\b", r"virtualiza[çc][ãa]o", r"hypervisor",
        r"\braid\b", r"\bthread\b", r"\bprocesso\b", r"rede de computadores",
        r"wi-?fi", r"modelo osi", r"\bhttp\b",
        r"topologia", r"cabeamento", r"fibra [óo]ptica", r"multiplexador",
        r"central telef[ôo]nica", r"comuta[çc][ãa]o", r"banda[s]? de", r"backup",
        r"c[óo]pia de seguran[çc]a", r"\bnap\b", r"complemento para 2",
        r"representa[çc][ãa]o bin[áa]ria", r"organiza[çc][ãa]o de computadores",
        # "servidor" sozinho é ambíguo demais (aparece o tempo todo em sentido
        # de RH — "servidor público" — nestas provas de tribunal); só conta
        # perto de vocabulário técnico de máquina/host.
        r"servidor\s+(de\s+)?(web|dns|dhcp|ftp|banco|aplica[çc][ãa]o|arquivos)",
    ]),
]

COMPILED = [(eixo, [re.compile(p, re.IGNORECASE) for p in pats]) for eixo, pats in RULES]

# A que eixo-pai cada folha pertence — build_csv.py usa isto pra não precisar
# de um --eixo-pai fixo por chamada (uma prova de Técnico em Informática, por
# exemplo, mistura Informática Básica — Conhecimentos Gerais — com Segurança
# da Informação — TI — na mesma faixa de questões).
EIXO_PAI: dict[str, str] = {
    # Conteúdo de carreira fiscal/tributária (Receita Federal e afins) — não é
    # transferível pra qualquer concurso do jeito que Português/RLM/Direito
    # Constitucional são, então ganha eixo-pai próprio em vez de entrar em
    # Conhecimentos Gerais.
    "Direito Aduaneiro": "Área Fiscal e Tributária",
    "Direito Tributário": "Área Fiscal e Tributária",
    "Escrituração Fiscal e Contábil": "Área Fiscal e Tributária",
    "Processo Administrativo Fiscal": "Área Fiscal e Tributária",
    "Informática Básica": "Conhecimentos Gerais",
    "Direito do Trabalho": "Conhecimentos Gerais",
    "Raciocínio Lógico": "Conhecimentos Gerais",
    "Estatística": "Conhecimentos Gerais",
    "Direito Constitucional": "Conhecimentos Gerais",
    "Direito Administrativo": "Conhecimentos Gerais",
    "Direito Penal": "Conhecimentos Gerais",
    "Língua Portuguesa": "Conhecimentos Gerais",
    "Legislação do Judiciário": "Conhecimentos Gerais",
    "Legislação": "TI - Analista de Sistemas / Programador",
    "Segurança da Informação": "TI - Analista de Sistemas / Programador",
    "Gestão e Governança de TIC": "TI - Analista de Sistemas / Programador",
    "Nuvem e Microsserviços": "TI - Analista de Sistemas / Programador",
    "Desenvolvimento e Arquitetura de Software": "TI - Analista de Sistemas / Programador",
    "Banco de Dados": "TI - Analista de Sistemas / Programador",
    "Infraestrutura e Redes": "TI - Analista de Sistemas / Programador",
}


def classify(text: str) -> str | None:
    """Devolve o nome do eixo (sob 'TI - Analista de Sistemas / Programador')
    cuja primeira regra bater no texto, ou None se nada bateu — nesse caso
    fica para revisão manual, não vira uma classificação forçada errada."""
    for eixo, patterns in COMPILED:
        if any(p.search(text) for p in patterns):
            return eixo
    return None
