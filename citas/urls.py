from django.urls import path
from rest_framework.routers import DefaultRouter

from .views import CitaViewSet, DisponibilidadView, ExtraViewSet, ServicioViewSet

router = DefaultRouter()
router.register("servicios", ServicioViewSet, basename="servicio")
router.register("extras", ExtraViewSet, basename="extra")
router.register("citas", CitaViewSet, basename="cita")

urlpatterns = [
    path("disponibilidad/", DisponibilidadView.as_view(), name="disponibilidad"),
] + router.urls
