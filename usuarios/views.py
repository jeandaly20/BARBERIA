import random

from django.conf import settings
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token as google_id_token
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.throttling import ScopedRateThrottle
from rest_framework.views import APIView
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView

from .models import CodigoRecuperacion, Usuario
from .notificaciones import enviar_email_codigo_recuperacion
from .serializers import (
    ConfirmarRecuperacionSerializer,
    GoogleLoginSerializer,
    RegistroSerializer,
    SolicitarCodigoSerializer,
    UsuarioSerializer,
)


class RegistroView(generics.CreateAPIView):
    queryset = Usuario.objects.all()
    serializer_class = RegistroSerializer
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class LoginView(TokenObtainPairView):
    """Igual que TokenObtainPairView, pero con límite de intentos para frenar fuerza bruta."""

    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"


class MiPerfilView(generics.RetrieveAPIView):
    serializer_class = UsuarioSerializer
    permission_classes = [permissions.IsAuthenticated]

    def get_object(self):
        return self.request.user


class SolicitarCodigoRecuperacionView(APIView):
    """Envía un código de 6 dígitos al correo si existe una cuenta con ese email.

    Siempre responde 200 con el mismo mensaje genérico, exista o no la cuenta, para no revelar
    qué correos están registrados (solo cambia si efectivamente se envía el email).
    """

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = SolicitarCodigoSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]

        if Usuario.objects.filter(email=email).exists():
            codigo = f"{random.randint(0, 999999):06d}"
            CodigoRecuperacion.objects.create(email=email, codigo=codigo)
            enviar_email_codigo_recuperacion(email, codigo)

        return Response({"detail": "Si el correo está registrado, te enviamos un código."})


class ConfirmarRecuperacionView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = ConfirmarRecuperacionSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        codigo = serializer.validated_data["codigo"]
        nueva_password = serializer.validated_data["nueva_password"]

        registro = (
            CodigoRecuperacion.objects.filter(email=email, codigo=codigo, usado=False)
            .order_by("-creado_en")
            .first()
        )
        if registro is None or registro.expirado():
            return Response({"detail": "Código inválido o expirado."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            usuario = Usuario.objects.get(email=email)
        except Usuario.DoesNotExist:
            return Response({"detail": "Código inválido o expirado."}, status=status.HTTP_400_BAD_REQUEST)

        usuario.set_password(nueva_password)
        usuario.save(update_fields=["password"])
        registro.usado = True
        registro.save(update_fields=["usado"])

        return Response({"detail": "Contraseña actualizada."})


class GoogleLoginView(APIView):
    """Verifica el ID token que entrega Google Identity Services en el navegador y devuelve
    los mismos tokens JWT que el login normal (crea la cuenta si es la primera vez)."""

    permission_classes = [permissions.AllowAny]
    throttle_classes = [ScopedRateThrottle]
    throttle_scope = "auth"

    def post(self, request):
        serializer = GoogleLoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        credential = serializer.validated_data["credential"]

        try:
            idinfo = google_id_token.verify_oauth2_token(
                credential, google_requests.Request(), settings.GOOGLE_CLIENT_ID
            )
        except ValueError:
            return Response({"detail": "Token de Google inválido."}, status=status.HTTP_400_BAD_REQUEST)

        if not idinfo.get("email_verified"):
            return Response({"detail": "El email de Google no está verificado."}, status=status.HTTP_400_BAD_REQUEST)

        email = idinfo["email"]
        usuario, creado = Usuario.objects.get_or_create(
            email=email,
            defaults={"nombre": idinfo.get("name", ""), "rol": Usuario.ROL_CLIENTE},
        )
        if creado:
            usuario.set_unusable_password()
            usuario.save(update_fields=["password"])

        refresh = RefreshToken.for_user(usuario)
        return Response({"access": str(refresh.access_token), "refresh": str(refresh)})
