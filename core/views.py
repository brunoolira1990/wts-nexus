from __future__ import annotations

import json
import logging
from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import Atendimento, Cliente, Contato, Mensagem
from .services import enviar_mensagem_whatsapp

logger = logging.getLogger(__name__)


@login_required
def dashboard(request: HttpRequest, contato_id: int | None = None) -> HttpResponse:
    contatos = Contato.objects.all()

    contato_selecionado: Contato | None
    if contato_id is not None:
        contato_selecionado = get_object_or_404(Contato, id=contato_id)
    else:
        contato_selecionado = contatos.first()

    if request.method == "POST" and contato_selecionado:
        texto = request.POST.get("texto", "").strip()
        if texto:
            enviar_mensagem_whatsapp(contato_selecionado.waid, texto)
        return redirect("core:dashboard_contato", contato_id=contato_selecionado.id)

    mensagens = (
        contato_selecionado.mensagens.all() if contato_selecionado is not None else []
    )

    context = {
        "contatos": contatos,
        "contato_selecionado": contato_selecionado,
        "mensagens": mensagens,
    }
    return render(request, "core/dashboard.html", context)


@csrf_exempt
def webhook(request: HttpRequest) -> HttpResponse:
    """
    Webhook de integração com a API do WhatsApp (Meta).

    - GET: verificação de token (setup no painel do Meta).
    - POST: recebimento de mensagens. Sempre retorna 200 para a Meta.
    """
    # Log de depuração global (antes de qualquer validação)
    logger.info(
        "Webhook request: method=%s headers=%s body=%s",
        request.method,
        dict(request.headers),
        request.body.decode("utf-8", errors="replace"),
    )

    if request.method == "GET":
        verify_token = settings.WHATSAPP_VERIFY_TOKEN
        mode = request.GET.get("hub.mode")
        token = request.GET.get("hub.verify_token")
        challenge = request.GET.get("hub.challenge")

        if mode and token:
            if mode == "subscribe" and token == verify_token:
                return HttpResponse(challenge or "")
            return HttpResponse("Token inválido", status=403)
        return HttpResponse("Parâmetros ausentes", status=403)

    if request.method != "POST":
        return HttpResponse(status=200)

    # POST: sempre retornar 200 para a Meta, mesmo com erro interno
    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError as e:
        logger.exception("Webhook POST: JSON inválido - %s", e)
        return HttpResponse(status=200)

    try:
        entries = payload.get("entry", [])
        for entry in entries:
            changes = entry.get("changes", [])
            for change in changes:
                value = change.get("value", {})
                messages = value.get("messages", [])
                contacts = value.get("contacts", [])

                for idx, message in enumerate(messages):
                    # Aceita qualquer waid (produção ou teste), ex: 982237891640106
                    waid = message.get("from")
                    if not waid:
                        continue
                    waid = str(waid).strip()

                    contact_name = waid
                    if idx < len(contacts):
                        profile = contacts[idx].get("profile") or {}
                        contact_name = profile.get("name") or waid

                    msg_type = message.get("type")
                    texto = ""
                    if msg_type == "text":
                        texto = (message.get("text") or {}).get("body", "")
                    # Outros tipos (image, audio, etc.) podem ser expandidos depois

                    if not texto:
                        continue

                    ts_raw = message.get("timestamp")
                    if ts_raw:
                        try:
                            ts_dt = datetime.fromtimestamp(
                                int(ts_raw),
                                tz=timezone.utc,
                            )
                        except (TypeError, ValueError):
                            ts_dt = timezone.now()
                    else:
                        ts_dt = timezone.now()

                    contato, created = Contato.objects.get_or_create(
                        waid=waid,
                        defaults={
                            "nome": contact_name,
                            "ultima_mensagem": texto,
                        },
                    )
                    if not created:
                        contato.ultima_mensagem = texto
                        contato.save(update_fields=["ultima_mensagem", "atualizado_em"])

                    Mensagem.objects.create(
                        contato=contato,
                        texto=texto,
                        direcao=Mensagem.Direcao.ENTRADA,
                        status=Mensagem.Status.ENTREGUE,
                        timestamp=ts_dt,
                        meta_message_id=message.get("id", ""),
                    )

                    # --- Fila de atendimento ---
                    cliente, _ = Cliente.objects.get_or_create(
                        telefone=waid,
                        defaults={"nome": contact_name},
                    )
                    if cliente.nome != contact_name and contact_name != waid:
                        cliente.nome = contact_name
                        cliente.save(update_fields=["nome"])

                    aberto = (
                        Atendimento.objects.filter(cliente=cliente)
                        .filter(
                            status__in=[
                                Atendimento.Status.AGUARDANDO,
                                Atendimento.Status.EM_ATENDIMENTO,
                            ]
                        )
                        .order_by("-data_inicio")
                        .first()
                    )

                    texto_limpo = texto.strip().lower()
                    if aberto and aberto.status == Atendimento.Status.EM_ATENDIMENTO:
                        continue  # Robô mudo; humano atende
                    if texto_limpo == "oi":
                        if not aberto:
                            Atendimento.objects.create(
                                cliente=cliente,
                                departamento=Atendimento.Departamento.SEM_DEPARTAMENTO,
                                status=Atendimento.Status.AGUARDANDO,
                            )
                            menu = (
                                "Olá! Escolha o departamento:\n"
                                "1 - Comercial\n2 - Financeiro\n3 - Técnico"
                            )
                            try:
                                enviar_mensagem_whatsapp(waid, menu)
                            except Exception as e:
                                logger.exception("Fila: falha ao enviar menu - %s", e)
                        continue
                    if texto_limpo in ("1", "2", "3") and aberto and aberto.departamento == Atendimento.Departamento.SEM_DEPARTAMENTO:
                        dept_map = {
                            "1": (Atendimento.Departamento.COMERCIAL, "Comercial"),
                            "2": (Atendimento.Departamento.FINANCEIRO, "Financeiro"),
                            "3": (Atendimento.Departamento.TECNICO, "Técnico"),
                        }
                        dept, label = dept_map[texto_limpo]
                        aberto.departamento = dept
                        aberto.save(update_fields=["departamento"])
                        msg_fila = f"Você está na fila do {label}. Aguarde um momento."
                        try:
                            enviar_mensagem_whatsapp(waid, msg_fila)
                        except Exception as e:
                            logger.exception("Fila: falha ao enviar msg fila - %s", e)
    except Exception as e:
        logger.exception("Webhook POST: erro ao processar mensagens - %s", e)
        return HttpResponse(status=200)

    return HttpResponse(status=200)


