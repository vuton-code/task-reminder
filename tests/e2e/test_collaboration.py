from pathlib import Path
from datetime import timedelta
from urllib.parse import urlparse
import pytest
from playwright.sync_api import sync_playwright, expect
from django.utils import timezone
from accounts.models import Account
from accounts.services import issue_proof
from projects.services import create_project
from projects.invitations import invite
from reminders.services import dispatch
from reminders.models import OutboundMessage
from reminders.providers import decrypt
from tasks.services import save_task
pytestmark=pytest.mark.django_db(transaction=True)

def sign_in(page,base,name):
    page.goto(base+"/accounts/login")
    page.get_by_label("Username").fill(name)
    page.get_by_label("Password").fill("browser-test-password")
    page.get_by_role("button",name="Sign in",exact=True).click()
    page.wait_for_url("**/projects")

@pytest.mark.parametrize("width",[1440,390])
def test_invitation_groups_assignment_and_departure(live_server,width):
    owner=Account.objects.create_user(username="owner",email="owner@example.test",password="browser-test-password",email_verified_at=timezone.now())
    member=Account.objects.create_user(username="member",email="member@example.test",password="browser-test-password",email_verified_at=timezone.now())
    project=create_project(owner,"Collaboration")
    task=save_task(owner,project,{"title":"Private team task","description":"Team details"})
    invitation=invite(owner,project,member.email)
    dispatch()
    link=urlparse(decrypt(OutboundMessage.objects.get(invitation=invitation).encrypted_payload)["text"].splitlines()[-1]).path
    base=live_server.url; root=f"{base}/projects/{project.pk}"
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        a=browser.new_page(viewport={"width":width,"height":900})
        b=browser.new_page(viewport={"width":width,"height":900})
        sign_in(b,base,"member")
        b.goto(base+link)
        expect(b.get_by_text("Private team task",exact=True)).to_have_count(0)
        b.get_by_role("button",name="Accept invitation").click()
        expect(b.get_by_role("link",name="Private team task",exact=True)).to_be_visible()
        sign_in(a,base,"owner")
        a.goto(root+"/groups")
        create=a.locator("section").filter(has=a.get_by_role("heading",name="Create group"))
        create.get_by_label("Name",exact=True).fill("Design")
        create.get_by_label("member",exact=True).check()
        create.get_by_role("button",name="Create group",exact=True).click()
        expect(a.get_by_role("heading",name="Design",exact=True)).to_be_visible()
        a.goto(root+f"/tasks/{task.pk}")
        a.get_by_label("Assign to").select_option(label="member")
        a.get_by_role("button",name="Save changes").click()
        b.goto(root+f"/tasks/{task.pk}")
        expect(b.get_by_role("button",name="Save changes")).to_be_visible()
        b.goto(root+"/groups")
        expect(b.get_by_role("button",name="Create group")).to_have_count(0)
        b.goto(root+"/members")
        b.get_by_role("button",name="Leave project",exact=True).click()
        b.goto(root+f"/tasks/{task.pk}")
        expect(b.get_by_text("Private team task",exact=True)).to_have_count(0)
        a.goto(root+"/groups")
        group=a.locator("section").filter(has=a.get_by_role("heading",name="Design",exact=True))
        expect(group.get_by_text("No members yet.",exact=True)).to_be_visible()
        group.get_by_text("Edit group",exact=True).click()
        group.get_by_role("button",name="Delete group").click()
        expect(a.get_by_role("heading",name="Design",exact=True)).to_have_count(0)
        assert a.evaluate("document.documentElement.scrollWidth <= innerWidth")
        browser.close()

def test_two_browser_sessions_reset_and_keyboard_access(live_server):
    a=Account.objects.create_user(username="sessions",email="sessions@example.test",password="browser-test-password",email_verified_at=timezone.now())
    proof=issue_proof(a,"reset")
    reset=urlparse(decrypt(OutboundMessage.objects.get(proof=proof).encrypted_payload)["text"]).path
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        first=browser.new_page(); second=browser.new_page()
        sign_in(first,live_server.url,"sessions"); sign_in(second,live_server.url,"sessions")
        first.goto(live_server.url+"/projects")
        first.keyboard.press("Tab")
        expect(first.get_by_role("link",name="Skip to content")).to_be_focused()
        first.keyboard.press("Enter")
        expect(first.locator("main")).to_be_focused()
        assert first.evaluate("navigator.serviceWorker.getRegistrations().then(x=>x.length)")==0
        first.get_by_role("button",name="Sign out").click()
        second.goto(live_server.url+"/projects")
        expect(second.get_by_role("button",name="Sign out")).to_be_visible()
        first.goto(live_server.url+reset)
        first.get_by_label("Password",exact=False).first.fill("new-browser-test-password")
        first.get_by_label("Confirmation").fill("new-browser-test-password")
        first.get_by_role("button",name="Confirm",exact=True).click()
        second.goto(live_server.url+"/projects")
        expect(second.get_by_role("button",name="Sign in",exact=True)).to_be_visible()
        browser.close()
