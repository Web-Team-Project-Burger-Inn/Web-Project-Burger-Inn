"""
Forms for BurgerInn.

Covers:
- Reservation / checkout details (+ optional deal code)
- Customer reviews
- User signup (with extra phone + address saved to UserProfile)
"""

from django import forms
from django.contrib.auth.forms import UserCreationForm
from django.contrib.auth.models import User

from .models import Reservation, Review, UserProfile


# =====================================================================
# RESERVATION / CHECKOUT FORM
# =====================================================================

class ReservationForm(forms.ModelForm):
    """
    FEATURE: Checkout / reservation form.

    - Backs the Reservation model for storing order details.
    - Adds an extra `deal_code` field that is NOT part of the model.
      The view (`checkout_view`) reads this from `cleaned_data`
      and applies the discount logic manually.
    """

    # Extra field that is NOT in the Reservation model
    deal_code = forms.CharField(
        required=False,
        label="Deal code",
        widget=forms.TextInput(
            attrs={
                "class": "form-control",
                "placeholder": "Optional – enter your deal code (e.g. MARGH500)",
            }
        ),
    )

    class Meta:
        model = Reservation
        # Model-backed fields that will be saved on Reservation
        fields = [
            "full_name",
            "phone",
            "email",
            "order_type",
            "address",
            "postal_code",
            "store_location",
            # NOTE: deal_code is intentionally NOT listed here,
            #       because it is not a model field.
        ]
        widgets = {
            "full_name": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "Your full name",
                }
            ),
            "phone": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. 5xxxxxxx",
                }
            ),
            "email": forms.EmailInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "you@example.com",
                }
            ),
            "order_type": forms.Select(
                attrs={
                    "class": "form-select",
                }
            ),
            "address": forms.Textarea(
                attrs={
                    "class": "form-control",
                    "rows": 3,
                    "placeholder": "Delivery address",
                }
            ),
            "postal_code": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. 742CU001",
                }
            ),
            "store_location": forms.TextInput(
                attrs={
                    "class": "form-control",
                    "placeholder": "e.g. Port Louis, Curepipe…",
                }
            ),
        }


# =====================================================================
# REVIEWS FORM
# =====================================================================

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
