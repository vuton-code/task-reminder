from django.shortcuts import get_object_or_404 as lookup
from django.http import Http404
from django.core.exceptions import ValidationError

def get_object_or_404(*args,**kwargs):
    try:
        return lookup(*args,**kwargs)
    except (ValidationError,ValueError):
        raise Http404 from None
