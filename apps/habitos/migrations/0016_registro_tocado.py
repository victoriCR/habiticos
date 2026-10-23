import apps.habitos.models
from django.db import migrations, models


class Migration(migrations.Migration):
    """Agrega "tocado" (cuándo se marcó de verdad) para el margen de 1 hora para deshacer.

    En dos pasos a propósito: primero sin valor por defecto, así los registros que ya
    existen quedan vacíos (= confirmados); después, el valor por defecto para los nuevos.
    En un solo paso, Django les pondría "ahora" a todos y se podrían deshacer una hora más.
    """

    dependencies = [
        ('habitos', '0015_alter_habito_identidad_and_more'),
    ]

    operations = [
        migrations.AddField(
            model_name='registro',
            name='tocado',
            field=models.DateTimeField(blank=True, null=True),
        ),
        migrations.AlterField(
            model_name='registro',
            name='tocado',
            field=models.DateTimeField(blank=True, default=apps.habitos.models.ahora, null=True),
        ),
    ]
