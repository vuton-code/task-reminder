import secrets
from datetime import timedelta
from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone
from accounts.models import Account
from projects.models import Membership
from projects.services import create_project
from tasks.models import Task

class Command(BaseCommand):
    help = "Create repeatable development fixtures."

    def add_arguments(self, parser):
        parser.add_argument("--scale", action="store_true")

    def handle(self, *args, **options):
        if not settings.DEBUG or settings.EMAIL_BACKEND_MODE != "fake":
            raise CommandError("Demo fixtures require local development and fake email.")
        password = secrets.token_urlsafe(18)
        owner, created = Account.objects.get_or_create(username="demo", defaults={"email": "demo@example.test", "email_verified_at": timezone.now()})
        if created:
            owner.set_password(password)
            owner.save()
            self.stdout.write(f"Development account: demo\nPassword: {password}")
        project = owner.project_set.filter(name="Website launch").first()
        if not project:
            project = create_project(owner, "Website launch")
        member = Membership.objects.get(project=project, account=owner, left_at=None)
        titles = ["Review the homepage copy", "Share the launch checklist", "Test the signup experience", "Prepare the team update"]
        for index, title in enumerate(titles):
            Task.objects.get_or_create(project=project, title=title, defaults={"assignee": member, "reminder_at": timezone.now()+timedelta(days=index+1)})
        from projects.services import change_role
        for name, role in [("demo-manager", "manager"), ("demo-member", "member")]:
            person, fresh = Account.objects.get_or_create(username=name, defaults={"email":name+"@example.test", "email_verified_at":timezone.now()})
            if fresh:
                person.set_password(password)
                person.save()
                self.stdout.write(f"Development account: {name}\nPassword: {password}")
            membership, _ = Membership.objects.get_or_create(project=project, account=person, left_at=None)
            if role=="manager" and membership.role!="manager":
                change_role(owner,project,membership,"manager",True,True,membership.version)
        if not owner.project_set.filter(name="Product planning").exists():
            create_project(owner,"Product planning")
        if options["scale"]:
            for index in range(100):
                Account.objects.get_or_create(username=f"fixture-{index}", defaults={"email": f"fixture-{index}@example.test", "email_verified_at": timezone.now()})
            fixture_users = list(Account.objects.filter(username__startswith="fixture-").order_by("username")[:49])
            for index in range(20):
                project = owner.project_set.filter(name=f"Capacity fixture {index}").first()
                if project is None:
                    project = create_project(owner, f"Capacity fixture {index}")
                member = Membership.objects.get(project=project, account=owner, left_at=None)
                for fixture in fixture_users:
                    Membership.objects.get_or_create(project=project, account=fixture, left_at=None)
                existing = set(Task.objects.filter(project=project).values_list("title", flat=True))
                Task.objects.bulk_create([
                    Task(project=project, title=f"Fixture task {number}", assignee=member)
                    for number in range(500) if f"Fixture task {number}" not in existing
                ])
        self.stdout.write(f"Project: /projects/{project.pk}/tasks")
