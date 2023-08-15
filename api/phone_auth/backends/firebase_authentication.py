# -*- coding: utf-8 -*-
"""
Authentication backend for handling firebase user.idToken from incoming
Authorization header, verifying, and locally authenticating
Author: Gary Burgmann
Email: garyburgmann@gmail.com
Location: Springfield QLD, Australia
Last update: 2019-02-10
"""
import json
import uuid

import firebase_admin
from firebase_admin import auth as firebase_auth, auth
from django.utils.encoding import smart_text
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.contrib.auth.models import AnonymousUser
from rest_framework import (
    authentication,
    exceptions
)
from mpw import settings

from lib.utils import logger

User = get_user_model()


class BaseFirebaseAuthentication(authentication.BaseAuthentication):
    """
    Token based authentication using firebase.
    """

    def authenticate(self, request):
        """
        With ALLOW_ANONYMOUS_REQUESTS, set request.user to an AnonymousUser,
        allowing us to configure access at the permissions level.
        """
        # authorization_header = authentication.get_authorization_header(request)
        # if not authorization_header:
        #     return

        """
        Returns a tuple of len(2) of `User` and the decoded firebase token if
        a valid signature has been supplied using Firebase authentication.
        """
        firebase_token = self.get_token(request)
        decoded_token = self.decode_token(firebase_token)

        firebase_user = self.authenticate_token(decoded_token)

        local_user = self.get_or_create_local_user(firebase_user)

        return local_user

    def get_token(self, request):
        raise NotImplementedError('get_token() has not been implemented.')

    def decode_token(self, firebase_token):
        raise NotImplementedError('decode_token() has not been implemented.')

    def authenticate_token(self, decoded_token):
        raise NotImplementedError('authenticate_token() has not been implemented.')

    def get_or_create_local_user(self, firebase_user):
        raise NotImplementedError('get_or_create_local_user() has not been implemented.')



class FirebaseAuthentication(BaseFirebaseAuthentication):
    """
    Clients should authenticate by passing the token key in the
    'Authorization' HTTP header, prepended with the string specified in the
    settings.FIREBASE_AUTH_HEADER_PREFIX setting (Default = 'JWT')
    """
    www_authenticate_realm = 'api'

    def get_token(self, request):
        """
        Parse Authorization header and retrieve JWT
        """
        id_token = settings.FIREBASE_AUTH_TOKEN_FIELD
        authorization_token = request.data.get(id_token)
        if not authorization_token:
            raise exceptions.AuthenticationFailed(
                'Invalid Authorization token'
            )

        return authorization_token

    def decode_token(self, firebase_token):
        """
        Attempt to verify JWT from Authorization header with Firebase and
        return the decoded token
        """
        try:
            return firebase_auth.verify_id_token(
                firebase_token,
                check_revoked=settings.FIREBASE_CHECK_JWT_REVOKED
            )
        except ValueError as exc:
            raise exceptions.AuthenticationFailed(
                'JWT was found to be invalid, or the App’s project ID cannot '
                'be determined.'
            )
        except Exception as exc:
            if exc.code == 'ID_TOKEN_REVOKED':
                raise exceptions.AuthenticationFailed(
                    'Token revoked, inform the user to reauthenticate or '
                    'signOut().'
                )
            else:
                raise exceptions.AuthenticationFailed(
                    'Token is invalid.'
                )

    def authenticate_token(self, decoded_token):
        """
        Returns firebase user if token is authenticated
        """
        try:
            uid = decoded_token.get('uid')
            firebase_user = firebase_auth.get_user(uid)
            if settings.FIREBASE_AUTH_EMAIL_VERIFICATION:
                if not firebase_user.email_verified:
                    raise exceptions.AuthenticationFailed(
                        'Email address of this user has not been verified.'
                    )
            return firebase_user
        except ValueError:
            raise exceptions.AuthenticationFailed(
                'User ID is None, empty or malformed'
            )
        except Exception as ex:
            raise exceptions.AuthenticationFailed(
                'Error retrieving the user, or the specified user ID does not '
                'exist'
            )

    def get_or_create_local_user(self, firebase_user):
        """
        Attempts to return or create a local User from Firebase user data
        """
        logger.debug(firebase_user.__dict__)
        email = firebase_user.email if firebase_user.email \
            else firebase_user.provider_data[0].email
        phone_number = firebase_user.phone_number
        photo_url = firebase_user.photo_url

        try:
            user = User.objects.get(phone_number=phone_number)
            if not user.is_active:
                raise exceptions.AuthenticationFailed(
                    'User account is not currently active.'
                )
            user.last_login = timezone.now()
            user.save()
            return user
        except User.DoesNotExist:
            first_name = firebase_user.display_name.split()[:1] if firebase_user.display_name else ""
            last_name = firebase_user.display_name.split()[1:] if firebase_user.display_name else ""
            uid = firebase_user.uid
            #refresh_token = firebase_user.referesh_token
            username = '_'.join(
                firebase_user.display_name.split(' ') if firebase_user.display_name \
                    else str(uuid.uuid4())
            )
            username = username if len(username) <= 30 else username[:30]
            new_user = User.objects.create_user(
                username=username,
                email=email,
                first_name=first_name,
                last_name=last_name,
                uid=uid,
                phone_number=phone_number
            )
            return new_user

    def authenticate_header(self, request):
        """
        Return a string to be used as the value of the `WWW-Authenticate`
        header in a `401 Unauthenticated` response, or `None` if the
        authentication scheme should return `403 Permission Denied` responses.
        """
        auth_header_prefix = settings.FIREBASE_AUTH_HEADER_PREFIX.lower()
        return '{0} realm="{1}"'.format(auth_header_prefix, self.www_authenticate_realm)

