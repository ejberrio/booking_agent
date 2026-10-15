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
        "delcode_subject": "Código para borrar tu cuenta de StayLever",
        "delcode_body": "Hola {name}:\n\nTu código para confirmar el borrado de tu cuenta es: {code}\n\nVence en 15 minutos. Si no lo pediste, ignora este mensaje y tu cuenta sigue igual.",
        "deleted_subject": "Tu cuenta de StayLever fue eliminada",
        "deleted_body": "Hola {name}:\n\nBorramos tu cuenta de StayLever y todos sus datos. Las copias de seguridad se eliminan solas en un máximo de 7 días.\n\nGracias por haber usado StayLever. Si fue un error, escríbenos a privacy@staylever.com.",
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
        "delcode_subject": "Code to delete your StayLever account",
        "delcode_body": "Hi {name},\n\nYour code to confirm deleting your account is: {code}\n\nIt expires in 15 minutes. If you didn't ask for it, ignore this message and your account stays as is.",
        "deleted_subject": "Your StayLever account was deleted",
        "deleted_body": "Hi {name},\n\nWe deleted your StayLever account and all its data. Backups are erased automatically within 7 days.\n\nThanks for using StayLever. If this was a mistake, write to privacy@staylever.com.",
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
        "delcode_subject": "Código para excluir sua conta do StayLever",
        "delcode_body": "Olá {name},\n\nSeu código para confirmar a exclusão da sua conta é: {code}\n\nEle expira em 15 minutos. Se não pediu, ignore esta mensagem e sua conta continua igual.",
        "deleted_subject": "Sua conta do StayLever foi excluída",
        "deleted_body": "Olá {name},\n\nExcluímos sua conta do StayLever e todos os seus dados. As cópias de segurança são apagadas automaticamente em até 7 dias.\n\nObrigado por usar o StayLever. Se foi um engano, escreva para privacy@staylever.com.",
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


def _plain(kind: str, to: str, lang: str | None, **fields: str) -> EmailMessage:
    """Correo sin botón (feature 028): código de borrado y confirmación."""
    t = _T[_lang(lang)]
    text = t[f"{kind}_body"].format(**fields)
    paras = "".join(f"<p>{escape(p).replace(chr(10), '<br>')}</p>" for p in text.split("\n\n"))
    html = f'<div style="font-family:system-ui,sans-serif;line-height:1.5">{paras}</div>'
    return EmailMessage(to=to, subject=t[f"{kind}_subject"], text=text, html=html)


def delete_code(to: str, lang: str | None, name: str, code: str) -> EmailMessage:
    return _plain("delcode", to, lang, name=name or "", code=code)


def account_deleted(to: str, lang: str | None, name: str) -> EmailMessage:
    return _plain("deleted", to, lang, name=name or "")


# --------- feature 030: informe completo e invitación desde la lista de espera ---------

_R = {
    "es": {
        "report_subject": "Tu informe de eventos y precios: {place}",
        "report_intro": "Hola:\n\nEstos son los eventos más importantes de los próximos 3 meses en {place} y el precio que te sugerimos para esas noches (partiendo de {base} {cur} por noche):",
        "report_none": "Por ahora no encontramos eventos grandes en {place}. Te avisaremos en la app cuando aparezcan.",
        "report_more": "…y {n} evento(s) más en tu informe en vivo, que se actualiza cada semana.",
        "report_outro": "Las sugerencias se actualizan cada día en tu cuenta:",
        "report_cta": "Abrir mi informe",
        "rel": {"high": "alta", "medium": "media", "low": "baja"},
        "invite_subject": "Ya tienes cupo en la beta de StayLever",
        "invite_body": "Hola:\n\nSe abrió un cupo para ti en la beta de StayLever. Crea tu cuenta con este enlace (vence en {days} días):\n{link}\n\nSi ya no te interesa, ignora este mensaje y borraremos tu correo.",
        "invite_cta": "Crear mi cuenta",
    },
    "en": {
        "report_subject": "Your events and pricing report: {place}",
        "report_intro": "Hi,\n\nHere are the most important events for the next 3 months in {place} and the price we suggest for those nights (starting from {base} {cur} per night):",
        "report_none": "We didn't find big events in {place} yet. We'll let you know in the app when they show up.",
        "report_more": "…and {n} more event(s) in your live report, updated every week.",
        "report_outro": "Suggestions are updated every day in your account:",
        "report_cta": "Open my report",
        "rel": {"high": "high", "medium": "medium", "low": "low"},
        "invite_subject": "Your spot in the StayLever beta is ready",
        "invite_body": "Hi,\n\nA spot opened for you in the StayLever beta. Create your account with this link (it expires in {days} days):\n{link}\n\nIf you're no longer interested, ignore this message and we'll delete your email.",
        "invite_cta": "Create my account",
    },
    "pt": {
        "report_subject": "Seu relatório de eventos e preços: {place}",
        "report_intro": "Olá,\n\nEstes são os eventos mais importantes dos próximos 3 meses em {place} e o preço que sugerimos para essas noites (a partir de {base} {cur} por noite):",
        "report_none": "Ainda não encontramos grandes eventos em {place}. Avisaremos no app quando aparecerem.",
        "report_more": "…e mais {n} evento(s) no seu relatório ao vivo, atualizado toda semana.",
        "report_outro": "As sugestões são atualizadas todos os dias na sua conta:",
        "report_cta": "Abrir meu relatório",
        "rel": {"high": "alta", "medium": "média", "low": "baixa"},
        "invite_subject": "Sua vaga na beta do StayLever está pronta",
        "invite_body": "Olá,\n\nAbriu uma vaga para você na beta do StayLever. Crie sua conta com este link (expira em {days} dias):\n{link}\n\nSe não tiver mais interesse, ignore esta mensagem e apagaremos seu e-mail.",
        "invite_cta": "Criar minha conta",
    },
}


EMAIL_EVENTS = 5  # el resto, en la app (la lista completa no va por correo)


def _money(value: str) -> str:
    try:
        return f"{int(float(value)):,}".replace(",", ".")
    except ValueError:
        return value


def full_report(to: str, lang: str | None, data: dict, link: str) -> EmailMessage:
    t = _R[_lang(lang)]
    place = data["municipality"]["label"]
    cur = data.get("currency") or "COP"
    lines = [t["report_intro"].format(place=place, base=_money(data["weekday_price"]), cur=cur)]
    rows = []
    for ev in data["events"][:EMAIL_EVENTS]:
        when = ev["start_date"] if ev["end_date"] == ev["start_date"] else f"{ev['start_date']} → {ev['end_date']}"
        rows.append(
            f"• {when} — {ev['name']} ({t['rel'].get(ev['relevance'], ev['relevance'])}): "
            f"{_money(ev['suggested_price'])} {cur} (+{ev['pct']}%)"
        )
    lines.append("\n".join(rows) if rows else t["report_none"].format(place=place))
    if len(data["events"]) > EMAIL_EVENTS:
        lines.append(t["report_more"].format(n=len(data["events"]) - EMAIL_EVENTS))
    lines.append(f"{t['report_outro']}\n{link}")
    text = "\n\n".join(lines)
    return EmailMessage(to=to, subject=t["report_subject"].format(place=place), text=text,
                        html=_html(text, link, t["report_cta"]))


def waitlist_invite(to: str, lang: str | None, link: str, days: int) -> EmailMessage:
    t = _R[_lang(lang)]
    text = t["invite_body"].format(link=link, days=days)
    return EmailMessage(to=to, subject=t["invite_subject"], text=text,
                        html=_html(text, link, t["invite_cta"]))


_D = {
    "es": {
        "subject": "Tu semana en StayLever: {n} noche(s) para revisar",
        "subject_events": "Tu semana en StayLever: eventos nuevos en tu zona",
        "hello": "Hola:",
        "nights": "Noches de las próximas 2 semanas con precio sugerido:",
        "manual": "Estás sin conexión: aprueba en StayLever y cópialo en cada plataforma:",
        "events": "Eventos nuevos en tu zona esta semana:",
        "cta": "Ver mis sugerencias",
        "off": "¿No quieres este resumen? Apágalo aquí: {link}",
        "rel": {"high": "alta", "medium": "media", "low": "baja"},
    },
    "en": {
        "subject": "Your week on StayLever: {n} night(s) to review",
        "subject_events": "Your week on StayLever: new events near you",
        "hello": "Hi,",
        "nights": "Nights in the next 2 weeks with a suggested price:",
        "manual": "You're offline: approve in StayLever and copy it on each platform:",
        "events": "New events near you this week:",
        "cta": "See my suggestions",
        "off": "Don't want this summary? Turn it off here: {link}",
        "rel": {"high": "high", "medium": "medium", "low": "low"},
    },
    "pt": {
        "subject": "Sua semana no StayLever: {n} noite(s) para revisar",
        "subject_events": "Sua semana no StayLever: eventos novos na sua região",
        "hello": "Olá,",
        "nights": "Noites das próximas 2 semanas com preço sugerido:",
        "manual": "Você está sem conexão: aprove no StayLever e copie em cada plataforma:",
        "events": "Eventos novos na sua região esta semana:",
        "cta": "Ver minhas sugestões",
        "off": "Não quer este resumo? Desative aqui: {link}",
        "rel": {"high": "alta", "medium": "média", "low": "baixa"},
    },
}


def weekly_digest(to: str, lang: str | None, data: dict, link: str, off_link: str) -> EmailMessage:
    t = _D[_lang(lang)]
    parts = [t["hello"]]
    if data["nights"]:
        rows = []
        for n in data["nights"]:
            when = n["date_from"] if n["date_to"] == n["date_from"] else f"{n['date_from']} → {n['date_to']}"
            cur = f"{_money(n['current'])} → " if n.get("current") else ""
            why = f" ({n['reason']})" if n.get("reason") else ""
            rows.append(f"• {when}: {cur}{_money(n['suggested'])}{why}")
        parts.append(t["nights"] + "\n" + "\n".join(rows))
        if data.get("manual") and data.get("links"):
            parts.append(t["manual"] + "\n" + "\n".join(
                f"• {x['channel'].capitalize()}: {x['url']}" for x in data["links"]))
    if data["events"]:
        parts.append(t["events"] + "\n" + "\n".join(
            f"• {e['start_date']} — {e['name']} ({t['rel'].get(e['relevance'], e['relevance'])})"
            for e in data["events"]))
    parts.append(link)
    text = "\n\n".join(parts) + "\n\n" + t["off"].format(link=off_link)
    subject = (t["subject"].format(n=len(data["nights"])) if data["nights"]
               else t["subject_events"])
    html = _html("\n\n".join(parts), link, t["cta"]) + (
        f'<p style="font-family:system-ui,sans-serif;font-size:12px;color:#666">'
        f'{escape(t["off"].format(link=""))}<a href="{escape(off_link)}">{escape(off_link)}</a></p>'
    )
    return EmailMessage(to=to, subject=subject, text=text, html=html)
