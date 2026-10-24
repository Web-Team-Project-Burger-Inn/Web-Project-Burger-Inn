class ReviewForm(forms.ModelForm):
    """
    FEATURE: Customer review submission.

    Used on the Reviews page to submit feedback with:
    - name
    - gender
    - rating (1–5)
    - free-text comment
    """

    class Meta:
        model = Review
        fields = ["name", "gender", "rating", "comment"]
        widgets = {
            "name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Your name",
                }
            ),
            "gender": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "rating": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "comment": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 4,
                    "placeholder": "Tell us what you thought of BurgerInn…",
                }
            ),
        }