from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from django import forms

class AccessibleForm(forms.Form):
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)
        for name,field in self.fields.items():
            if name in {"username","email"}:
                field.widget.attrs.update({"autocomplete":name,"autocorrect":"off","autocapitalize":"none","spellcheck":"false"})
            elif name in {"password","confirmation"}:
                field.widget.attrs["autocomplete"]="current-password" if self.__class__.__name__=="LoginForm" else "new-password"

class RegistrationForm(AccessibleForm):
    username = forms.CharField(max_length=150)
    email = forms.EmailField()
    password = forms.CharField(widget=forms.PasswordInput, min_length=12)
    confirmation = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        data = super().clean()
        if data.get("password") != data.get("confirmation"):
            self.add_error("confirmation", "Passwords must match.")
        return data

class LoginForm(AccessibleForm):
    username = forms.CharField(max_length=150)
    password = forms.CharField(widget=forms.PasswordInput)

class RecoveryForm(AccessibleForm):
    email = forms.EmailField()

class PasswordForm(AccessibleForm):
    password = forms.CharField(widget=forms.PasswordInput, min_length=12)
    confirmation = forms.CharField(widget=forms.PasswordInput)

    def clean(self):
        data = super().clean()
        if data.get("password") != data.get("confirmation"):
            self.add_error("confirmation", "Passwords must match.")
        return data

class PreferencesForm(forms.Form):
    email_enabled = forms.BooleanField(required=False, label="Email me task reminders")
    display_timezone = forms.CharField(max_length=80, label="Time zone", help_text="For example, America/Los_Angeles")

    def clean_display_timezone(self):
        value = self.cleaned_data["display_timezone"]
        try:
            ZoneInfo(value)
        except ZoneInfoNotFoundError:
            raise forms.ValidationError("Enter a valid IANA time zone.")
        return value
