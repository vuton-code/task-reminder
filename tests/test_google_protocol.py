import time
from types import SimpleNamespace
from unittest.mock import patch
import jwt
import pytest
from cryptography.hazmat.primitives.asymmetric import rsa
from allauth.socialaccount.providers.google.views import _verify_and_decode
from allauth.socialaccount.providers.oauth2.client import OAuth2Error

@pytest.fixture(scope="module")
def key():
    return rsa.generate_private_key(public_exponent=65537, key_size=2048)

@pytest.mark.parametrize("override", [{"aud":"wrong"}, {"iss":"wrong"}, {"exp":1}])
def test_real_google_token_validation_rejects_invalid_claims(key, override):
    claims = {"sub":"subject", "aud":"client", "iss":"https://accounts.google.com", "exp":int(time.time())+300, **override}
    encoded = jwt.encode(claims, key, algorithm="RS256", headers={"kid":"test"})
    with patch("allauth.socialaccount.internal.jwtkit.fetch_key", return_value=("RS256", key.public_key())):
        with pytest.raises(OAuth2Error):
            _verify_and_decode(SimpleNamespace(client_id="client"), encoded)

def test_real_google_signature_validation(key):
    other_key = rsa.generate_private_key(public_exponent=65537, key_size=2048)
    claims = {"sub":"subject", "aud":"client", "iss":"https://accounts.google.com", "exp":int(time.time())+300}
    encoded = jwt.encode(claims, other_key, algorithm="RS256", headers={"kid":"test"})
    with patch("allauth.socialaccount.internal.jwtkit.fetch_key", return_value=("RS256", key.public_key())):
        with pytest.raises(OAuth2Error):
            _verify_and_decode(SimpleNamespace(client_id="client"), encoded)

@pytest.mark.django_db
def test_google_flow_replay_and_pkce(client, settings):
    from accounts.models import GoogleFlow
    from urllib.parse import urlparse, parse_qs
    settings.GOOGLE_CLIENT_ID = "client"
    settings.GOOGLE_CLIENT_SECRET = "secret"
    result = client.post("/accounts/google/login/")
    assert result.status_code == 302
    parameters = parse_qs(urlparse(result.url).query)
    assert parameters["code_challenge_method"] == ["S256"]
    state = parameters["state"][0]
    assert client.get("/accounts/google/login/callback/", {"state":state, "error":"access_denied"}).status_code == 400
    assert client.get("/accounts/google/login/callback/", {"state":state, "code":"replay"}).status_code == 400
    assert GoogleFlow.objects.get().consumed_at

@pytest.mark.django_db
def test_google_flow_wrong_session(client, settings):
    from django.test import Client
    from urllib.parse import urlparse, parse_qs
    settings.GOOGLE_CLIENT_ID = "client"
    settings.GOOGLE_CLIENT_SECRET = "secret"
    url = client.post("/accounts/google/login/").url
    state = parse_qs(urlparse(url).query)["state"][0]
    assert Client().get("/accounts/google/login/callback/", {"state":state,"code":"x"}).status_code == 400
