"""Persistent evaluation history, separate from ordinary assistant usage logs."""
from django.db import models


class EvaluationRun(models.Model):
    created_at = models.DateTimeField(auto_now_add=True)
    total = models.PositiveIntegerField(default=0)
    passed = models.PositiveIntegerField(default=0)

    class Meta:
        ordering = ("-created_at", "-pk")

    @property
    def failed(self):
        return self.total - self.passed

    @property
    def accuracy(self):
        return round(100 * self.passed / self.total) if self.total else 0

    def __str__(self):
        return f"Evaluation #{self.pk} ({self.passed}/{self.total})"


class EvaluationResult(models.Model):
    run = models.ForeignKey(EvaluationRun, on_delete=models.CASCADE, related_name="results")
    position = models.PositiveIntegerField()
    question = models.TextField()
    expected = models.TextField()
    actual = models.TextField(blank=True)
    source_ids = models.JSONField(default=list)
    passed = models.BooleanField(default=False)
    feedback = models.TextField(blank=True)

    class Meta:
        ordering = ("position", "pk")
        constraints = [models.UniqueConstraint(fields=("run", "position"), name="unique_eval_run_position")]

    def __str__(self):
        return f"{self.question[:75]} ({'pass' if self.passed else 'fail'})"
