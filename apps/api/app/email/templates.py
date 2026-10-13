"""Plantillas de correo es/en/pt (feature 026). Texto plano + HTML mínimo, sin rastreo."""

from __future__ import annotations

from html import escape

from app.email.base import EmailMessage

_T = {
    "es": {
        "verify_subject": "Confirma tu correo en StayLever",
        "verify_body": "Hola {name}:\n\nConfirma tu correo para activar tu cuenta de StayLever:\n{link}\n\nEl enlace vence en 24 horas. Si no fuiste tú, ignora este mensaje.",
        "verify_cta": "Confirmar correo",
        "reset_subject": "Restablece tu contraseña de StayLever",
        "reset_body": "Hola {name}:\n\nPara elegir una contraseña nueva entra aquí:\n{link}\n\nEl enlace vence en 1 hora y solo sirve una vez. Si no lo pediste, ignora este mensaje: tu contraseña sigue igual.",
        "reset_cta": "Elegir contraseña nueva",
        "exists_subject": "Ya tienes una cuenta en StayLever",
        "exists_body": "Hola:\n\nAlguien intentó registrarse con este correo, pero ya tienes una cuenta. Entra aquí:\n{link}\n\nSi olvidaste la contraseña, usa \"Olvidé mi contraseña\" en esa página.",
        "exists_cta": "Entrar a StayLever",
    },
    "en": {
        "verify_subject": "Confirm your email for StayLever",
        "verify_body": "Hi {name},\n\nConfirm your email to activate your StayLever account:\n{link}\n\nThe link expires in 24 hours. If this wasn't you, ignore this message.",
        "verify_cta": "Confirm email",
        "reset_subject": "Reset your StayLever password",
        "reset_body": "Hi {name},\n\nTo choose a new password go here:\n{link}\n\nThe link expires in 1 hour and works once. If you didn't ask for it, ignore this message: your password stays the same.",
        "reset_cta": "Choose a new password",
        "exists_subject": "You already have a StayLever account",
        "exists_body": "Hi,\n\nSomeone tried to sign up with this email, but you already have an account. Sign in here:\n{link}\n\nIf you forgot your password, use \"Forgot password\" on that page.",
        "exists_cta": "Sign in to StayLever",
    },
    "pt": {
        "verify_subject": "Confirme seu e-mail no StayLever",
        "verify_body": "Olá {name},\n\nConfirme seu e-mail para ativar sua conta do StayLever:\n{link}\n\nO link expira em 24 horas. Se não foi você, ignore esta mensagem.",
        "verify_cta": "Confirmar e-mail",
        "reset_subject": "Redefina sua senha do StayLever",
        "reset_body": "Olá {name},\n\nPara escolher uma nova senha acesse:\n{link}\n\nO link expira em 1 hora e funciona uma vez. Se não pediu, ignore esta mensagem: sua senha continua a mesma.",
        "reset_cta": "Escolher nova senha",
        "exists_subject": "Você já tem uma conta no StayLever",
        "exists_body": "Olá,\n\nAlguém tentou se cadastrar com este e-mail, mas você já tem uma conta. Entre aqui:\n{link}\n\nSe esqueceu a senha, use \"Esqueci minha senha\" nessa página.",
        "exists_cta": "Entrar no StayLever",
    },
}


def _lang(lang: str | None) -> str:
    return lang if lang in _T else "es"


def _html(text: str, link: str, cta: str) -> str:
    paras = "".join(
        f"<p>{escape(p).replace(chr(10), '<br>')}</p>" for p in text.split("\n\n") if link not in p
    )
    button = (
        f'<p><a href="{escape(link)}" style="background:#2563eb;color:#fff;padding:10px 16px;'
        f'border-radius:8px;text-decoration:none;display:inline-block">{escape(cta)}</a></p>'
    )
    return f'<div style="font-family:system-ui,sans-serif;line-height:1.5">{paras}{button}</div>'


def _build(kind: str, to: str, lang: str | None, link: str, name: str = "") -> EmailMessage:
    t = _T[_lang(lang)]
    text = t[f"{kind}_body"].format(name=name or "", link=link)
    return EmailMessage(
        to=to,
        subject=t[f"{kind}_subject"],
        text=text,
        html=_html(text, link, t[f"{kind}_cta"]),
    )


def verify_email(to: str, lang: str | None, link: str, name: str) -> EmailMessage:
    return _build("verify", to, lang, link, name)


def reset_password(to: str, lang: str | None, link: str, name: str) -> EmailMessage:
    return _build("reset", to, lang, link, name)


def already_registered(to: str, lang: str | None, link: str) -> EmailMessage:
    return _build("exists", to, lang, link)
