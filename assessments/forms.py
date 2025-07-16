from django import forms
from django.forms import inlineformset_factory
from django.contrib.auth import get_user_model
from .models import Assessment, Question, Answer

User = get_user_model()

class AssessmentForm(forms.ModelForm):
    class Meta:
        model = Assessment
        fields = ['title', 'description', 'passing_score', 'time_limit', 'allow_retake', 'max_retakes']
        widgets = {
            'description': forms.Textarea(attrs={'rows': 3}),
        }

class QuestionForm(forms.ModelForm):
    class Meta:
        model = Question
        fields = ['text']

class AnswerForm(forms.ModelForm):
    class Meta:
        model = Answer
        fields = ['text', 'is_correct']

QuestionFormSet = inlineformset_factory(
    Assessment, Question, form=QuestionForm, extra=1, can_delete=True
)

AnswerFormSet = inlineformset_factory(
    Question, Answer, form=AnswerForm, extra=1, can_delete=True
)

# ✅ Rewritten AssignmentForm: assign to multiple employees at once
class AssignmentForm(forms.Form):
    assessment = forms.ModelChoiceField(
        queryset=Assessment.objects.all(),
        label="Select Assessment",
        widget=forms.Select(attrs={'class': 'form-control'})
    )
    employees = forms.ModelMultipleChoiceField(
        queryset=User.objects.filter(is_staff=False),
        label="Select Employees",
        widget=forms.CheckboxSelectMultiple
    )