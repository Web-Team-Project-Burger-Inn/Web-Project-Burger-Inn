"""
Forms for BurgerInn
- User signup (with extra phone + address saved to UserProfile)
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import UserProfile

# =====================================================================
# SIGNUP FORM (USER + USERPROFILE)
# =====================================================================

class SignUpForm(UserCreationForm):
    """
    FEATURE: User registration form.

    Extends Django's built-in UserCreationForm to capture extra fields:
    - email   (stored on auth.User)
    - phone   (stored on UserProfile)
    - address (stored on UserProfile)

    The overridden `save()` method:
    - saves the User
    - then creates or updates the linked UserProfile with phone + address.
    """

    email = forms.EmailField(
        required=True,
        widget=forms.EmailInput(
            attrs={
                "placeholder": "Enter your email",
            }
        ),
    )
    phone = forms.CharField(
        label="Phone number",
        max_length=20,
        required=False,
        widget=forms.TextInput(
            attrs={
                "placeholder": "e.g. +230 5xxx xxxx",
            }
        ),
    )
    address = forms.CharField(
        label="Address",
        required=False,
        widget=forms.Textarea(
            attrs={
                "rows": 3,
                "placeholder": "Street, town, etc.",
            }
        ),
    )

    class Meta(UserCreationForm.Meta):
        model = User
        # NOTE: `phone` and `address` are extra form fields (not User model fields),
        # but we include them here so they appear in the form in the desired order.
        fields = (
            "username",
            "email",
            "phone",
            "address",
            "password1",
            "password2",
        )

    def save(self, commit=True):
        """
        Save the user and ensure the linked UserProfile is created/updated
        with the extra phone + address fields.
        """
        user = super().save(commit=False)

        # Persist email on the User model
        user.email = self.cleaned_data.get("email")

        if commit:
            user.save()

            # Create / update matching UserProfile with phone & address
            UserProfile.objects.update_or_create(
                user=user,
                defaults={
                    "phone": self.cleaned_data.get("phone", ""),
                    "address": self.cleaned_data.get("address", ""),
                },
            )

        return user
