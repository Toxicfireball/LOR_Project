from django.shortcuts import render, redirect, get_object_or_404
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.urls import reverse
from django.contrib.contenttypes.models import ContentType
from django.forms import modelform_factory

from .forms import RegistrationForm
from .models import EmailVerification, UserEmail
from .utils import send_verification_email
from .utils import send_verification_email, EmailSendError

def register(request):
    """
    New users:
      - Save user
      - Create EmailVerification(purpose=signup)
      - Send email with /accounts/verify/<token>/
      - Show 'check your email' page (do NOT login yet)
    """
    if request.method == 'POST':
        form = RegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            UserEmail.objects.get_or_create(user=user)

            ev = EmailVerification.objects.create(
                user=user,
                email=user.email,
                purpose=EmailVerification.PURPOSE_SIGNUP
            )
            # register():
            verify_url = request.build_absolute_uri(
                reverse('accounts:verify_email', args=[str(ev.token)])
            )
            try:
                send_verification_email(user, user.email, verify_url=verify_url)
                return render(request, 'accounts/check_email.html', {
                    'email': user.email, 'verify_url': verify_url,
                })
            except EmailSendError as e:
                return render(request, 'accounts/check_email.html', {
                    'email': user.email, 'verify_url': verify_url, 'error': str(e),
                })

    else:
        form = RegistrationForm()
    return render(request, 'accounts/register.html', {'form': form})

@login_required
def request_verification(request):
    meta = getattr(request.user, "email_meta", None)
    if meta and meta.is_verified:
        messages.info(request, "Your email is already verified.")
        return redirect('campaigns:campaign_list')

    if request.method == "POST":
        ev = EmailVerification.objects.create(
            user=request.user,
            email=request.user.email,
            purpose=EmailVerification.PURPOSE_SIGNUP
        )
        verify_url = request.build_absolute_uri(
            reverse('accounts:verify_email', args=[str(ev.token)])
        )
        try:
            send_verification_email(request.user, request.user.email, verify_url=verify_url)
            return render(request, 'accounts/check_email.html', {
                'email': request.user.email, 'verify_url': verify_url,
            })
        except EmailSendError as e:
            return render(request, 'accounts/check_email.html', {
                'email': request.user.email, 'verify_url': verify_url, 'error': str(e),
            })


    return render(request, 'accounts/request_verification.html', {})

@login_required
def change_email(request):
    if request.method == "POST":
        new_email = (request.POST.get("new_email") or "").strip()
        if not new_email:
            messages.error(request, "Please enter a new email.")
            return redirect('accounts:change_email')

        ev = EmailVerification.objects.create(
            user=request.user,
            email=new_email,
            purpose=EmailVerification.PURPOSE_CHANGE
        )
        verify_url = request.build_absolute_uri(
            reverse('accounts:verify_email', args=[str(ev.token)])
        )
        try:
            send_verification_email(request.user, new_email, verify_url=verify_url)
            return render(request, 'accounts/check_email.html', {
                'email': new_email, 'verify_url': verify_url,
            })
        except EmailSendError as e:
            return render(request, 'accounts/check_email.html', {
                'email': new_email, 'verify_url': verify_url, 'error': str(e),
            })

    return render(request, 'accounts/change_email.html', {})

def verify_email(request, token):
    ev = get_object_or_404(EmailVerification, token=token, used_at__isnull=True)
    meta, _ = UserEmail.objects.get_or_create(user=ev.user)

    if ev.purpose == EmailVerification.PURPOSE_SIGNUP:
        meta.is_verified = True
        meta.save(update_fields=["is_verified"])
        ev.mark_used()
        login(request, ev.user)
        return render(request, 'accounts/verify_result.html', {
            'ok': True,
            'title': "Email verified",
            'message': "Your email has been verified. You are now signed in.",
        })

    elif ev.purpose == EmailVerification.PURPOSE_CHANGE:
        ev.user.email = ev.email
        ev.user.save(update_fields=["email"])
        meta.is_verified = True
        meta.save(update_fields=["is_verified"])
        ev.mark_used()
        return render(request, 'accounts/verify_result.html', {
            'ok': True,
            'title': "Email changed & verified",
            'message': f"Your email has been changed to {ev.email} and verified.",
        })

    return render(request, 'accounts/verify_result.html', {
        'ok': False,
        'title': "Invalid verification",
        'message': "This verification link is not valid.",
    })

@login_required
def submission_list(request):
    subs = request.user.submissions.order_by('-created_at')
    return render(request, 'accounts/submission_list.html', {'subs': subs})


