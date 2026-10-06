from django.shortcuts import render

def home(request):
    """Homepage — Part 6 এ full version আসবে।"""
    return render(request, 'website/home.html', {})