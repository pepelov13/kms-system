from django import forms
from .models import UserAnswer

class UserAnswerForm(forms.ModelForm):
    def __init__(self, *args, **kwargs):
        self.question = kwargs.pop('question')
        super().__init__(*args, **kwargs)

        # Nur Antworten dieser Frage anzeigen
        self.fields['selected_answers'].queryset = self.question.answers.all()

        # Widget für Mehrfachauswahl (Checkboxen)
        self.fields['selected_answers'].widget = forms.CheckboxSelectMultiple()

    class Meta:
        model = UserAnswer
        fields = ['selected_answers']