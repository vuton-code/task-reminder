import ipaddress
from django.conf import settings

class TrustedProxyMiddleware:
    """Only an explicitly trusted peer may assert HTTPS; never trust public headers."""
    def __init__(self,get_response): self.get_response=get_response
    def __call__(self,request):
        try:
            peer=ipaddress.ip_address(request.META.get("REMOTE_ADDR",""))
            trusted=any(peer in ipaddress.ip_network(cidr) for cidr in settings.TRUSTED_PROXY_CIDRS if cidr)
        except ValueError:
            trusted=False
        if trusted and request.META.get("HTTP_X_FORWARDED_PROTO")=="https":
            request.META["wsgi.url_scheme"]="https"
        return self.get_response(request)
