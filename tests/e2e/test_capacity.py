"""Local capacity evidence; automated timings do not replace human usability trials."""
import io
import json
import time
from pathlib import Path
import pytest
from django.core.management import call_command
from django.test import Client
from django.conf import settings
from accounts.models import Account
from projects.models import Project, Membership
from tasks.models import Task
from playwright.sync_api import sync_playwright
pytestmark=pytest.mark.django_db(transaction=True)

def test_fifty_active_tabs_at_fixture_scale(live_server):
    call_command("seed_demo",scale=True,stdout=io.StringIO())
    call_command("seed_demo",scale=True,stdout=io.StringIO())
    projects=Project.objects.filter(name__startswith="Capacity fixture ")
    assert projects.count()==20
    assert Task.objects.filter(project__in=projects).count()==10000
    assert Account.objects.filter(username__startswith="fixture-").count()==100
    owner=Account.objects.get(username="demo")
    client=Client(); client.force_login(owner); client.get("/projects")
    cookie=client.cookies[settings.SESSION_COOKIE_NAME].value
    report={"accounts":100,"projects":20,"tasks":10000,"tabs":50,"samples":[]}
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        context=browser.new_context()
        context.add_cookies([{"name":settings.SESSION_COOKIE_NAME,"value":cookie,"url":live_server.url}])
        pages=[]
        for i in range(50):
            page=context.new_page()
            page.goto(live_server.url+"/reminders")
            pages.append(page)
        # All pages stay alive with the application's two-second polling enabled.
        for round_number in range(2):
            for page in pages:
                measurement=page.evaluate("""async () => {
                    const start=performance.now();
                    const result=await fetch('/reminders/due',{cache:'no-store'});
                    await result.json();
                    return {status:result.status,seconds:(performance.now()-start)/1000,visible:!document.hidden};
                }""")
                report["samples"].append(measurement)
        report["browser"]=browser.version
        browser.close()
    assert all(x["status"]==200 and x["visible"] for x in report["samples"])
    assert sum(x["seconds"]<=5 for x in report["samples"])>=99
    Path("artifacts").mkdir(exist_ok=True)
    Path("artifacts/capacity-50-tabs.json").write_text(json.dumps(report,indent=2))
