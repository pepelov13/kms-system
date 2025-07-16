from django.contrib import admin
from .models import UserAnswer, AssessmentResult

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ['user', 'assessment', 'question', 'selected_answer']
    search_fields = ['user__username', 'question__question_text']
    list_filter = []

@admin.register(AssessmentResult)
class AssessmentResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'assessment', 'score', 'status']
    search_fields = ['user__username', 'assessment__title']
    list_filter = ['status']
