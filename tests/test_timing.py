import json
import time
from pathlib import Path
from datetime import timedelta
import pytest
from django.utils import timezone
from playwright.sync_api import sync_playwright
from accounts.models import Account
from projects.services import create_project
from projects.models import Membership
from tasks.models import Task

@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("width,height", [(1440,900), (390,844)])
def test_active_and_returning_reminders(live_server, width, height):
    user = Account.objects.create_user(username="timing", email="timing@example.test",
        password="timing-test-password", email_verified_at=timezone.now())
    project = create_project(user, "Timing")
    member = Membership.objects.get(project=project,account=user)
    due = timezone.now()+timedelta(seconds=8)
    Task.objects.bulk_create([Task(project=project, assignee=member, title=f"Timed task {i}", reminder_at=due) for i in range(100)])
    report = {"viewport": [width,height], "active": [], "returning": [], "provider":"local"}
    with sync_playwright() as tools:
        browser = tools.chromium.launch()
        page = browser.new_page(viewport={"width":width,"height":height})
        page.goto(live_server.url+"/accounts/login")
        page.get_by_label("Username").fill("timing")
        page.get_by_label("Password").fill("timing-test-password")
        page.get_by_role("button",name="Sign in",exact=True).click()
        page.wait_for_url("**/projects")
        assert page.locator("[data-reminders] a").count() == 0
        page.locator("[data-reminders] a").nth(99).wait_for(timeout=15000)
        observed = timezone.now()
        lag = (observed-due).total_seconds()
        report["active"] = [{"scheduled_at":due.isoformat(), "visible_at":observed.isoformat(), "delay_seconds":lag} for _ in range(100)]
        assert 0 <= lag <= 10
        for number in range(100):
            if number % 2:
                page.get_by_role("button",name="Sign out",exact=True).click()
                page.get_by_label("Username").fill("timing")
                page.get_by_label("Password").fill("timing-test-password")
                start=time.monotonic()
                page.get_by_role("button",name="Sign in",exact=True).click()
                page.wait_for_url("**/projects")
            else:
                start=time.monotonic()
                page.goto(live_server.url+"/projects")
            page.locator("[data-reminders] a").nth(99).wait_for()
            report["returning"].append({"seconds":time.monotonic()-start, "login":bool(number%2)})
        browser.close()
    assert sum(sample["seconds"] <= 5 for sample in report["returning"]) >= 99
    Path("artifacts").mkdir(exist_ok=True)
    Path(f"artifacts/timing-{width}.json").write_text(json.dumps(report,indent=2))
