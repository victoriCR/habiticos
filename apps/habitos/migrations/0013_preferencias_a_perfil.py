from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):
    """Preferencias pasa a llamarse Perfil (ahora también guarda @usuario y frase).

    RenameModel conserva la tabla y sus datos; borrar y crear otra los perdería.
    """

    dependencies = [
        ('habitos', '0012_papelera'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.RenameModel(old_name='Preferencias', new_name='Perfil'),
    ]
