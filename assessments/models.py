from django.db import models
from django.core.validators import MinValueValidator
from django.conf import settings
from django.utils import timezone


class Assessment(models.Model):
    title = models.CharField(max_length=255)
    description = models.TextField(blank=True)
    created_by = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='created_assessments')
    created_at = models.DateTimeField(auto_now_add=True)
    duration_minutes = models.PositiveIntegerField(default=15)
    passing_score = models.PositiveIntegerField(default=80, help_text="Minimum score (in %) required to pass this assessment.")
    allow_retake = models.BooleanField(default=False, help_text="Allow employees to retake this assessment.")
    max_retakes = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Maximum number of retakes allowed (leave blank for unlimited)."
    )
    time_limit = models.PositiveIntegerField(
        null=True, blank=True,
        help_text="Time limit in minutes (optional). Leave blank for no time limit.",
        validators=[MinValueValidator(1)]
    )

    def __str__(self):
        return self.title



class Question(models.Model):
    assessment = models.ForeignKey(Assessment, related_name='questions', on_delete=models.CASCADE)
    text = models.CharField(max_length=500)
    is_multiple_choice = models.BooleanField(default=False)  # ✅ NEW

    def __str__(self):
        return self.text


class Answer(models.Model):
    question = models.ForeignKey(Question, related_name='answers', on_delete=models.CASCADE)
    text = models.CharField(max_length=255)
    is_correct = models.BooleanField(default=False)

    def __str__(self):
        return f"{self.text} ({'Correct' if self.is_correct else 'Incorrect'})"


class Assignment(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    employee = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, limit_choices_to={'is_staff': False})
    assigned_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        unique_together = ('assessment', 'employee')

    def __str__(self):
        return f"{self.assessment.title} → {self.employee.username}"
