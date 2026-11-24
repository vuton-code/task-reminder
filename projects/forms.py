from django import forms

class ProjectForm(forms.Form):
    name = forms.CharField(max_length=100, label="Project name")
    mutation_key = forms.UUIDField(widget=forms.HiddenInput)

class InvitationForm(forms.Form):
    email = forms.EmailField(label="Invite by email")
    mutation_key = forms.UUIDField(widget=forms.HiddenInput)


class DeleteProjectForm(forms.Form):
    confirmation = forms.CharField(label="Project name", max_length=100, strip=False)
    version = forms.IntegerField(widget=forms.HiddenInput)

    def __init__(self, *args, project, **kwargs):
        super().__init__(*args, **kwargs)
        self.project = project
        self.fields["confirmation"].help_text = "Type the project name exactly to confirm deletion."

    def clean_confirmation(self):
        value = self.cleaned_data["confirmation"]
        if value != self.project.name:
            raise forms.ValidationError("Enter the project name exactly as shown above.")
        return value
