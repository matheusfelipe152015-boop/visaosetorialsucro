"""Contas individuais — cadastro, login, aprovação e níveis de acesso.

Três níveis (papel): 'adm', 'gerencia', 'analista'.
Situação: 'pendente' (recém-cadastrado) ou 'ativo' (aprovado).

Segurança:
  · A senha nunca é guardada em texto. Guardamos o hash PBKDF2-SHA256 com um
    "sal" aleatório por usuário (padrão da indústria).
  · O ADM é definido por um email fixo no cofre (ADMIN_EMAIL). O cadastro com
    esse email vira ADM automaticamente e já entra ativo — ninguém consegue
    se promover a ADM de outro jeito.

Regras de quem-pode-o-quê estão em `pode_conceder` e `papeis_que_pode_conceder`.
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
_ITERACOES = 200_000  # custo do PBKDF2 (quanto maior, mais difícil quebrar)


# ── segurança de senha ────────────────────────────────────────────────────

def _hash_senha(senha: str, sal: str) -> str:
    return hashlib.pbkdf2_hmac("sha256", senha.encode(), sal.encode(), _ITERACOES).hex()


def _senha_forte(senha: str) -> tuple[bool, str]:
    """Exige mínimo de robustez. Devolve (ok, motivo)."""
    if len(senha) < 8:
        return False, "A senha precisa ter ao menos 8 caracteres."
    if not re.search(r"[A-Za-z]", senha) or not re.search(r"\d", senha):
        return False, "Use letras e números na senha."
    return True, ""


def _email_valido(email: str) -> bool:
    return bool(re.match(r"^[^@\s]+@[^@\s]+\.[^@\s]+$", (email or "").strip()))


def _admin_email() -> str | None:
    """Email do ADM, lido do cofre (st.secrets) ou do ambiente."""
    try:
        if "ADMIN_EMAIL" in st.secrets:
            return str(st.secrets["ADMIN_EMAIL"]).strip().lower()
    except Exception:
        pass
    v = os.environ.get("ADMIN_EMAIL")
    return v.strip().lower() if v else None


# ── cadastro e login ──────────────────────────────────────────────────────

def cadastrar(email: str, nome: str, senha: str) -> tuple[bool, str]:
    """Cria uma conta nova. Devolve (ok, mensagem)."""
    email = (email or "").strip().lower()
    if not _email_valido(email):
        return False, "Email inválido."
    ok, motivo = _senha_forte(senha)
    if not ok:
        return False, motivo

    ja = _fetch_df_raw("SELECT id FROM usuarios WHERE email = :e", {"e": email})
    if not ja.empty:
        return False, "Já existe uma conta com esse email."

    sal = secrets.token_hex(16)
    h = _hash_senha(senha, sal)
    agora = datetime.utcnow()

    # se for o email do ADM (do cofre), entra como adm já ativo
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
        return True, "Conta de administrador criada. Você já pode entrar."
    return True, "Cadastro enviado. Aguarde a aprovação de um administrador ou gerente."


def autenticar(email: str, senha: str) -> tuple[dict | None, str]:
    """Verifica email+senha. Devolve (usuario, mensagem). usuario=None se falhar."""
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
        return None, "Sua conta ainda não foi aprovada."
    return {"id": u["id"], "email": u["email"], "nome": u["nome"],
            "papel": u["papel"]}, "ok"


# ── administração (aprovar, promover, revogar) ────────────────────────────

def papeis_que_pode_conceder(papel_de_quem_faz: str) -> list[str]:
    """Quais papéis cada nível pode atribuir a outros."""
    if papel_de_quem_faz == "adm":
        return ["analista", "gerencia", "adm"]   # ADM pode tudo
    if papel_de_quem_faz == "gerencia":
        return ["analista", "gerencia"]           # gerência NÃO cria adm
    return []                                     # analista não concede nada


def pode_administrar(papel: str) -> bool:
    """Quem enxerga a tela de administração."""
    return papel in ("adm", "gerencia")


def listar_usuarios() -> object:
    return _fetch_df_raw(
        "SELECT id, email, nome, papel, situacao, criado_em, aprovado_em "
        "FROM usuarios ORDER BY situacao DESC, criado_em DESC"
    )


def aprovar(uid: str, papel: str, quem_faz: dict) -> tuple[bool, str]:
    """Aprova (ativa) um usuário pendente e define o papel dele."""
    if papel not in papeis_que_pode_conceder(quem_faz["papel"]):
        return False, "Você não tem permissão para conceder esse nível."
    with get_engine().begin() as conn:
        conn.execute(
            text("""UPDATE usuarios SET situacao='ativo', papel=:p,
                    aprovado_em=:ae, aprovado_por=:por WHERE id=:id"""),
            {"id": uid, "p": papel, "ae": datetime.utcnow(), "por": quem_faz["email"]},
        )
    return True, "Usuário aprovado."


def mudar_papel(uid: str, novo_papel: str, quem_faz: dict) -> tuple[bool, str]:
    """Muda o nível de um usuário já ativo (respeitando as regras)."""
    if novo_papel not in papeis_que_pode_conceder(quem_faz["papel"]):
        return False, "Você não tem permissão para conceder esse nível."
    # ninguém rebaixa a si mesmo por engano
    if uid == quem_faz["id"] and novo_papel != quem_faz["papel"]:
        return False, "Você não pode alterar o seu próprio nível."
    with get_engine().begin() as conn:
        conn.execute(
            text("UPDATE usuarios SET papel=:p WHERE id=:id"),
            {"id": uid, "p": novo_papel},
        )
    return True, "Nível atualizado."


def revogar(uid: str, quem_faz: dict) -> tuple[bool, str]:
    """Revoga o acesso de um usuário (volta a 'pendente')."""
    if uid == quem_faz["id"]:
        return False, "Você não pode revogar o seu próprio acesso."
    # não deixa gerência mexer em adm
    alvo = _fetch_df_raw("SELECT papel FROM usuarios WHERE id=:id", {"id": uid})
    if not alvo.empty and alvo.iloc[0]["papel"] == "adm" and quem_faz["papel"] != "adm":
        return False, "Apenas um administrador pode revogar outro administrador."
    with get_engine().begin() as conn:
        conn.execute(
            text("UPDATE usuarios SET situacao='pendente' WHERE id=:id"), {"id": uid}
        )
    return True, "Acesso revogado (usuário voltou a pendente)."


def usuario_logado() -> dict | None:
    """Devolve o usuário logado nesta sessão (ou None)."""
    return st.session_state.get("_usuario")
