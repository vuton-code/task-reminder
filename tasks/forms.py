from datetime import datetime, timezone
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError
from django import forms
from projects.models import Membership

class TaskForm(forms.Form):
    title = forms.CharField(max_length=200, label="Task")
    description = forms.CharField(required=False, max_length=10000, widget=forms.Textarea(attrs={"rows": 3}))
    reminder_at = forms.CharField(required=False, label="Remind me", widget=forms.DateTimeInput(attrs={"type": "datetime-local"}))
    timezone = forms.CharField(max_length=80, label="Time zone")
    fold = forms.ChoiceField(required=False, label="Repeated time", choices=[("", "Choose only if the clock repeats"), ("0", "First occurrence"), ("1", "Second occurrence")])
    assignee = forms.ModelChoiceField(queryset=Membership.objects.none(), required=False)
    version = forms.IntegerField(required=False, widget=forms.HiddenInput)
    mutation_key = forms.UUIDField(required=False, widget=forms.HiddenInput)

    def __init__(self, *args, project, actor=None, **kwargs):
        if args and args[0] is not None and "expected_version" in args[0] and "version" not in args[0]:
            data=args[0].copy()
            data["version"]=data["expected_version"]
            args=(data,*args[1:])
        super().__init__(*args, **kwargs)
        self.fields["assignee"].queryset = Membership.objects.filter(project=project, left_at__isnull=True).select_related("account")
        self.fields["assignee"].label = "Assign to"
        if actor is not None:
            member = Membership.objects.get(project=project, account=actor, left_at=None)
            if project.owner_id != actor.pk and not (member.role == "manager" and member.can_assign):
                self.fields["assignee"].queryset = self.fields["assignee"].queryset.filter(pk=member.pk)
                self.fields["assignee"].empty_label = None
                self.fields["assignee"].help_text = "You can create tasks for yourself. Assigning to others requires project permission."
        self.fields["assignee"].label_from_instance = lambda m: m.account.display_name

    def clean_reminder_at(self):
        return self.cleaned_data["reminder_at"]

    def clean(self):
        data = super().clean()
        raw = data.get("reminder_at")
        if not raw:
            data["reminder_at"] = None
            return data
        try:
            zone = ZoneInfo(data.get("timezone", ""))
            naive = datetime.fromisoformat(raw)
            if naive.tzinfo is not None:
                raise ValueError
            first, second = naive.replace(tzinfo=zone, fold=0), naive.replace(tzinfo=zone, fold=1)
            if first.astimezone(timezone.utc).astimezone(zone).replace(tzinfo=None) != naive:
                raise ValueError
            if first.utcoffset() != second.utcoffset() and not data.get("fold"):
                self.add_error("fold", "This local time occurs twice. Choose an occurrence.")
                return data
            data["reminder_at"] = naive.replace(tzinfo=zone, fold=int(data.get("fold") or 0)).astimezone(timezone.utc)
        except (ValueError, ZoneInfoNotFoundError):
            self.add_error("reminder_at", "Choose a valid local time and time zone.")
        return data
