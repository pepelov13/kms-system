from django import forms
from .models import UserAnswer

class UserAnswerForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.question = kwargs.pop('question')
        super().__init__(*args, **kwargs)
        # Limit answers to only those related to the given question
        self.fields['selected_answer'].queryset = self.question.answers.all()

    class Meta:
        model = UserAnswer
        fields = ['selected_answer']
