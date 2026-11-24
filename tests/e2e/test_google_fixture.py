import time
from urllib.parse import urlparse,parse_qs
from unittest.mock import patch
import pytest
from playwright.sync_api import sync_playwright,expect
pytestmark=pytest.mark.django_db(transaction=True)

def test_google_onboarding_and_logout_browser(live_server,settings):
    settings.GOOGLE_CLIENT_ID="client";settings.GOOGLE_CLIENT_SECRET="fixture"
    with sync_playwright() as pw:
        browser=pw.chromium.launch()
        page=browser.new_page()
        params = {}
        def intercept_begin(route):
            response=route.fetch(max_redirects=0)
            params.update(parse_qs(urlparse(response.headers["location"]).query))
            route.fulfill(response=response,status=200,
                headers={k:v for k,v in response.headers.items() if k.lower()!="location"},
                body="Local Google provider fixture")
        page.route("**/accounts/google/login/",intercept_begin)
        page.goto(live_server.url+"/accounts/login")
        page.get_by_role("button",name="Continue with Google").click()
        page.wait_for_url("**/accounts/google/login/")
        assert "nonce" in params
        claims={"sub":"browser-google","email":"google@gmail.com","email_verified":True,
                "iss":"https://accounts.google.com","aud":"client","exp":int(time.time())+300,"nonce":params["nonce"][0]}
        with patch("accounts.google_flow.httpx.post") as exchange,patch("accounts.google_flow._verify_and_decode",return_value=claims):
            exchange.return_value.json.return_value={"id_token":"fixture"}
            page.goto(live_server.url+"/accounts/google/login/callback/?state="+params["state"][0]+"&code=fixture")
            expect(page.get_by_role("button",name="Sign out")).to_be_visible()
            expect(page.get_by_label("Password")).to_have_count(0)
            page.get_by_role("button",name="Sign out").click()
            expect(page.get_by_role("button",name="Sign in",exact=True)).to_be_visible()
        browser.close()
