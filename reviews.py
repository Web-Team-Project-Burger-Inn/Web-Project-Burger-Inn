from django.db import models
from django.contrib import messages
from django.shortcuts import redirect, render
from django.urls import reverse

from .forms import ReviewForm


class Review(models.Model):
    """
    FEATURE: Customer reviews.

    - Collected via Reviews page (ReviewForm).
    - Gender + rating choice used for small visual touches on UI.
    - Sorted newest first.
    """

    GENDER_CHOICES = [
        ("Male", "Male"),
        ("Female", "Female"),
        ("Other", "Other"),
    ]

    RATING_CHOICES = [
        (1, "⭐☆☆☆☆"),
        (2, "⭐⭐☆☆☆"),
        (3, "⭐⭐⭐☆☆"),
        (4, "⭐⭐⭐⭐☆"),
        (5, "⭐⭐⭐⭐⭐"),
    ]

    name = models.CharField(max_length=100)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES)
    rating = models.IntegerField(choices=RATING_CHOICES)
    comment = models.TextField()
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"{self.name} ({self.rating}★)"

def review_list(request):
    if request.method == "POST":
        if not request.user.is_authenticated:
            messages.error(request, "You must be logged in to submit a review.")
            return redirect(f"{reverse('login')}?next={reverse('reviews')}")

        form = ReviewForm(request.POST)
        if form.is_valid():
            form.save()
            return redirect("reviews")
    else:
        form = ReviewForm()

    reviews = Review.objects.all()
    return render(request, "pages/reviews.html", {"reviews": reviews, "form": form})

    messages.success(request, "Thank you for your review! 🍕")
    messages.error(request, "Please fix the errors below.")