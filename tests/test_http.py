import uuid
import pytest
from django.utils import timezone
from accounts.models import Account
from projects.services import create_project
from projects.models import Membership
from tasks.services import save_task

pytestmark = pytest.mark.django_db

@pytest.fixture
def user():
    return Account.objects.create_user(username="maya", email="maya@example.com", password="test-password-123", email_verified_at=timezone.now())

def test_pages_and_task_form(client, user):
    client.force_login(user)
    assert client.get("/projects").status_code == 200
    project = create_project(user, "Review")
    url = f"/projects/{project.pk}/tasks"
    assert client.get(url).status_code == 200
    response = client.post(url, {"title": "Check copy", "timezone": "America/Los_Angeles", "mutation_key": str(uuid.uuid4())})
    assert response.status_code == 302
    assert client.get(url).status_code == 200
    assert client.get(f"/projects/{project.pk}/members").status_code == 200
    assert client.get(f"/projects/{project.pk}/groups").status_code == 200

def test_outsider_gets_no_task(client, user):
    project = create_project(user, "Secret")
    task = save_task(user, project, {"title": "Private title"})
    outsider = Account.objects.create_user(username="other", email="other@example.com")
    client.force_login(outsider)
    response = client.get(f"/projects/{project.pk}/tasks/{task.pk}")
    assert response.status_code == 404
    assert b"Private title" not in response.content

def test_logout_ends_one_session(client, user):
    from django.test import Client
    second = Client()
    client.force_login(user)
    second.force_login(user)
    client.get("/projects")
    second.get("/projects")
    assert client.post("/accounts/logout").status_code == 302
    assert client.get("/reminders/due").status_code == 401
    assert second.get("/reminders/due").status_code == 200

def test_google_button_available(client):
    response = client.get("/accounts/login")
    assert b"Continue with Google" in response.content
    assert client.get("/accounts/google/login/").status_code == 405
