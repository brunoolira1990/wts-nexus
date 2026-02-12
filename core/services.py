from __future__ import annotations

import logging
from typing import Optional

import requests
from django.conf import settings
from django.utils import timezone

from .models import Contato, Mensagem

logger = logging.getLogger(__name__)


def enviar_mensagem_whatsapp(waid: str, texto: str) -> Mensagem:
    """
    Envia uma mensagem de texto via API do WhatsApp (Meta) e registra no banco.
    """
    if not settings.META_WA_PHONE_NUMBER_ID or not settings.META_WA_ACCESS_TOKEN:
        raise RuntimeError("Configuração da API do WhatsApp não encontrada.")

    url = (
        f"https://graph.facebook.com/"
        f"{settings.META_WA_API_VERSION}/"
        f"{settings.META_WA_PHONE_NUMBER_ID}/messages"
    )

    headers = {
        "Authorization": f"Bearer {settings.META_WA_ACCESS_TOKEN}",
        "Content-Type": "application/json",
    }

    payload = {
        "messaging_product": "whatsapp",
        "to": waid,
        "type": "text",
        "text": {"body": texto},
    }

    try:
        response = requests.post(url, headers=headers, json=payload, timeout=10)
    except requests.RequestException as exc:
        logger.exception("Erro de rede ao enviar mensagem para %s", waid)
        msg_status = Mensagem.Status.FALHA
        meta_message_id: Optional[str] = None
    else:
        if response.ok:
            msg_status = Mensagem.Status.ENVIADA
            try:
                data = response.json()
                meta_message_id = (
                    (data.get("messages") or [{}])[0].get("id")  # type: ignore[assignment]
                )
            except Exception:  # noqa: BLE001
                meta_message_id = None
        else:
            logger.error(
                "Falha ao enviar mensagem para %s: %s %s",
                waid,
                response.status_code,
                response.text,
            )
            msg_status = Mensagem.Status.FALHA
            meta_message_id = None

    contato, created = Contato.objects.get_or_create(
        waid=waid,
        defaults={"nome": waid, "ultima_mensagem": texto},
    )
    if not created:
        contato.ultima_mensagem = texto
        contato.save(update_fields=["ultima_mensagem", "atualizado_em"])

    mensagem = Mensagem.objects.create(
        contato=contato,
        texto=texto,
        direcao=Mensagem.Direcao.SAIDA,
        status=msg_status,
        timestamp=timezone.now(),
        meta_message_id=meta_message_id or "",
    )

    return mensagem

