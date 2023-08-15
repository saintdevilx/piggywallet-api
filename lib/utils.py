import base64
import hmac
import logging
import time
import urllib
from _sha1 import sha1
from datetime import datetime
from urllib.parse import quote_plus, urlparse, parse_qs

import firebase_admin
import jwt
from botocore.config import Config
from django.core.files.base import ContentFile
from firebase_admin import auth
from rest_framework import status
from rest_framework.response import Response

from api.user.exceptions import InvalidJWTToken
from mpw import settings

logger = logging.getLogger('application')

import boto3
from botocore.exceptions import ClientError


def create_presigned_post(bucket_name, object_name,
                          fields=None, conditions=None, expiration=3600, access_control='public-read', method='put'):
    """Generate a presigned URL S3 POST request to upload a file

    :param bucket_name: string
    :param object_name: string
    :param fields: Dictionary of prefilled form fields
    :param conditions: List of conditions to include in the policy
    :param expiration: Time in seconds for the presigned URL to remain valid
    :return: Dictionary with the following keys:
        url: URL to post to
        fields: Dictionary of form fields and values to submit with the POST
    :return: None if error.
    """

    # Generate a presigned S3 POST URL
    s3_client = boto3.client('s3', aws_access_key_id=settings.AWS_ACCESS_KEY_ID,
                             aws_secret_access_key=settings.AWS_SECRET_ACCESS_KEY, region_name='ap-south-1',
                             config=Config(signature_version='s3v4'))
    try:
        expires_in = int(time.time() + expiration )
        response = s3_client.generate_presigned_post(bucket_name,
                                                     object_name,
                                                     Fields=fields,
                                                     Conditions=conditions,
                                                     ExpiresIn=expiration)
    except ClientError as e:
        logger.error(e)
        return None
    response['image_url'] = F"{response['url']}{response['fields']['key']}"
    return response

def js_timestamp_date_to_utc_datetime(timestamp):
    return datetime.utcfromtimestamp(timestamp/1000)


def validate_and_decode_firebase_id_token(token):
    try:
        return auth.verify_id_token(token)
    except Exception as ex:
        logger.exception('error while decoding id token')
        return jwt.decode(token, verify=False)


class ErrorResponse(Response):
        def __init__(self, message,**kwargs):
            data = {
                'error': {
                    'message':message,
                    'code': kwargs.pop('error_code') if kwargs.get('error_code') else None
                }
            }
            if not kwargs.get('status'):
                kwargs['status'] = status.HTTP_400_BAD_REQUEST
            super(ErrorResponse, self).__init__(data, **kwargs)


def getContentFileFromBase64(data):
    logger.debug(type(data))
    format, imgstr = data.split(';base64,')
    ext = format.split('/')[-1]
    return ContentFile(base64.b64decode(imgstr), name='temp.' + ext)


def get_jwt_token(payload, algo='HS256'):
    encoded = jwt.encode(payload, settings.SECRET_KEY, algorithm=algo).decode('utf-8')
    return encoded


def verify_jwt_token(token, algo='HS256'):
    try:
        return jwt.decode(token, settings.SECRET_KEY, algorithms=algo)
    except Exception as ex:
        raise InvalidJWTToken(ex)


def get_url_params(url):
    parsed = urlparse(url)
    return parsed.query


def get_url_param(url, name):
    try:
        query = get_url_params(url)
        qs_data = parse_qs(query)
        param = qs_data.get(name)
        if param:
            return param[0]
    except:
        pass