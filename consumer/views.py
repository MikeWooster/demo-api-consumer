import json

from django.http import HttpResponseRedirect
from django.views.generic import TemplateView, DetailView
from django.urls import reverse
import requests
from urllib.parse import urlencode

from applications.models import Application, Token


def pretty_print_json(json_data):
    return json.dumps(json_data, indent=4, sort_keys=True)


class AccountInfo:
    def __init__(self, bearer_token, base_url):
        self.bearer_token = bearer_token
        self.base_url = base_url

        self._headers = None
        self._accounts = None

    @property
    def headers(self):
        if self._headers is None:
            self._headers = {
                'Authorization': f'Bearer {self.bearer_token}'
            }
        return self._headers

    def get_accounts(self):
        return pretty_print_json(self.accounts)

    @property
    def accounts(self):
        if self._accounts is None:
            accounts_url = f"{self.base_url}accounts/"
            response = requests.get(accounts_url, headers=self.headers)
            account_data = self._get_data_from_response(response)
            self._accounts = account_data['Account']
        return self._accounts

    def get_balance_for_accounts(self):
        balances = []
        for account in self.accounts:
            account_id = account['AccountId']
            balance_url = f"{self.base_url}accounts/{account_id}/balances/"
            response = requests.get(balance_url, headers=self.headers)
            balance_data = self._get_data_from_response(response)
            balances.append(
                pretty_print_json(balance_data['Balance'])
            )
        return balances

    def get_products_for_accounts(self):
        products = []
        for account in self.accounts:
            account_id = account['AccountId']
            product_url = f"{self.base_url}accounts/{account_id}/product/"
            response = requests.get(product_url, headers=self.headers)
            product_data = self._get_data_from_response(response)
            products.append(
                pretty_print_json(product_data['Product'])
            )
        return products

    def _get_data_from_response(self, response):
        content = response.json()
        return content['Data']


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
                'account_info': self._build_account_info_for_application(app),
            })
        context['unconnected_applications'] = unconnected_applications
        return context

    def _user_connected_applications(self):
        tokens = Token.objects.filter(user=self.request.user)
        applications = []
        for token in tokens:
            applications.append(token.application)
        return applications

    def _build_account_info_for_application(self, app):
        """Build a list of accounts with their product information and balance.
        """
        base_url = app.base_api_url
        bearer_token = self._get_bearer_token(app)
        account_info = AccountInfo(bearer_token, base_url)

        return {
            'accounts': account_info.get_accounts(),
            'balances': account_info.get_balance_for_accounts(),
            'products': account_info.get_products_for_accounts(),
        }

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
        print(f"Redirecting to authorize: {url}")
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
            'client_secret': self.object.client_secret,
        }
        print(f"Getting user token at: {self.object.token_url} with data: {post_data}")
        response = requests.post(
            self.object.token_url,
            data=post_data,
        )
        response_json = response.json()
        print(f"Got response from token endpoint: {response} with data: {response_json}")
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
        print(f"Disconnecting user at: {self.object.revoke_url} with data: {post_data}")
        response = requests.post(
            self.object.revoke_url,
            data=post_data,
        )
        print(f"Got response from revoke endpoint: {response}")
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