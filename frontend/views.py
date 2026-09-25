from django.conf import settings
from django.views.generic import TemplateView


class LoginView(TemplateView):
    template_name = "frontend/login.html"

    def get_context_data(self, **kwargs):
        context = super().get_context_data(**kwargs)
        context["google_client_id"] = settings.GOOGLE_CLIENT_ID
        return context


class ServiciosView(TemplateView):
    template_name = "frontend/servicios.html"


class AgendaView(TemplateView):
    template_name = "frontend/agenda.html"


class PagoView(TemplateView):
    template_name = "frontend/pago.html"


class MisCitasView(TemplateView):
    template_name = "frontend/mis_citas.html"


class PerfilView(TemplateView):
    template_name = "frontend/perfil.html"
