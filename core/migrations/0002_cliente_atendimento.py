# Generated migration for Cliente and Atendimento

import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ("core", "0001_initial"),
    ]

    operations = [
        migrations.CreateModel(
            name="Cliente",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("telefone", models.CharField(max_length=32, unique=True)),
                ("nome", models.CharField(blank=True, max_length=255)),
            ],
            options={
                "verbose_name": "Cliente",
                "verbose_name_plural": "Clientes",
                "ordering": ("nome", "telefone"),
            },
        ),
        migrations.CreateModel(
            name="Atendimento",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "departamento",
                    models.CharField(
                        choices=[
                            ("COMERCIAL", "Comercial"),
                            ("FINANCEIRO", "Financeiro"),
                            ("TECNICO", "Técnico"),
                            ("SEM_DEPARTAMENTO", "Sem departamento"),
                        ],
                        default="SEM_DEPARTAMENTO",
                        max_length=20,
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("AGUARDANDO", "Aguardando"),
                            ("EM_ATENDIMENTO", "Em atendimento"),
                            ("FINALIZADO", "Finalizado"),
                        ],
                        default="AGUARDANDO",
                        max_length=20,
                    ),
                ),
                ("data_inicio", models.DateTimeField(auto_now_add=True)),
                (
                    "agente_responsavel",
                    models.ForeignKey(
                        blank=True,
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="atendimentos_agente",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "cliente",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="atendimentos",
                        to="core.cliente",
                    ),
                ),
            ],
            options={
                "verbose_name": "Atendimento",
                "verbose_name_plural": "Atendimentos",
                "ordering": ("-data_inicio",),
            },
        ),
    ]
