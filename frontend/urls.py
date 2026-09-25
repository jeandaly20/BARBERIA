from django.urls import path

from . import views

app_name = "frontend"

urlpatterns = [
    path("login/", views.LoginView.as_view(), name="login"),
    path("servicios/", views.ServiciosView.as_view(), name="servicios"),
    path("agenda/", views.AgendaView.as_view(), name="agenda"),
    path("pago/", views.PagoView.as_view(), name="pago"),
    path("citas/", views.MisCitasView.as_view(), name="mis_citas"),
    path("perfil/", views.PerfilView.as_view(), name="perfil"),
]
