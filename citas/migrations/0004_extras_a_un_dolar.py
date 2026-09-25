from decimal import Decimal

from django.db import migrations


def actualizar_precios(apps, schema_editor):
    Extra = apps.get_model("citas", "Extra")
    Extra.objects.all().update(precio=Decimal("1.00"))


def revertir_precios(apps, schema_editor):
    Extra = apps.get_model("citas", "Extra")
    precios_originales = {
        "Diseño freestyle": Decimal("2.00"),
        "Cejas": Decimal("1.50"),
        "Barba": Decimal("2.50"),
    }
    for nombre, precio in precios_originales.items():
        Extra.objects.filter(nombre=nombre).update(precio=precio)


class Migration(migrations.Migration):

    dependencies = [
        ("citas", "0003_cita"),
    ]

    operations = [
        migrations.RunPython(actualizar_precios, revertir_precios),
    ]
