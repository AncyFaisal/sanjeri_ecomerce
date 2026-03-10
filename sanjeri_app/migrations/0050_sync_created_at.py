from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('sanjeri_app', '0049_temp_remove_created_at'),
    ]

    operations = [
        migrations.AddField(
            model_name='offerapplication',
            name='created_at',
            field=models.DateTimeField(auto_now_add=True, default=None),
            preserve_default=False,
        ),
    ]