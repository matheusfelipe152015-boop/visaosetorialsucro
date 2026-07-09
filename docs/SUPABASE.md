# Ligar o banco na nuvem (Supabase) — passo a passo

Este guia te leva do zero até a plataforma rodando com banco na nuvem.
Não precisa entender de banco de dados: é só seguir na ordem.
Tempo estimado: ~15 minutos. Custo: R$ 0 (plano grátis, sem cartão).

---

## Parte 1 — Criar a conta e o projeto (você faz)

1. Acesse **https://supabase.com** e clique em **Start your project**.
2. Entre com sua conta do GitHub (ou e-mail). Não pede cartão de crédito.
3. Clique em **New project**.
4. Preencha:
   - **Name**: `canavis` (ou o nome que preferir)
   - **Database Password**: clique em **Generate a password** e **GUARDE essa senha**
     (vamos precisar dela). Anote num lugar seguro.
   - **Region**: escolha **South America (São Paulo)** — fica mais rápido.
5. Clique em **Create new project** e espere ~2 minutos (ele está montando seu banco).

---

## Parte 2 — Pegar o endereço de conexão (você faz, e me envia)

1. Com o projeto criado, clique no botão verde **Connect** (no topo da tela).
2. Vai abrir uma janela. Procure a aba/seção **Connection string** e dentro dela
   a opção **Transaction pooler** (ou "Pooler").
3. Vai aparecer um endereço parecido com isto:

   ```
   postgresql://postgres.abcdefgh:[YOUR-PASSWORD]@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
   ```

4. **Copie esse endereço inteiro.** Onde estiver escrito `[YOUR-PASSWORD]`,
   troque pela senha que você guardou na Parte 1.

> **O que me enviar:** esse endereço completo, já com a senha no lugar.
> Pode mandar aqui na conversa que eu finalizo a configuração.

⚠️ **Segurança:** essa senha dá acesso ao banco. Como estamos num ambiente de
trabalho, tudo bem me enviar para configurarmos juntos — mas não publique isso
em lugar público (e-mail aberto, redes, etc.). Depois você pode trocá-la pelo
painel do Supabase quando quiser.

---

## Parte 3 — Configurar (eu faço, ou te guio)

Com o endereço em mãos, faremos:

1. Colar o endereço no arquivo `.env`, na linha `DATABASE_URL=`.
   O formato final (note o `+psycopg` logo após `postgresql`):

   ```
   DATABASE_URL=postgresql+psycopg://postgres.abcdefgh:SUA_SENHA@aws-0-sa-east-1.pooler.supabase.com:6543/postgres
   ```

2. Montar o banco na nuvem com um comando só:

   ```bash
   python jobs/setup_cloud.py
   ```

   Isso cria todas as tabelas e cadastra o catálogo. Pode rodar sem medo.

3. Fazer a primeira coleta real:

   ```bash
   python jobs/run_daily.py
   ```

4. Abrir a plataforma lendo da nuvem:

   ```bash
   streamlit run app/Home.py
   ```

---

## Parte 4 — Ligar o robô (depois que o banco estiver no ar)

Para o agendamento automático (GitHub Actions) gravar na nuvem:

1. No seu repositório no GitHub, vá em **Settings → Secrets and variables → Actions**.
2. Clique em **New repository secret**.
3. Em **Name**, escreva exatamente: `DATABASE_URL`
4. Em **Secret**, cole o mesmo endereço de conexão (com `+psycopg` e a senha).
5. Salve. Pronto — a partir daí o robô coleta todo dia e grava na nuvem sozinho.

> Enquanto esse segredo não existir, o robô roda em "modo teste" (coleta e mostra
> nos logs, sem gravar). Então nada quebra antes da hora.

---

## Dúvidas comuns

- **O banco "dorme" depois de 7 dias parado?** Sim, no plano grátis. Mas o robô
  bate no banco todo dia, então ele nunca fica 7 dias parado — na prática, não te afeta.
- **Meus dados somem se ele dormir?** Não. Os dados ficam guardados; só o acesso
  fica suspenso até reativar pelo painel (um clique).
- **Preciso pagar?** Não para começar. Só faz sentido pensar no plano pago (US$ 25/mês)
  se isso virar uso intenso por várias pessoas, lá na frente.
