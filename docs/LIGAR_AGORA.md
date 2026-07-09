# Ligar o banco na nuvem — comandos finais

São 4 passos, todos na sua máquina (onde há internet), dentro da pasta do projeto.

## Passo 1 — Criar o arquivo de configuração (.env)

Crie um arquivo chamado `.env` na raiz do projeto com este conteúdo
(a connection string do seu Supabase você tem na conversa com o Claude):

```
DATABASE_URL=postgresql+psycopg://postgres:SUA_SENHA@db.hefbcfxdovfjkdposvho.supabase.co:5432/postgres
SUMMARY_PROVIDER=extractive
TIMEZONE=America/Sao_Paulo
ENV=local
```

Troque `SUA_SENHA` pela senha do banco.

## Passo 2 — Instalar o projeto (só na primeira vez)
```bash
pip install -e .
```

## Passo 3 — Montar o banco na nuvem (cria tabelas + catálogo)
```bash
python jobs/setup_cloud.py
```
Você deve ver: "✓ Banco na nuvem pronto!"

## Passo 4 — Primeira coleta real + abrir a plataforma
```bash
python jobs/run_daily.py
streamlit run app/Home.py
```

---

## Se aparecer erro
- **erro de conexão / host**: confira a internet e se o projeto está "Saudável" no Supabase.
- **password authentication failed**: a senha no `.env` está errada.
- **qualquer outra coisa**: copie a mensagem e mande pro Claude.

## Depois que funcionar
1. Avise o Claude — aí ligamos o robô (agendamento) no GitHub.
2. **Troque a senha do banco** no painel do Supabase (Settings → Database →
   Reset database password) e atualize o `.env`, já que ela passou pela conversa.
