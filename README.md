# Observatório da Educação

[![CI](https://github.com/henriquesakita/observatorio-educacao/actions/workflows/ci.yml/badge.svg)](https://github.com/henriquesakita/observatorio-educacao/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.12-3776AB?logo=python&logoColor=white)](https://www.python.org/)
[![Streamlit](https://img.shields.io/badge/dashboard-Streamlit-FF4B4B?logo=streamlit&logoColor=white)](https://streamlit.io/)
[![License: MIT](https://img.shields.io/badge/license-MIT-0f766e.svg)](LICENSE)

Dashboard em Python que transforma as planilhas públicas do **Ideb municipal** em uma leitura navegável da educação básica brasileira. O projeto baixa os arquivos oficiais do Inep, trata os dados com pandas e apresenta séries históricas, rankings e comparações por município, etapa, rede e território.

> **5.571 municípios · 11 edições (2005–2025) · 339 mil registros tratados**
>
> Anos Iniciais e Anos Finais cobrem 2005–2025; o Ensino Médio tem recorte municipal a partir de 2017.

---

## O problema

Os resultados do Ideb são públicos, mas chegam em planilhas largas, com cabeçalhos compostos, códigos e notas de rodapé. Comparar municípios, acompanhar a evolução de uma rede ou entender a diferença entre anos exige um trabalho de limpeza que afasta quem mais precisa desses números: gestores, professores, jornalistas e pesquisadores.

Este projeto faz esse trabalho uma vez, de forma reprodutível, e entrega a análise pronta para consulta.

## O que o painel responde

- Como o Ideb evoluiu em cada região entre 2005 e 2025?
- Quais municípios têm os melhores e os menores resultados em cada edição?
- Quanto um município avançou desde a primeira edição disponível e como ele se compara à média da UF, da região e do Brasil?
- A melhora veio da **aprendizagem** (nota do Saeb) ou do **rendimento** (aprovação)?
- Quais unidades da federação lideram e quais ficaram para trás?

## Principais achados — edição 2025, rede pública

| Indicador | Anos Iniciais | Anos Finais | Ensino Médio |
| --- | ---: | ---: | ---: |
| Municípios com resultado | 5.478 | 5.491 | 5.428 |
| Ideb médio (média simples) | **6,22** | **5,12** | **4,47** |
| Variação vs edição inicial | **+2,61** (2005) | **+1,81** (2005) | **+0,90** (2017) |
| Municípios abaixo de 6,0 | 36% | 89% | 99% |
| Avançaram desde a edição inicial | 99,9% | 99,8% | 93,8% |

- **Ceará** lidera os Anos Iniciais (7,19) e os Anos Finais (5,90). No Ensino Médio, o **Paraná** aparece na frente (5,04), seguido de Espírito Santo (5,03) e Rio Grande do Sul (4,89).
- **Amapá** (4,87) e **Roraima** (3,94) têm os menores resultados médios nos Anos Iniciais e Finais. No Ensino Médio, **Roraima** (3,34) e **Amazonas** (3,43) ficam no fim da lista.
- Entre 2005 e 2025, **Ibateguara (AL)** foi o maior avanço nos Anos Iniciais (+7,8) e **Branquinha (AL)** nos Anos Finais (+6,5). No Ensino Médio, **Presidente Kennedy (ES)** lidera (+3,7 desde 2017).
- Os Anos Finais concentram o maior desafio: nove em cada dez municípios ainda ficam abaixo de 6,0. No Ensino Médio esse quadro é ainda mais crítico — **99% dos municípios** ficaram abaixo da referência em 2025.

> As médias do painel são **simples entre municípios**. O Ideb oficial do Brasil e das UFs é ponderado pelo número de alunos, então os valores servem para comparar municípios — não substituem o indicador oficial. Essa escolha está explicada na aba **Método**.

## Demo

**▶ [Abrir o painel publicado](https://observatorio-educacao.streamlit.app/)**

[![Streamlit App](https://static.streamlit.io/badges/streamlit_badge_black_white.svg)](https://observatorio-educacao.streamlit.app/)

O painel roda no Streamlit Community Cloud direto do branch `main`: qualquer push
atualiza a versão publicada.

![Dashboard do Observatório da Educação](docs/dashboard.png)

## Como rodar

```bash
git clone https://github.com/henriquesakita/observatorio-educacao.git
cd observatorio-educacao

python -m venv .venv
source .venv/bin/activate        # Windows: .venv\Scripts\activate
pip install -r requirements-dev.txt

streamlit run app.py
```

O painel abre em `http://localhost:8501`.

### Regerar os dados

O recorte tratado já está versionado em `data/processed/ideb_municipios.csv.gz`. Para baixar as planilhas originais e refazer o pipeline:

```bash
python scripts/build_dataset.py
```

O script baixa os arquivos das três etapas direto do Inep, extrai os `.xlsx`, limpa o cabeçalho composto e grava o CSV comprimido. Os arquivos brutos ficam em `data/raw/` e não são versionados.

### Testes e qualidade

```bash
pytest          # 21 testes
ruff check .    # lint
```

A CI roda lint e testes a cada push e pull request, além de validar a importação do dashboard em um ambiente limpo.

## Estrutura

```
observatorio-educacao/
├── app.py                      # entrada do Streamlit
├── src/observatorio/
│   ├── config.py               # UFs, regiões, anos e caminhos
│   ├── ingest.py               # download dos ZIPs do Inep
│   ├── transform.py            # limpeza e formato tidy
│   ├── metrics.py              # agregações e rankings
│   └── app.py                  # interface
├── scripts/build_dataset.py    # pipeline completo
├── tests/                      # transformação + métricas
├── data/processed/             # recorte tratado (6,6 MB)
└── .github/workflows/ci.yml
```

## Pipeline

```
INEP (ZIP/XLSX) → ingest.py → transform.py → CSV tidy → metrics.py → Streamlit + Plotly
```

O formato final é **longo**: uma linha por `ano × etapa × município × rede`, com Ideb, nota de Matemática, nota de Português, nota média, indicador de rendimento, taxa de aprovação e meta (quando existe). Esse desenho simplifica filtros, séries temporais e testes.

### Decisões técnicas

- **pandas + openpyxl** para ler um cabeçalho de três níveis e descartar as linhas de notas do Inep.
- **CSV comprimido versionado** para que o dashboard funcione sem depender de rede ou de uma pasta `data/raw/` de 100 MB.
- **Médias explícitas**: toda agregação é simples e rotulada como tal, evitando confundir o painel com o Ideb oficial.
- **Separação entre dados e interface**: `metrics.py` é testável sem Streamlit; a UI só orquestra.
- **Cache do Streamlit** no carregamento do CSV e nenhuma chamada externa em tempo de execução.
- **Testes de consistência**: o Ideb divulgado é comparado com `N × P` (tolerância de arredondamento) e as chaves são verificadas contra duplicidade.

## Limitações

- O Ideb combina aprovação e desempenho no Saeb; **não mede equidade, infraestrutura ou aprendizagem por aluno**.
- O Inep não divulga resultados com participantes insuficientes no Saeb ou sob solicitação de não divulgação. Por isso o número de municípios varia entre edições.
- O Ideb do **ensino médio** só tem recorte municipal a partir de **2017**; as edições anteriores trazem apenas o resultado nacional. A cobertura municipal também cai bastante em **2021** (pandemia).
- A edição de **2021** reflete a pandemia de Covid-19 e deve ser lida com cautela.
- O primeiro ciclo de metas terminou em 2021; as edições seguintes **não têm metas oficiais**.
- As planilhas municipais trazem as redes pública, estadual, municipal e federal; a rede privada não entra no recorte municipal.
- A referência de **6,0** é uma linha de leitura, não uma meta oficial do Inep.

## Próximos passos

- Ponderar as médias pelo número de alunos (Censo Escolar) para reproduzir os agregados oficiais.
- Adicionar dados escolares e um mapa coroplético por município.
- Cruzar o Ideb com indicadores socioeconômicos e de infraestrutura.
- Publicar um modelo de alerta de evasão com interpretabilidade (SHAP) como próximo projeto da trilha de dados.

## Fonte

- [INEP — Resultados do Ideb](https://www.gov.br/inep/pt-br/areas-de-atuacao/pesquisas-estatisticas-e-indicadores/ideb/resultados)
- Planilhas: `divulgacao_anos_iniciais_municipios_2025.zip`, `divulgacao_anos_finais_municipios_2025.zip` e `divulgacao_ensino_medio_municipios_2025.zip`
- Edição de referência: **Ideb 2025** (Saeb 2025 + Censo Escolar 2025)

## Sobre

Projeto de portfólio de **Henrique Sakita**, professor de Ciências e Biologia em transição para dados. Une 12 anos de sala de aula à prática de Python, SQL e estatística para transformar dados públicos em decisões educacionais.

- GitHub: [@henriquesakita](https://github.com/henriquesakita)
- LinkedIn: [henrique-sakita](https://www.linkedin.com/in/henrique-sakita/)
- Contato: [henriquesakita@gmail.com](mailto:henriquesakita@gmail.com)

## Licença

MIT — veja [LICENSE](LICENSE).
