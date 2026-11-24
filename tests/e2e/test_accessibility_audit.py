import json
from pathlib import Path
import pytest
from django.utils import timezone
from accounts.models import Account
from projects.services import create_project
from tasks.services import save_task
from playwright.sync_api import sync_playwright
pytestmark=pytest.mark.django_db(transaction=True)

def test_axe_public_and_authenticated_pages(live_server):
    script=Path(".runtime/a11y/node_modules/axe-core/axe.min.js")
    assert script.exists(), "Install test tool: pnpm --dir .runtime/a11y add axe-core@4.14.0"
    a=Account.objects.create_user(username="audit",email="audit@example.test",password="audit-test-password",email_verified_at=timezone.now())
    p=create_project(a,"Accessibility")
    save_task(a,p,{"title":"Review the form"})
    report=[]
    with sync_playwright() as pw:
        browser=pw.chromium.launch(); page=browser.new_page(viewport={"width":390,"height":844})
        def audit(path):
            page.goto(live_server.url+path)
            page.add_script_tag(path=str(script.resolve()))
            result=page.evaluate("async () => (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})).violations")
            report.append({"path":path,"violations":result})
        audit("/accounts/register"); audit("/accounts/login")
        page.get_by_label("Username").fill("audit")
        page.get_by_label("Password").fill("audit-test-password")
        page.get_by_role("button",name="Sign in",exact=True).click()
        page.wait_for_url("**/projects")
        for path in ["/projects",f"/projects/{p.pk}/tasks",f"/projects/{p.pk}/members",f"/projects/{p.pk}/groups","/reminders","/accounts/preferences"]:
            audit(path)
        browser.close()
    Path("artifacts/accessibility-audit.json").write_text(json.dumps(report,indent=2))
    assert not [(r["path"],v["id"],[n["target"] for n in v["nodes"]]) for r in report for v in r["violations"]]
