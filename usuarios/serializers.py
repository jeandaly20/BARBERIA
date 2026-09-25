from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

from .models import Usuario


class SolicitarCodigoSerializer(serializers.Serializer):
    email = serializers.EmailField()


class ConfirmarRecuperacionSerializer(serializers.Serializer):
    email = serializers.EmailField()
    codigo = serializers.CharField(max_length=6, min_length=6)
    nueva_password = serializers.CharField(write_only=True, validators=[validate_password])


class GoogleLoginSerializer(serializers.Serializer):
    credential = serializers.CharField()


class RegistroSerializer(serializers.ModelSerializer):
    password = serializers.CharField(write_only=True, validators=[validate_password])

    class Meta:
        model = Usuario
        fields = ["id", "email", "nombre", "telefono", "password"]

    def create(self, validated_data):
        return Usuario.objects.create_user(rol=Usuario.ROL_CLIENTE, **validated_data)


class UsuarioSerializer(serializers.ModelSerializer):
    class Meta:
        model = Usuario
        fields = ["id", "email", "nombre", "telefono", "rol"]
        read_only_fields = ["rol"]
