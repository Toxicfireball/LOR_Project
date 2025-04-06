# accounts/views.py

from django.shortcuts import render, redirect
from django.contrib.auth import login
from .forms import RegistrationForm

def register(request):
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()         # Save the new user
            login(request, user)       # Log the user in immediately after registering
            return redirect('campaigns:campaign_list')  # Redirect to a campaign list (or wherever)
    else:
        form = RegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})
