from pathlib import Path
import pytest
from django.utils import timezone
from playwright.sync_api import sync_playwright, expect
from accounts.models import Account
from projects.services import create_project
from tasks.services import save_task

@pytest.mark.django_db(transaction=True)
@pytest.mark.parametrize("engine", ["chromium", "firefox", "webkit"])
def test_browser_task_workflow(live_server,engine):
    user = Account.objects.create_user(username="browser", email="browser@example.test",
        password="browser-test-password", email_verified_at=timezone.now())
    project = create_project(user, "Website launch")
    for title in ["Review the homepage copy", "Share the launch checklist", "Prepare the team update"]:
        save_task(user, project, {"title": title})
    with sync_playwright() as browser_tools:
        browser = getattr(browser_tools,engine).launch()
        page = browser.new_page()
        page.goto(live_server.url + "/accounts/login")
        page.get_by_label("Username").fill("browser")
        page.get_by_label("Password").fill("browser-test-password")
        page.get_by_role("button", name="Sign in", exact=True).click()
        page.get_by_role("link", name="Website launch").last.click()
        page.get_by_label("Task").fill("Check the final draft")
        page.get_by_role("button", name="Save task").click()
        page.get_by_role("link", name="Check the final draft", exact=True).wait_for()
        folder = Path("artifacts")
        folder.mkdir(exist_ok=True)
        page.set_viewport_size({"width": 1440, "height": 1000})
        page.screenshot(path=str(folder / ("desktop.png" if engine=="chromium" else f"desktop-{engine}.png")), full_page=True)
        page.get_by_role("button", name="Complete Check the final draft", exact=True).click()
        expect(page.locator(".completed").filter(has_text="Check the final draft")).to_have_count(1)
        page.set_viewport_size({"width": 390, "height": 844})
        assert page.evaluate("document.documentElement.scrollWidth <= window.innerWidth")
        page.screenshot(path=str(folder / ("mobile.png" if engine=="chromium" else f"mobile-{engine}.png")), full_page=True)
        browser.close()

