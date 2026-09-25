from django.db import migrations


def actualizar_duraciones(apps, schema_editor):
    Servicio = apps.get_model("citas", "Servicio")
    Servicio.objects.all().update(duracion_minutos=40)


def revertir_duraciones(apps, schema_editor):
    Servicio = apps.get_model("citas", "Servicio")
    duraciones_originales = {
        "Corte clásico": 30,
        "Corte fade": 40,
    }
    for nombre, minutos in duraciones_originales.items():
        Servicio.objects.filter(nombre=nombre).update(duracion_minutos=minutos)


class Migration(migrations.Migration):

    dependencies = [
        ("citas", "0004_extras_a_un_dolar"),
    ]

    operations = [
        migrations.RunPython(actualizar_duraciones, revertir_duraciones),
    ]
