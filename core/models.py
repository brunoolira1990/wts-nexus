from __future__ import annotations

from django.conf import settings
from django.db import models


class Cliente(models.Model):
    """Cliente identificado pelo telefone (ex: 551199999999)."""
    telefone = models.CharField(max_length=32, unique=True)
    nome = models.CharField(max_length=255, blank=True)

    class Meta:
        verbose_name = "Cliente"
        verbose_name_plural = "Clientes"
        ordering = ("nome", "telefone")

    def __str__(self) -> str:
        return f"{self.nome or self.telefone} ({self.telefone})"


class Atendimento(models.Model):
    class Departamento(models.TextChoices):
        COMERCIAL = "COMERCIAL", "Comercial"
        FINANCEIRO = "FINANCEIRO", "Financeiro"
        TECNICO = "TECNICO", "Técnico"
        SEM_DEPARTAMENTO = "SEM_DEPARTAMENTO", "Sem departamento"

    class Status(models.TextChoices):
        AGUARDANDO = "AGUARDANDO", "Aguardando"
        EM_ATENDIMENTO = "EM_ATENDIMENTO", "Em atendimento"
        FINALIZADO = "FINALIZADO", "Finalizado"

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name="atendimentos",
    )
    departamento = models.CharField(
        max_length=20,
        choices=Departamento.choices,
        default=Departamento.SEM_DEPARTAMENTO,
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.AGUARDANDO,
    )
    data_inicio = models.DateTimeField(auto_now_add=True)
    agente_responsavel = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="atendimentos_agente",
    )

    class Meta:
        verbose_name = "Atendimento"
        verbose_name_plural = "Atendimentos"
        ordering = ("-data_inicio",)

    def __str__(self) -> str:
        return f"#{self.pk} {self.cliente} - {self.get_departamento_display()} ({self.get_status_display()})"


class Contato(models.Model):
    nome = models.CharField(max_length=255)
    waid = models.CharField("WAID", max_length=32, unique=True)
    ultima_mensagem = models.TextField(blank=True)
    atualizado_em = models.DateTimeField(auto_now=True)
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Contato"
        verbose_name_plural = "Contatos"
        ordering = ("-atualizado_em",)

    def __str__(self) -> str:
        return f"{self.nome} ({self.waid})"


class Mensagem(models.Model):
    class Direcao(models.TextChoices):
        ENTRADA = "in", "Entrada"
        SAIDA = "out", "Saída"

    class Status(models.TextChoices):
        ENFILEIRADA = "queued", "Enfileirada"
        ENVIADA = "sent", "Enviada"
        ENTREGUE = "delivered", "Entregue"
        LIDA = "read", "Lida"
        FALHA = "failed", "Falha"

    contato = models.ForeignKey(
        Contato,
        on_delete=models.CASCADE,
        related_name="mensagens",
    )
    texto = models.TextField()
    direcao = models.CharField(
        max_length=3,
        choices=Direcao.choices,
    )
    status = models.CharField(
        max_length=16,
        choices=Status.choices,
        default=Status.ENFILEIRADA,
    )
    timestamp = models.DateTimeField(db_index=True)
    meta_message_id = models.CharField(
        max_length=128,
        blank=True,
        help_text="ID da mensagem na API do WhatsApp (Meta)",
    )
    criado_em = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Mensagem"
        verbose_name_plural = "Mensagens"
        ordering = ("timestamp", "id")

    def __str__(self) -> str:
        prefix = ">>" if self.direcao == self.Direcao.SAIDA else "<<"
        return f"{prefix} {self.contato}: {self.texto[:40]}"

