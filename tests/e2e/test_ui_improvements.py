from datetime import timedelta
from pathlib import Path
import pytest
from django.utils import timezone
from accounts.models import Account
from projects.models import Membership
from projects.services import create_project
from tasks.services import save_task
from playwright.sync_api import sync_playwright, expect

pytestmark = pytest.mark.django_db(transaction=True)

@pytest.mark.parametrize("engine", ["chromium", "firefox", "webkit"])
def test_ui_metadata_mobile_and_deletion(live_server,engine):
    owner=Account.objects.create_user(username="Maya",email="maya@example.test",password="browser-test-password",email_verified_at=timezone.now())
    member=Account.objects.create_user(username="Alex",email="alex@example.test",password="browser-test-password",email_verified_at=timezone.now())
    project=create_project(owner,"Website launch")
    Membership.objects.create(project=project,account=member)
    save_task(owner,project,{"title":"Review launch checklist", "reminder_at":timezone.now()-timedelta(minutes=1)})
    with sync_playwright() as pw:
        browser=getattr(pw,engine).launch()
        context=browser.new_context(viewport={"width":390,"height":844})
        page=context.new_page()
        page.goto(live_server.url+"/accounts/login")
        page.get_by_label("Username").fill("Maya")
        page.get_by_label("Password").fill("browser-test-password")
        page.get_by_role("button",name="Sign in",exact=True).click()
        expect(page.locator(".account-chip")).to_contain_text("maya@example.test")
        expect(page.locator(".account-chip")).to_be_visible()
        expect(page.locator(".project-card .role-badge")).to_have_text("Owner")
        page.goto(live_server.url+f"/projects/{project.pk}/tasks")
        expect(page.get_by_label("Assign to")).to_be_visible()
        expect(page.get_by_label("Assign to").locator("option")).to_have_count(3)
        page.wait_for_function("document.querySelector('[data-reminders]').dataset.signature")
        reminder=page.locator(".reminder-item").first
        expect(reminder).to_contain_text("Assigned by Maya")
        expect(reminder.locator("time")).to_have_count(3)
        expect(reminder).to_contain_text("Created ")
        expect(page.locator(".brand-subtitle")).to_have_count(0)
        expect(reminder).not_to_contain_text("America/Los_Angeles")
        reminder.focus()
        with page.expect_response(lambda r:'/reminders/due' in r.url): pass
        expect(reminder).to_be_focused()
        assert page.evaluate("document.documentElement.scrollWidth <= innerWidth")
        if engine=="chromium":
            page.evaluate("window.scrollTo(0,0)")
            page.screenshot(path="artifacts/ui-mobile.png",full_page=True)
            page.set_viewport_size({"width":1440,"height":1000})
            page.evaluate("window.scrollTo(0,0)")
            page.screenshot(path="artifacts/ui-desktop.png",full_page=True)
            axe=Path('.runtime/a11y/node_modules/axe-core/axe.min.js')
            for path in [f"/projects/{project.pk}/tasks",f"/projects/{project.pk}/delete"]:
                page.goto(live_server.url+path)
                page.add_script_tag(path=str(axe.resolve()))
                issues=page.evaluate("async () => (await axe.run(document,{runOnly:{type:'tag',values:['wcag2a','wcag2aa','wcag21aa','wcag22aa']}})).violations")
                assert not issues, [(v["id"], [(n["target"], n.get("failureSummary")) for n in v["nodes"]]) for v in issues]
        # Confirmation works with JavaScript disabled and leaves data alone on GET/cancel.
        nojs=browser.new_context(java_script_enabled=False,storage_state=context.storage_state())
        confirm=nojs.new_page()
        confirm.goto(live_server.url+f"/projects/{project.pk}/delete")
        confirm.get_by_role("link",name="Keep project").click()
        expect(confirm.get_by_role("heading",name="People",exact=True)).to_be_visible()
        confirm.goto(live_server.url+f"/projects/{project.pk}/delete")
        confirm.get_by_label("Project name").fill("Website launch")
        confirm.get_by_role("button",name="Permanently delete project").click()
        expect(confirm).to_have_url(live_server.url+"/projects")
        expect(confirm.locator(".project-card")).to_have_count(0)
        browser.close()
