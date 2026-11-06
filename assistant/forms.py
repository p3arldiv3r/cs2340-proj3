from django import forms

class QuestionForm(forms.Form):
    question = forms.CharField(max_length=1000, label='Your question', strip=True,
        widget=forms.Textarea(attrs={'rows': 3, 'aria-describedby': 'question-help',
            'placeholder': 'Ask about social connection, groups, or activities...'}))
