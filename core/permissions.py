from rest_framework import permissions


class EsPropietario(permissions.BasePermission):
    """Solo el dueño de la barbería (rol=propietario) puede pasar."""

    def has_permission(self, request, view):
        return bool(
            request.user
            and request.user.is_authenticated
            and request.user.rol == request.user.ROL_PROPIETARIO
        )


class EsClienteDuenoOPropietario(permissions.BasePermission):
    """A nivel de objeto: el propietario ve/gestiona cualquier Cita; un cliente solo la suya."""

    def has_object_permission(self, request, view, obj):
        if request.user.rol == request.user.ROL_PROPIETARIO:
            return True
        return obj.cliente_id == request.user.id
