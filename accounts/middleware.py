from django.contrib.auth import logout

class AccountSessionMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            generation = request.session.get("auth_generation")
            if generation is None:
                request.session["auth_generation"] = request.user.auth_generation
            elif generation != request.user.auth_generation:
                logout(request)
        response = self.get_response(request)
        response["Cache-Control"] = "private, no-store"
        return response
