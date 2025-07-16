from django.contrib import admin
from .models import Assessment, Question, Answer

# Inline for managing answers directly within each question
class AnswerInline(admin.TabularInline):
    model = Answer
    extra = 2  # Number of empty answer forms shown initially
    min_num = 1
    verbose_name = "Answer"
    verbose_name_plural = "Answers"

@admin.register(Assessment)
class AssessmentAdmin(admin.ModelAdmin):
    list_display = ['title', 'created_by_username', 'passing_score']
    search_fields = ['title']
    list_filter = ['created_by']
    fields = ['title', 'description', 'created_by', 'passing_score']

    def created_by_username(self, obj):
        return obj.created_by.username
    created_by_username.admin_order_field = 'created_by'
    created_by_username.short_description = 'Created By'


@admin.register(Question)
class QuestionAdmin(admin.ModelAdmin):
    list_display = ['text', 'get_correct_answer', 'assessment']
    list_filter = ['assessment']
    search_fields = ['text']
    inlines = [AnswerInline]  # ✅ Add answers inline when editing a question

    def get_correct_answer(self, obj):
        correct = obj.answers.filter(is_correct=True).first()
        return correct.text if correct else "—"
    get_correct_answer.short_description = 'Correct Answer'
