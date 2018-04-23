from django.db import models
from django.contrib.auth import get_user_model

class Application(models.Model):
    """
    The applications that are registered with the system.
    """
    application_name = models.CharField(max_length=100)
    client_secret = models.CharField(max_length=256)
    client_id = models.CharField(max_length=256)
    authorize_url = models.CharField(max_length=1024)
    token_url = models.CharField(max_length=1024)
    refresh_url = models.CharField(max_length=1024)
    revoke_url = models.CharField(max_length=1024)
    base_api_url = models.CharField(max_length=1024)

    def __str__(self):
        return self.application_name


class Token(models.Model):
    """
    The users token for applications.
    """
    token = models.CharField(max_length=1024)
    refresh = models.CharField(max_length=1024)
    user = models.ForeignKey(get_user_model(), on_delete=models.CASCADE)
    application = models.ForeignKey(Application, on_delete=models.CASCADE)

    def __str__(self):
        return self.token