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