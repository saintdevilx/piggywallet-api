from rest_framework import status
from rest_framework.authtoken.models import Token

from api.user.serializers import UserDetailReadSerializer

STATUS = {
    "status": None,
    "message": None,
}


def too_many_requests():
    STATUS["status"] = status.HTTP_429_TOO_MANY_REQUESTS
    STATUS["message"] = "Reached max limit for the day."
    return (STATUS, STATUS["status"])


def unauthorized():
    STATUS["status"] = status.HTTP_401_UNAUTHORIZED
    STATUS["message"] = "User not logged in."
    return (STATUS, STATUS["status"])


def failure(message="Failed"):
    STATUS["status"] = status.HTTP_400_BAD_REQUEST
    STATUS["message"] = message
    return (STATUS, STATUS["status"])


def success(message=None):
    STATUS["status"] = status.HTTP_200_OK
    STATUS["message"] = message
    return (STATUS, STATUS["status"])


def user_detail(user):
    try:
        token = user.auth_token.key
    except:
        token = Token.objects.create(user=user)
        token = token.key
    user_json = {
        "id": user.pk,
        "last_login": user.last_login,
        "username":user.username,
        "token": token,
        "status": status.HTTP_200_OK
    }
    user_json.update(UserDetailReadSerializer(user).data)
    return user_json


def model_field_attr(model, model_field, attr):
    """
    Returns the specified attribute for the specified field on the model class.
    """
    fields = dict([(field.name, field) for field in model._meta.fields])
    return getattr(fields[model_field], attr)
