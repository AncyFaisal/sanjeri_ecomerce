from django.db import migrations, models

class Migration(migrations.Migration):
    dependencies = [
        ('sanjeri_app', '0043_alter_offerapplication_options'),
    ]

    operations = [
        migrations.AddField(
            model_name='productoffer',
            name='discount_percentage',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name='productoffer',
            name='max_discount',
            field=models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='productoffer',
            name='usage_limit',
            field=models.IntegerField(default=0, help_text='0 = unlimited'),
        ),
        migrations.AddField(
            model_name='categoryoffer',
            name='discount_percentage',
            field=models.DecimalField(decimal_places=2, default=0, max_digits=5),
        ),
        migrations.AddField(
            model_name='categoryoffer',
            name='max_discount',
            field=models.DecimalField(decimal_places=2, max_digits=10, null=True, blank=True),
        ),
        migrations.AddField(
            model_name='categoryoffer',
            name='usage_limit',
            field=models.IntegerField(default=0, help_text='0 = unlimited'),
        ),
    ]