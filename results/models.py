from django.db import models
from django.conf import settings
from assessments.models import Assessment, Question, Answer


class AssessmentResult(models.Model):
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE)
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(
        max_length=50,
        choices=[('Not Started', 'Not Started'), ('In Progress', 'In Progress'), ('Completed', 'Completed')]
    )
    score = models.DecimalField(max_digits=5, decimal_places=2, null=True, blank=True)
    submitted_at = models.DateTimeField(null=True, blank=True)
    start_time = models.DateTimeField(null=True, blank=True)
    retake_count = models.PositiveIntegerField(default=0)
    
    def __str__(self):
        return f"{self.user.username} - {self.assessment.title} - {self.score}"

    @property
    def user_answers(self):
        return self.user.user_answers.filter(assessment=self.assessment)


class UserAnswer(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name='user_answers')
    assessment = models.ForeignKey(Assessment, on_delete=models.CASCADE, related_name='user_answers')
    question = models.ForeignKey(Question, on_delete=models.CASCADE, related_name='user_answers')
    selected_answers = models.ManyToManyField(Answer)
    answered_at = models.DateTimeField(auto_now_add=True)

    def is_correct(self):
        return self.selected_answer.is_correct

    class Meta:
        unique_together = ('user', 'question', 'assessment')  # One answer per question per user

    def __str__(self):
        return f"{self.user.username} → Q: {self.question.text[:50]} → A: {self.selected_answer.text[:50]}"
