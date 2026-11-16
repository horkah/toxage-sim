"""The visitor whose space holds a data set in a demo installation."""
from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [("explorer", "0002_course_fields_same_as_base")]

    operations = [
        migrations.AddField(
            model_name="dataset", name="owner",
            field=models.CharField(blank=True, db_index=True, default="", max_length=16)),
    ]
