# VISÃO SETORIAL SUCRO — Inteligência do setor sucroenergético (MVP)

Plataforma web privada que centraliza notícias, indicadores de mercado, dados de
safra/produção e fatos relevantes do setor sucroenergético brasileiro, para apoiar
analistas e gestores na preparação de comitês. **Camada de inteligência, não de
decisão**: não gera rating, não classifica notícia como positiva/negativa e não
usa dado interno.

## Princípios

- **Rastreabilidade total** — todo registro guarda fonte, URL, data de referência,
  de publicação e de coleta, separadamente. A interface exibe isso em todo card
  (o *selo de frescor* é a assinatura visual do produto).
- **Custo quase-zero** — roda local em SQLite; em produção, free tiers
  (Supabase, GitHub Actions, Streamlit Community Cloud, Resend).
- **Idempotência** — recoletar nunca duplica (upsert por `ON CONFLICT`).
- **Coletores isolados** — um adaptador por fonte, com a mesma interface; trocar
  uma fonte não afeta o resto. O app **não coleta** durante a navegação.
- **Confiabilidade > cobertura** — fonte indisponível vira alerta, não dado falso.

## Primeira integração vertical

`BCB · SGS série 1` → câmbio **USD/BRL (PTAX venda)**. API pública, estável, sem
licença restritiva. Prova o encanamento ponta a ponta: coleta → validação →
banco → dashboard → saúde.

## Estrutura

```
config/            Configuração (Pydantic Settings)
db/migrations/     Schema portátil (SQLite + PostgreSQL); runner aplica todos em ordem
db/seeds/          Dados de demonstração (sinalizados)
src/domain/        Modelos, enums, regra de frescor
src/persistence/   Engine + repositórios (upsert idempotente)
src/collectors/    Contrato base + coletor BCB PTAX
src/services/      Regras puras e testáveis (ex.: filtragem de notícias)
src/summarize/     Resumo extrativo (plugue de LLM desligado)
src/theme.py       Identidade visual (CSS + Plotly + selo de frescor)
app/               Streamlit: Home (filtros + watchlist) + páginas
jobs/run_daily.py  Rotina diária de coleta
tests/             parse PTAX, frescor, idempotência, filtragem de notícias
```

Ver **docs/INSTALACAO.md** para subir em 3 comandos.

> Nome do produto provisório. A camada de resumo de notícias usa modo extrativo
> (sem custo/risco); o plugue de LLM existe na interface, mas fica **desligado**.
