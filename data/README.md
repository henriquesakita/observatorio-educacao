# Dados

## `processed/ideb_municipios.csv.gz`

Recorte tratado das planilhas oficiais do Ideb municipal (INEP/Saeb), edição 2025.

- **Linhas:** 338.900
- **Municípios:** 5.571
- **Edições:** 2005 a 2025 (anos ímpares)
- **Etapas:** Anos Iniciais, Anos Finais e Ensino Médio (a partir de 2017)
- **Redes:** Pública, Estadual, Municipal e Federal
- **Tamanho:** ~6,6 MB

### Colunas

| Coluna | Descrição |
| --- | --- |
| `ano` | Edição do Ideb |
| `etapa` | Anos Iniciais ou Anos Finais |
| `uf` | Sigla da unidade da federação |
| `regiao` | Região geográfica |
| `cod_municipio` | Código IBGE de 7 dígitos |
| `municipio` | Nome do município |
| `rede` | Rede de ensino |
| `ideb` | Ideb divulgado (0 a 10) |
| `taxa_aprovacao` | Taxa de aprovação da etapa (%) |
| `indicador_rendimento` | Indicador de rendimento (P) |
| `nota_matematica` | Nota padronizada de Matemática |
| `nota_portugues` | Nota padronizada de Língua Portuguesa |
| `nota_media` | Nota média padronizada (N) |
| `meta` | Meta do primeiro ciclo (2007–2021), quando pactuada |

O Ideb é o produto `nota_media × indicador_rendimento`, arredondado pelo Inep para uma casa decimal.

## `raw/`

Arquivos ZIP/XLSX originais baixados do INEP. Não são versionados: para recriá-los, rode `python scripts/build_dataset.py`.

## Fonte

- [INEP — Resultados do Ideb](https://www.gov.br/inep/pt-br/areas-de-atuacao/pesquisas-estatisticas-e-indicadores/ideb/resultados)
- `divulgacao_anos_iniciais_municipios_2025.zip`
- `divulgacao_anos_finais_municipios_2025.zip`

## Observações

- O Inep usa `-` para resultados não divulgados (participantes insuficientes no Saeb ou pedido de não divulgação).
- A rede **Pública** agrega estadual, municipal e federal; use uma rede por vez para evitar dupla contagem.
- As médias calculadas no dashboard são simples entre municípios, não ponderadas por alunos.
