"""Contas individuais — cadastro, login, aprovacao e niveis de acesso.

Tres niveis (papel): 'adm', 'gerencia', 'analista'.
Situacao: 'pendente' (recem-cadastrado) ou 'ativo' (aprovado).

Seguranca:
  - A senha nunca e guardada em texto. Guardamos o hash PBKDF2-SHA256 com um
    "sal" aleatorio por usuario.
  - O ADM e definido por um email fixo no cofre (ADMIN_EMAIL). Cadastro com
    esse email vira ADM automaticamente e ja entra ativo.
"""

from __future__ import annotations

import hashlib
import os
import re
import secrets
import uuid
from datetime import datetime

import streamlit as st
from sqlalchemy import text

from src.persistence.db import _fetch_df_raw, get_engine

PAPEIS = ("adm", "gerencia", "analista")
_ITERACOES = 200_000


def _hash_senha(senha, sal):
    return hashlib.pbkdf2_hmac("sha256", senha.encode(), sal.encode(), _ITERACOES).hex()


def _senha_forte(senha):
    if len(senha) < 8:
        return False, "A senha precisa ter ao menos 8 caracteres."
    if not re.search(r"[A-Za-z]", senha) or not re.search(r"\d", senha):
        return False, "Use letras e numeros na senha."
    return True, ""


def _email_valido(email):
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", (email or "").strip()))


def _admin_email():
    try:
        if "ADMIN_EMAIL" in st.secrets:
            return str(st.secrets["ADMIN_EMAIL"]).strip().lower()
    except Exception:
        pass
    v = os.environ.get("ADMIN_EMAIL")
    return v.strip().lower() if v else None


def cadastrar(email, nome, senha):
    """Cria uma conta nova. Devolve (ok, mensagem)."""
    email = (email or "").strip().lower()
    if not _email_valido(email):
        return False, "Email invalido."
    ok, motivo = _senha_forte(senha)
    if not ok:
        return False, motivo

    ja = _fetch_df_raw("SELECT id FROM usuarios WHERE email = :e", {"e": email})
    if not ja.empty:
        return False, "Ja existe uma conta com esse email."

    sal = secrets.token_hex(16)
    h = _hash_senha(senha, sal)
    agora = datetime.utcnow()

    eh_adm = _admin_email() is not None and email == _admin_email()
    papel = "adm" if eh_adm else "analista"
    situacao = "ativo" if eh_adm else "pendente"

    with get_engine().begin() as conn:
        conn.execute(
            text("""INSERT INTO usuarios
                    (id, email, nome, senha_hash, senha_sal, papel, situacao,
                     criado_em, aprovado_em, aprovado_por)
                    VALUES(:id,:e,:n,:h,:s,:p,:sit,:c,:ae,:ap)"""),
            {"id": uuid.uuid4().hex, "e": email, "n": (nome or "").strip(),
             "h": h, "s": sal, "p": papel, "sit": situacao, "c": agora,
             "ae": agora if eh_adm else None, "ap": "sistema" if eh_adm else None},
        )
    if eh_adm:
        return True, "Conta de administrador criada. Voce ja pode entrar."
    return True, "Cadastro enviado. Aguarde a aprovacao de um administrador ou gerente."


def autenticar(email, senha):
    """Verifica email+senha. Devolve (usuario, mensagem)."""
    email = (email or "").strip().lower()
    df = _fetch_df_raw(
        "SELECT id, email, nome, senha_hash, senha_sal, papel, situacao "
        "FROM usuarios WHERE email = :e",
        {"e": email},
    )
    if df.empty:
        return None, "Email ou senha incorretos."
    u = df.iloc[0].to_dict()
    if _hash_senha(senha, u["senha_sal"]) != u["senha_hash"]:
        return None, "Email ou senha incorretos."
    if u["situacao"] != "ativo":
        return None, "Sua conta ainda nao foi aprovada."
    return {"id": u["id"], "email": u["email"], "nome": u["nome"],
            "papel": u["papel"]}, "ok"


def papeis_que_pode_conceder(papel_de_quem_faz):
    """Quais papeis cada nivel pode atribuir a outros."""
    if papel_de_quem_faz == "adm":
        return ["analista", "gerencia", "adm"]
    if papel_de_quem_faz == "gerencia":
        return ["analista", "gerencia"]
    return []


def pode_administrar(papel):
    return papel in ("adm", "gerencia")


def listar_usuarios():
    return _fetch_df_raw(
        "SELECT id, email, nome, papel, situacao, criado_em, aprovado_em "
        "FROM usuarios ORDER BY situacao DESC, criado_em DESC"
    )


def aprovar(uid, papel, quem_faz):
    if papel not in papeis_que_pode_conceder(quem_faz["papel"]):
        return False, "Voce nao tem permissao para conceder esse nivel."
    with get_engine().begin() as conn:
        conn.execute(
            text("""UPDATE usuarios SET situacao='ativo', papel=:p,
                    aprovado_em=:ae, aprovado_por=:por WHERE id=:id"""),
            {"id": uid, "p": papel, "ae": datetime.utcnow(), "por": quem_faz["email"]},
        )
    return True, "Usuario aprovado."


def mudar_papel(uid, novo_papel, quem_faz):
    if novo_papel not in papeis_que_pode_conceder(quem_faz["papel"]):
        return False, "Voce nao tem permissao para conceder esse nivel."
    if uid == quem_faz["id"] and novo_papel != quem_faz["papel"]:
        return False, "Voce nao pode alterar o seu proprio nivel."
    with get_engine().begin() as conn:
        conn.execute(
            text("UPDATE usuarios SET papel=:p WHERE id=:id"),
            {"id": uid, "p": novo_papel},
        )
    return True, "Nivel atualizado."


def revogar(uid, quem_faz):
    if uid == quem_faz["id"]:
        return False, "Voce nao pode revogar o seu proprio acesso."
    alvo = _fetch_df_raw("SELECT papel FROM usuarios WHERE id=:id", {"id": uid})
    if not alvo.empty and alvo.iloc[0]["papel"] == "adm" and quem_faz["papel"] != "adm":
        return False, "Apenas um administrador pode revogar outro administrador."
    with get_engine().begin() as conn:
        conn.execute(
            text("UPDATE usuarios SET situacao='pendente' WHERE id=:id"), {"id": uid}
        )
    return True, "Acesso revogado (usuario voltou a pendente)."


def usuario_logado():
    return st.session_state.get("_usuario")
