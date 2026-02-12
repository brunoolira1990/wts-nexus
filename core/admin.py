from django.contrib import admin
from .models import Atendimento, Cliente, Contato, Mensagem


@admin.register(Cliente)
class ClienteAdmin(admin.ModelAdmin):
    list_display = ("telefone", "nome")
    search_fields = ("telefone", "nome")


@admin.register(Atendimento)
class AtendimentoAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cliente",
        "departamento",
        "status",
        "data_inicio",
        "agente_responsavel",
    )
    list_filter = ("departamento", "status")
    list_editable = ("status",)
    raw_id_fields = ("cliente", "agente_responsavel")
    readonly_fields = ("data_inicio",)
    ordering = ("-data_inicio",)


@admin.register(Contato)
class ContatoAdmin(admin.ModelAdmin):
    list_display = ("nome", "waid", "atualizado_em")
    search_fields = ("nome", "waid")


@admin.register(Mensagem)
class MensagemAdmin(admin.ModelAdmin):
    list_display = ("contato", "texto_preview", "direcao", "status", "timestamp")
    list_filter = ("direcao", "status")

    def texto_preview(self, obj):
        return (obj.texto or "")[:50] + ("..." if len(obj.texto or "") > 50 else "")

    texto_preview.short_description = "Texto"
