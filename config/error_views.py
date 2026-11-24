import logging
import uuid
from django.shortcuts import render

def server_error(request):
    reference=uuid.uuid4().hex[:12]
    logging.getLogger("django.request").error("Unexpected request failure; reference=%s",reference)
    response=render(request,"notice.html",{"title":"Something went wrong",
        "notice":f"Please try again. If the problem continues, share reference {reference}."},status=500)
    response["X-Error-Reference"]=reference
    return response
