from django.http import HttpResponseRedirect
from django.urls import reverse, resolve


class LoginRequiredMiddleware:
    ALLOWED_URLS = {
        'login'
    }
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        namespaced_url_name = self._get_namespaced_url(request)
        if namespaced_url_name not in self.ALLOWED_URLS and not request.user.is_authenticated:
            return HttpResponseRedirect(reverse('login'))

        response = self.get_response(request)
        return response

    def _get_namespaced_url(self, request):
        """Constructs the fully namespaced url string from the request object.

        Returns:
            None if the request does not have a url_name, or the namespaced url string
        """
        resolved_url = resolve(request.path)
        if resolved_url.url_name:
            namespaced_url = resolved_url.namespaces
            namespaced_url.append(resolved_url.url_name)
            return ":".join(namespaced_url)
        else:
            return None