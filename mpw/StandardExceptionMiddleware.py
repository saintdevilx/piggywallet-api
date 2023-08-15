import logging, sys

from django import http
from django.conf import settings
from django.core.mail import mail_admins
# Temporary, from http://code.djangoproject.com/attachment/ticket/6094/6094.2008-02-01.diff

from django.http import Http404
from django.utils.deprecation import MiddlewareMixin

logger = logging.getLogger('application')


class StandardExceptionMiddleware(MiddlewareMixin):
    def process_exception(self, request, exception):
        # Get the exception info now, in case another exception is thrown later.
        # don't track Http404 error to email let it normally return ignore email for 404
        if isinstance(exception, Exception) and not isinstance(exception, Http404):
            return self.handle_500(request, exception)

    def handle_500(self, request, exception):
        exc_info = sys.exc_info()
        if settings.DEBUG:
            return self.debug_500_response(request, exception, exc_info)
        else:
            if settings.ON_PRODUCTION:
                # disabling sentry for now in case you
                pass
                # sentry_exception_handler(request=request)
            self.log_exception(request, exception, exc_info)
            return http.HttpResponse("There was an error. Please contact support at tech@mypiggywallet.com", status=500)

    def debug_500_response(self, request, exception, exc_info):
        """
        :param request: 
        :type request: django.core.handlers.wsgi.WSGIRequest
        :param exception: 
        :type exception: Union[django.db.models.fields.related.RelatedObjectDoesNotExist, users.models.DoesNotExist, elasticsearch.exceptions.NotFoundError, exceptions.AttributeError]
        :param exc_info: 
        :type exc_info: Union[Tuple[type, django.db.models.fields.related.RelatedObjectDoesNotExist, traceback], Tuple[type, users.models.DoesNotExist, traceback], Tuple[type, users.models.DoesNotExist, traceback], Tuple[type, users.models.DoesNotExist, traceback], Tuple[type, users.models.DoesNotExist, traceback], Tuple[type, elasticsearch.exceptions.NotFoundError, traceback], Tuple[type, elasticsearch.exceptions.NotFoundError, traceback], Tuple[type, elasticsearch.exceptions.NotFoundError, traceback], Tuple[type, elasticsearch.exceptions.NotFoundError, traceback], Tuple[type, exceptions.AttributeError, traceback]]
        :return: 
        :rtype: django.http.response.HttpResponseServerError
        """
        from django.views import debug
        try:
            request_repr = repr(request)
        except:
            request_repr = "Request repr() unavailable"
        message = "%s\n\n%s" % (_get_traceback(exc_info), request_repr)
        logger.debug('Debug 500 message: ' + message)
        logger.debug('Exception :' + str(exception))
        return debug.technical_500_response(request, *exc_info)

    def exception_email(self, request, exc_info):
        if request.user.is_authenticated:
            username = request.user.phone_number
        else:
            username = "anon_user"
        subject = 'Error with user ' + str(username)
        try:
            request_repr = repr(request)
        except:
            request_repr = "Request repr() unavailable"
        message = "%s\n\n%s" % (_get_traceback(exc_info), request_repr)
        return subject, message

    def log_exception(self, request, exception, exc_info):
        if settings.ON_PRODUCTION:
            subject, message = self.exception_email(request, exc_info)
            mail_admins(subject, message, fail_silently=True)
        try:
            request_repr = repr(request)
        except:
            request_repr = "Request repr() unavailable"
        if request.user.is_authenticated:
            username = request.user.username
        else:
            username = "anon_user"
        logger.error("Error with user " + username + " " + request_repr + " & " + _get_traceback(exc_info))


def _get_traceback(exc_info=None):
    """Helper function to return the traceback as a string"""
    import traceback
    return '\n'.join(traceback.format_exception(*(exc_info or sys.exc_info())))
