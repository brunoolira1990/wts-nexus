from __future__ import annotations

import json
from datetime import datetime

from django.conf import settings
from django.contrib.auth.decorators import login_required
from django.http import HttpRequest, HttpResponse, JsonResponse
from django.shortcuts import get_object_or_404, redirect, render
from django.utils import timezone
from django.views.decorators.csrf import csrf_exempt

from .models import Contato, Mensagem
from .services import enviar_mensagem_whatsapp


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
    - POST: recebimento de mensagens.
    """
    print(request.body)
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
        return JsonResponse({"detail": "Method not allowed."}, status=405)

    try:
        payload = json.loads(request.body.decode("utf-8"))
    except json.JSONDecodeError:
        return JsonResponse({"detail": "Invalid JSON payload."}, status=400)

    entries = payload.get("entry", [])
    for entry in entries:
        changes = entry.get("changes", [])
        for change in changes:
            value = change.get("value", {})
            messages = value.get("messages", [])
            contacts = value.get("contacts", [])

            for idx, message in enumerate(messages):
                waid = message.get("from")
                if not waid:
                    continue

                contact_name = waid
                if idx < len(contacts):
                    profile = contacts[idx].get("profile") or {}
                    contact_name = profile.get("name") or waid

                msg_type = message.get("type")
                texto = ""
                if msg_type == "text":
                    texto = (message.get("text") or {}).get("body", "")
                # Aqui podemos expandir para outros tipos (image, audio, etc) se necessário

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

    return JsonResponse({"status": "ok"})


