from django.shortcuts import render
from django.contrib.auth.decorators import login_required

def home(request):
    """Landing page view."""
    return render(request, 'core/home.html')

@login_required
def dashboard(request):
    """Main dashboard view."""
    context = {
        'title': 'Dashboard',
        # We'll add more context data as we develop the functionality
    }
    return render(request, 'core/dashboard.html', context)