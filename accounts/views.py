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
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.contenttypes.models import ContentType
from django.contrib.auth.decorators import login_required
from django.forms import modelform_factory
from django.urls import reverse
from .models import Submission

@login_required
def submission_list(request):
    """Show a user their own submissions."""
    subs = request.user.submissions.order_by('-created_at')
    return render(request, 'accounts/submission_list.html', {'subs': subs})

@login_required
def submit_model(request, app_label, model_name, pk=None):
    """
    Generic create/edit submission.
      - if pk is passed: it's an edit_submission
      - else: new object
    """
    # 1) Resolve the model
    from django.apps import apps
    model = apps.get_model(app_label, model_name)
    ct    = ContentType.objects.get_for_model(model)

    # 2) Build a ModelForm (exclude auto fields)
    FormClass = modelform_factory(model, exclude=['id', 'created_at', 'updated_at'])

    instance = None
    if pk:
        instance = get_object_or_404(model, pk=pk)

    if request.method == 'POST':
        form = FormClass(request.POST, request.FILES, instance=instance)
        if form.is_valid():
            payload = {}
            for field, val in form.cleaned_data.items():
                # Handle FileFields: upload now so path exists
                if hasattr(val, 'url'):
                    payload[field] = val  # file instance
                else:
                    payload[field] = val
            # Save a Submission record
            Submission.objects.create(
                submitter    = request.user,
                content_type = ct,
                object_id    = pk,
                data         = payload
            )
            return redirect('accounts:submission_list')
    else:
        form = FormClass(instance=instance)

    # 3) Render a template
    return render(request, 'accounts/submit_model.html', {
        'form':      form,
        'model_name': model._meta.verbose_name.title(),
        'is_edit':    pk is not None,
    })
