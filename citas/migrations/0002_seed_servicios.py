from decimal import Decimal

from django.db import migrations


def crear_datos_iniciales(apps, schema_editor):
    Servicio = apps.get_model("citas", "Servicio")
    Extra = apps.get_model("citas", "Extra")

    Servicio.objects.create(nombre="Corte clásico", precio=Decimal("3.50"), duracion_minutos=30)
    Servicio.objects.create(
        nombre="Corte fade", precio=Decimal("4.00"), duracion_minutos=40, precio_desde=True
    )

    Extra.objects.create(nombre="Diseño freestyle", precio=Decimal("2.00"), duracion_minutos=15)
    Extra.objects.create(nombre="Cejas", precio=Decimal("1.50"), duracion_minutos=10)
    Extra.objects.create(nombre="Barba", precio=Decimal("2.50"), duracion_minutos=20)


def eliminar_datos_iniciales(apps, schema_editor):
    Servicio = apps.get_model("citas", "Servicio")
    Extra = apps.get_model("citas", "Extra")
    Servicio.objects.filter(nombre__in=["Corte clásico", "Corte fade"]).delete()
    Extra.objects.filter(nombre__in=["Diseño freestyle", "Cejas", "Barba"]).delete()


class Migration(migrations.Migration):

    dependencies = [
        ("citas", "0001_initial"),
    ]

    operations = [
        migrations.RunPython(crear_datos_iniciales, eliminar_datos_iniciales),
    ]
