from django import forms
from django.contrib.auth import get_user_model

User = get_user_model()

class RegistrationForm(forms.ModelForm):
    password = forms.CharField(widget=forms.PasswordInput(attrs={"class": "form-control"}))
    password2 = forms.CharField(label="Confirm Password", widget=forms.PasswordInput(attrs={"class": "form-control"}))

    class Meta:
        model = User
        fields = ("username", "email", "password")
        widgets = {
            "username": forms.TextInput(attrs={"class": "form-control"}),
            "email": forms.EmailInput(attrs={"class": "form-control"}),
        }

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if User.objects.filter(email__iexact=email).exists():
            raise forms.ValidationError("This email is already in use.")
        return email

    def clean(self):
        cd = super().clean()
        if cd.get("password") != cd.get("password2"):
            self.add_error("password2", "Passwords do not match.")
        return cd

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = (self.cleaned_data["email"] or "").strip().lower()
        user.set_password(self.cleaned_data["password"])
        if commit:
            user.save()
        return user
