from django.shortcuts import render
from datetime import datetime

def home(request):
    """
    Render the home page with template
    """
    context = {
        'current_time': datetime.now().strftime("%B %d, %Y %I:%M %p")
    }
    return render(request, 'myapp/home.html', context)