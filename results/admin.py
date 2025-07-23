from django.contrib import admin
from .models import UserAnswer, AssessmentResult

@admin.register(UserAnswer)
class UserAnswerAdmin(admin.ModelAdmin):
    list_display = ['user', 'assessment', 'question', 'get_selected_answers']
    search_fields = ['user__username', 'question__text']  # Feldname war falsch: question_text → text
    list_filter = []

    def get_selected_answers(self, obj):
        return ", ".join([a.text for a in obj.selected_answers.all()])
    get_selected_answers.short_description = 'Selected Answers'

@admin.register(AssessmentResult)
class AssessmentResultAdmin(admin.ModelAdmin):
    list_display = ['user', 'assessment', 'score', 'status']
    search_fields = ['user__username', 'assessment__title']
    list_filter = ['status']
