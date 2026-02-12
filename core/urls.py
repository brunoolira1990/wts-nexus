from django.urls import path

from . import views

app_name = "core"

urlpatterns = [
    path("", views.dashboard, name="dashboard"),
    path("contato/<int:contato_id>/", views.dashboard, name="dashboard_contato"),
    path("webhook/whatsapp/", views.whatsapp_webhook, name="whatsapp_webhook"),
]


