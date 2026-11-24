from concurrent.futures import ThreadPoolExecutor
from datetime import timedelta
from urllib.parse import urlparse, parse_qs
from unittest.mock import patch
import time
import pytest
from django.db import connections
from django.test import Client
from django.utils import timezone
from django.core.exceptions import ValidationError
from accounts.models import Account, GoogleFlow
from accounts.google_flow import resolve_identity
from accounts.services import issue_proof, consume_proof
from allauth.socialaccount.models import SocialAccount
from reminders.models import OutboundMessage
from reminders.providers import decrypt
pytestmark=pytest.mark.django_db

def claims(email="person@gmail.com"):
    return {"sub":"stable-sub","email":email,"email_verified":True,"aud":"client",
            "iss":"https://accounts.google.com","exp":int(time.time())+300}

def begin(client,settings,**data):
    settings.GOOGLE_CLIENT_ID="client"; settings.GOOGLE_CLIENT_SECRET="secret"
    response=client.post("/accounts/google/login/",data)
    assert response.status_code==302
    return parse_qs(urlparse(response.url).query)["state"][0]

def callback(client,state,assertion):
    with patch("accounts.google_flow.httpx.post") as exchange,patch("accounts.google_flow._verify_and_decode",return_value=assertion):
        exchange.return_value.json.return_value={"id_token":"fixture"}
        return client.get("/accounts/google/login/callback/",{"state":state,"code":"fixture"})

@pytest.mark.parametrize("mode",["nonce","expired","cancel","missing"])
def test_invalid_flow_grants_no_access(client,settings,mode):
    state=begin(client,settings)
    flow=GoogleFlow.objects.get()
    assertion=claims()|{"nonce":flow.nonce}
    if mode=="nonce": assertion["nonce"]="wrong"
    if mode=="missing": assertion.pop("sub")
    if mode=="expired": GoogleFlow.objects.update(expires_at=timezone.now()-timedelta(seconds=1))
    if mode=="cancel":
        response=client.get("/accounts/google/login/callback/",{"state":state,"error":"access_denied"})
    else: response=callback(client,state,assertion)
    assert response.status_code==400
    assert not SocialAccount.objects.exists()
    assert client.get("/reminders/due").status_code==401

def test_changed_email_and_inactive_identity():
    a=resolve_identity(claims())
    assert resolve_identity(claims("changed@gmail.com")).pk==a.pk
    a.refresh_from_db()
    assert a.email=="person@gmail.com" and a.email_verified_at is None
    a.is_active=False; a.save()
    with pytest.raises(ValidationError): resolve_identity(claims())

def test_explicit_link_and_mixed_session_reset(client,settings):
    a=Account.objects.create_user(username="local",email="person@gmail.com",email_verified_at=timezone.now(),password="strong-local-password")
    client.force_login(a)
    settings.GOOGLE_CLIENT_ID="client"; settings.GOOGLE_CLIENT_SECRET="secret"
    assert client.post("/accounts/google/login/",{"process":"connect"}).url=="/accounts/reauthenticate"
    assert client.post("/accounts/reauthenticate",{"username":"local","password":"strong-local-password"}).status_code==302
    state=begin(client,settings,process="connect")
    assert callback(client,state,claims()|{"nonce":GoogleFlow.objects.get().nonce}).status_code==302
    second=Client()
    state=begin(second,settings)
    assert callback(second,state,claims()|{"nonce":GoogleFlow.objects.order_by("-expires_at").first().nonce}).status_code==302
    assert client.get("/reminders/due").status_code==second.get("/reminders/due").status_code==200
    proof=issue_proof(a,"reset")
    token=decrypt(OutboundMessage.objects.get(proof=proof).encrypted_payload)["text"].rsplit("/",1)[-1]
    consume_proof(token,"reset","new-strong-local-password")
    assert client.get("/reminders/due").status_code==second.get("/reminders/due").status_code==401

def test_invitation_return_is_preview_only(client,settings):
    state=begin(client,settings,next="/invitations/opaque")
    response=callback(client,state,claims()|{"nonce":GoogleFlow.objects.get().nonce})
    assert response.url=="/invitations/opaque"
    assert not client.session.get("password_confirmed_at")

@pytest.mark.django_db(transaction=True)
def test_concurrent_google_first_signin_creates_one_profile():
    def login():
        try: return resolve_identity(claims()).pk
        finally: connections.close_all()
    with ThreadPoolExecutor(max_workers=2) as pool:
        results=list(pool.map(lambda _:login(),range(2)))
    assert results[0]==results[1]
    assert Account.objects.count()==SocialAccount.objects.count()==1
