
from django.shortcuts import render


def about_page(request):
    return render(request, 'about/about.html')


def profile_page(request):
    return render(request, 'about/profile.html')
