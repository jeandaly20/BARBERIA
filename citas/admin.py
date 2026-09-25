from django.contrib import admin

from .models import Extra, Servicio


@admin.register(Servicio)
class ServicioAdmin(admin.ModelAdmin):
    list_display = ("nombre", "precio", "duracion_minutos", "precio_desde", "activo")
    list_filter = ("activo",)


@admin.register(Extra)
class ExtraAdmin(admin.ModelAdmin):
    list_display = ("nombre", "precio", "duracion_minutos", "activo")
    list_filter = ("activo",)
