from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):
    initial = True
    dependencies = []
    operations = [
        migrations.CreateModel(
            name="EvaluationRun",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("total", models.PositiveIntegerField(default=0)),
                ("passed", models.PositiveIntegerField(default=0)),
            ],
            options={"ordering": ("-created_at", "-pk")},
        ),
        migrations.CreateModel(
            name="EvaluationResult",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("position", models.PositiveIntegerField()),
                ("question", models.TextField()),
                ("expected", models.TextField()),
                ("actual", models.TextField(blank=True)),
                ("source_ids", models.JSONField(default=list)),
                ("passed", models.BooleanField(default=False)),
                ("feedback", models.TextField(blank=True)),
                ("run", models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name="results", to="evaluation.evaluationrun")),
            ],
            options={"ordering": ("position", "pk")},
        ),
        migrations.AddConstraint(
            model_name="evaluationresult",
            constraint=models.UniqueConstraint(fields=("run", "position"), name="unique_eval_run_position"),
        ),
    ]
