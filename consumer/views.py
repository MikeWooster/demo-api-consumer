from django.http import HttpResponseRedirect
from django.views.generic import TemplateView, DetailView
from django.urls import reverse
import requests
from urllib.parse import urlencode

from applications.models import Application, Token


class HomeView(TemplateView):
    template_name = 'home.html'

    def get_context_data(self, **kwargs):

        connected_applications = self._user_connected_applications()
        unconnected_applications = Application.objects.exclude(id__in=[a.id for a in connected_applications])

        context = super().get_context_data()
        context['api_endpoints'] = []
        for app in connected_applications:
            context['api_endpoints'].append({
                'id':  app.id,
                'name': app.application_name,
                'application_balance': self._get_balance_for_application(app),
            })
        print(context['api_endpoints'])
        # context['connected_applications'] = connected_applications
        context['unconnected_applications'] = unconnected_applications
        return context

    def _user_connected_applications(self):
        tokens = Token.objects.filter(user=self.request.user)
        applications = []
        for token in tokens:
            applications.append(token.application)
        return applications

    def _get_balance_for_application(self, app):
        """Get the balance for the application.
        """
        base_url = app.base_api_url
        accounts_url = f'{base_url}accounts/'

        bearer_token = self._get_bearer_token(app)
        headers = {
            'Authorization': f'Bearer {bearer_token}'
        }
        print(headers)
        response = requests.get(accounts_url, headers=headers)
        return response.json()

    def _get_bearer_token(self, app):
        token = Token.objects.get(
            user=self.request.user,
            application=app,
        )
        return token.token


class ConnectView(DetailView):
    model = Application

    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)

        redirect_uri = f'https://localhost:8001/success/{self.object.id}'
        params = {
            'response_type': 'code',
            'client_id': self.object.client_id,
            'state': 'random_state_string',
            'redirect_uri': redirect_uri,
            'scope': 'balances products accounts',
        }

        url = self.object.authorize_url + '?' + urlencode(params)
        return HttpResponseRedirect(url)


class GetTokenView(DetailView):
    model = Application

    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)

        code = request.GET['code']
        print(code)
        user = request.user

        redirect_uri = f'https://localhost:8001/success/{self.object.id}'
        post_data = {
            'code': code,
            'grant_type': 'authorization_code',
            'client_id': self.object.client_id,
            'redirect_uri': redirect_uri,
            'scope': 'balances products accounts',
        }
        response = requests.post(
            self.object.token_url,
            data=post_data,
        )
        response_json = response.json()
        print(response_json)
        access_token = response_json['access_token']
        refresh_token = response_json['refresh_token']

        Token.objects.create(
            user=user,
            application=self.object,
            token=access_token,
            refresh=refresh_token,
        )
        return HttpResponseRedirect(reverse('home'))


class DisconnectView(DetailView):
    model = Application

    def get(self, request, *args, **kwargs):
        super().get(request, *args, **kwargs)

        token = self._get_token()
        post_data = {
            'token': token.token,
            'client_id': self.object.client_id,
            'client_secret': self.object.client_secret,
        }
        response = requests.post(
            self.object.revoke_url,
            data=post_data,
        )
        if response.status_code == 200:
            token.delete()
        return HttpResponseRedirect(reverse('home'))

    def _get_token(self):
        """Returns the token for the user to connect to this application.
        """
        token = Token.objects.get(
            user=self.request.user,
            application=self.object,
        )
        return token