# Deduplicação de Cadastros

[![Testes](https://github.com/gabriellapresbitero/deduplicacao-cadastros/actions/workflows/testes.yml/badge.svg)](https://github.com/gabriellapresbitero/deduplicacao-cadastros/actions/workflows/testes.yml)
![Python](https://img.shields.io/badge/Python-3.11+-3776AB?logo=python&logoColor=white)
![pandas](https://img.shields.io/badge/pandas-150458?logo=pandas&logoColor=white)

Encontra cadastros duplicados de clientes, mesmo com erros de digitação e formatos diferentes, e
junta cada pessoa em um único **registro mestre**.

## O problema

Toda empresa que cadastra clientes por mais de um canal (loja, site, WhatsApp, sistema antigo)
acaba com a mesma pessoa cadastrada várias vezes:

| id | nome | cpf | telefone | e-mail |
|---|---|---|---|---|
| 12 | Maria da Silva | 529.982.247-25 | (81) 8872-0211 | |
| 87 | MARIA SILVA | 52998224725 | +55 81 98872-0211 | maria@gmail.com |
| 430 | Mraia Clara Silva | | 81988720211 | MARIA@GMAIL.COM |

Isso gera custo real: a mesma pessoa recebe três cartas, o histórico de compras fica partido, as
métricas de "clientes ativos" ficam infladas e a empresa pode descumprir a LGPD ao não saber
todos os dados que tem de alguém.

## Como funciona

```
CSV  →  normalização  →  blocagem  →  pontuação dos pares  →  agrupamento (Union-Find)  →  registro mestre
```

**1. Normalização** ([`normalizacao.py`](deduplicacao/normalizacao.py)): coloca tudo no mesmo formato.
- Nome: sem acentos, maiúsculo, sem "da/de/dos" → `MARIA SILVA`
- CPF: só dígitos, **validado pelos dígitos verificadores**, e com o zero à esquerda que o Excel costuma apagar
- Telefone: tira o +55 e o 0 da operadora, e **devolve o 9** a celulares cadastrados antes de 2016
- E-mail em minúsculas e validado. Datas em vários formatos viram `AAAA-MM-DD`

**2. Blocagem** ([`blocagem.py`](deduplicacao/blocagem.py)): comparar todo mundo com todo mundo é
inviável (100 mil cadastros = ~5 bilhões de pares). Só comparo cadastros que compartilham CPF,
e-mail, telefone ou início do nome. Na base de exemplo, isso cai de **1,25 milhão** de
comparações para cerca de **2 mil** (0,17%).

**3. Pontuação** ([`similaridade.py`](deduplicacao/similaridade.py)): cada par recebe uma nota de 0 a 1.
- Mesmo CPF válido → 1,0. **CPFs diferentes → 0**, nunca juntam
- Sem CPF: nome (50%, tolerando erros de digitação com `difflib`) + e-mail (20%) + telefone (20%) + nascimento (10%)
- Datas de nascimento diferentes **tiram** pontos. Assim, pai e filho "Júnior", com o mesmo
  nome e o mesmo telefone de casa, não viram uma pessoa só

**4. Agrupamento** ([`agrupamento.py`](deduplicacao/agrupamento.py)): se A = B e B = C, então
A = B = C. Uso a estrutura **Union-Find** (com compressão de caminho). Ela também se recusa a juntar
dois grupos com CPFs diferentes, para que um cadastro sem CPF não sirva de "ponte" entre duas pessoas.

**5. Registro mestre** ([`registro_mestre.py`](deduplicacao/registro_mestre.py)): para cada campo,
vale o valor do cadastro mais recente que esteja preenchido e seja válido. Para o nome, vale o mais completo.

Pares com nota entre **0,60 e 0,75** não são juntados automaticamente: vão para
`pares_para_revisao.csv`, para uma pessoa decidir.

## Resultados

A pasta [`dados/`](dados) tem uma **base fictícia** de 1.582 cadastros de 1.000 pessoas inventadas,
gerada por [`exemplo.py`](deduplicacao/exemplo.py) com os problemas de uma base real: erros de
digitação, campos vazios, CPF sem máscara, telefone antigo e as armadilhas de homônimos e de pai e filho.
Como a base tem gabarito (coluna `entidade`), dá para medir o acerto:

| Limiar | Precisão | Recall | F1 | Pares para revisão |
|:---:|---:|---:|---:|---:|
| 0,90 | 100,0% | 53,3% | 0,696 | 253 |
| 0,80 | 100,0% | 71,7% | 0,835 | 133 |
| **0,75** (padrão) | **100,0%** | **79,2%** | **0,884** | **85** |
| 0,70 | 99,8% | 86,0% | 0,924 | 43 |
| 0,65 | 99,8% | 89,9% | 0,946 | 21 |

**Por que o padrão é 0,75 e não 0,65, que tem F1 maior?** Porque os dois erros não custam o
mesmo. Juntar duas pessoas diferentes (erro de precisão) mistura dados pessoais e histórico, e é
difícil de desfazer. Deixar uma duplicata para trás (erro de recall) só mantém o problema que já
existia. Então prefiro precisão de 100% e mando a zona cinzenta para revisão humana.

## Como rodar

Pré-requisito: Python 3.11 ou mais novo.

```bash
git clone https://github.com/gabriellapresbitero/deduplicacao-cadastros.git
cd deduplicacao-cadastros
python -m venv .venv
source .venv/bin/activate        # no Windows: .venv\Scripts\activate
pip install -r requirements.txt

# Deduplica a base de exemplo
python -m deduplicacao dados/clientes_exemplo.csv

# Com a sua base (CSV separado por , ou ;)
python -m deduplicacao meus_clientes.csv --saida resultado --limiar 0.8

# Gera outra base fictícia
python -m deduplicacao --gerar-exemplo dados/outra_base.csv --pessoas 5000
```

**Colunas do CSV:** `id` e `nome` são obrigatórias. `cpf`, `email`, `telefone`,
`data_nascimento`, `cidade` e `atualizado_em` são opcionais, e quanto mais colunas, melhor o resultado.

### Saídas

| Arquivo | Conteúdo |
|---|---|
| `clientes_unificados.csv` | Um registro mestre por pessoa, com os ids que foram unidos |
| `mapa_ids.csv` | `id_original → id_mestre`, para atualizar pedidos e outras tabelas |
| `pares_para_revisao.csv` | Pares na zona cinzenta, com a nota e o motivo |
| `qualidade_campos.csv` | % preenchido e % válido de cada campo |
| `relatorio.md` | Resumo de tudo, com precisão e recall quando há gabarito |

## Testes

```bash
python -m unittest discover -s tests -t . -v
```

Há testes para cada regra de normalização (inclusive os formatos de telefone e o zero do CPF),
para a pontuação, a blocagem e o Union-Find, e para o pipeline completo. Um teste de qualidade
roda a deduplicação numa base gerada e **falha se a precisão cair abaixo de 99% ou o recall
abaixo de 70%**. Assim, uma mudança que piore o resultado não passa despercebida.

## Estrutura

```
deduplicacao/
├── normalizacao.py     # nome, CPF, e-mail, telefone e datas
├── blocagem.py         # quais pares comparar
├── similaridade.py     # nota de cada par e o motivo
├── agrupamento.py      # Union-Find
├── registro_mestre.py  # consolidação dos campos
├── pipeline.py         # junta as etapas
├── qualidade.py        # perfil de preenchimento
├── avaliacao.py        # precisão, recall e F1
├── exemplo.py          # gerador da base fictícia
└── __main__.py         # linha de comando
dados/clientes_exemplo.csv
tests/
```

## Próximos passos

- [ ] Comparação fonética de nomes ("Thiago" x "Tiago", "Luiz" x "Luis")
- [ ] Endereço e CEP como evidência
- [ ] Tela simples para revisar os pares da zona cinzenta

---
Feito por **Gabriella Presbítero** · Licença MIT · Todos os dados de exemplo são fictícios.
