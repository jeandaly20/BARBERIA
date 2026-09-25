from django.urls import path
from rest_framework_simplejwt.views import TokenRefreshView

from .views import (
    ConfirmarRecuperacionView,
    GoogleLoginView,
    LoginView,
    MiPerfilView,
    RegistroView,
    SolicitarCodigoRecuperacionView,
)

urlpatterns = [
    path("registro/", RegistroView.as_view(), name="registro"),
    path("login/", LoginView.as_view(), name="token_obtain_pair"),
    path("google/", GoogleLoginView.as_view(), name="google_login"),
    path("refresh/", TokenRefreshView.as_view(), name="token_refresh"),
    path("mi-perfil/", MiPerfilView.as_view(), name="mi_perfil"),
    path("recuperar/solicitar/", SolicitarCodigoRecuperacionView.as_view(), name="recuperar_solicitar"),
    path("recuperar/confirmar/", ConfirmarRecuperacionView.as_view(), name="recuperar_confirmar"),
]
