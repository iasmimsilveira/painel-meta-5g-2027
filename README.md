# Meta 5G 2027 · painel com dados públicos

Painel independente sobre a meta de **31/07/2027** do Edital 5G da Anatel (faixa de 3,5 GHz): municípios da lista oficial, em regra com 100 mil habitantes ou mais, precisam ter no mínimo **1 site 5G a cada 15 mil habitantes**.

Feito só com dados públicos. Não representa posição oficial da Anatel nem de nenhuma operadora.

## Fontes

| Dado | Origem |
|---|---|
| Compromissos do Edital 5G | Anatel, `dadosabertos/paineis_de_dados/acompanhamento_e_controle/5g.zip` |
| Estações licenciadas do SMP | Anatel, `dadosabertos/paineis_de_dados/outorga_e_licenciamento/estacoes_smp.zip` |
| População | IBGE: estimativa 2020 (tabela 6579) e Censo 2022 (tabela 4709), em `dados/populacao_ibge.json` |

## Como funciona

- `atualizar.py` baixa os arquivos da Anatel, conta os sites 5G de 3,5 GHz de cada operadora por município, calcula a meta (população IBGE 2020 ÷ 15 mil, arredondado para cima) e gera `site/index.html`.
- Se os dados vierem incompletos, o script para com erro e não sobrescreve a página anterior.
- O GitHub Actions (`.github/workflows/atualizar.yml`) roda toda segunda-feira às 8h e publica a página no GitHub Pages. Também dá para rodar manualmente em **Actions → Atualizar painel → Run workflow**.

## Rodar no computador

```bash
python3 atualizar.py
```

Precisa só do Python 3, sem bibliotecas extras. Baixa cerca de 95 MB.

A página aceita `?op=TIM`, `?op=CLARO` ou `?op=VIVO` na URL para abrir já com a operadora escolhida.
