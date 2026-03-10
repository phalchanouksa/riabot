from rest_framework_simplejwt.authentication import JWTAuthentication
from rest_framework_simplejwt.exceptions import InvalidToken, TokenError
from django.conf import settings
from django.http import JsonResponse
from datetime import datetime, timedelta
import jwt


class CookieJWTAuthentication(JWTAuthentication):
    """
    Custom JWT authentication that reads tokens from httpOnly cookies
    """
    def authenticate(self, request):
        header = self.get_header(request)
        if header is not None:
            # If Authorization header is present, use default behavior
            raw_token = self.get_raw_token(header)
        else:
            # Try to get token from cookie
            raw_token = request.COOKIES.get(settings.JWT_AUTH_COOKIE)
            
        if raw_token is None:
            return None

        try:
            validated_token = self.get_validated_token(raw_token)
            return self.get_user(validated_token), validated_token
        except InvalidToken:
            # Token is invalid, treat as anonymous user
            # This allows public endpoints to be accessed even with an invalid token
            return None


def set_jwt_cookies(response, access_token, refresh_token, remember_me=False):
    """
    Helper function to set JWT tokens as httpOnly cookies
    """
    # Add debugging
    print(f"Setting cookies with remember_me: {remember_me}")
    
    # Calculate cookie max_age based on remember_me option
    if remember_me:
        # Extended lifetime for remember me (30 days)
        access_max_age = 60 * 60 * 24 * 30  # 30 days
        refresh_max_age = 60 * 60 * 24 * 30  # 30 days
        print(f"Using extended lifetime: {access_max_age} seconds (30 days)")
    else:
        # Default lifetime
        access_max_age = settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds()
        refresh_max_age = settings.SIMPLE_JWT['REFRESH_TOKEN_LIFETIME'].total_seconds()
        print(f"Using default lifetime: access={access_max_age}, refresh={refresh_max_age}")
    
    # Set access token cookie
    response.set_cookie(
        settings.JWT_AUTH_COOKIE,
        access_token,
        max_age=int(access_max_age),
        httponly=settings.JWT_AUTH_COOKIE_HTTP_ONLY,
        secure=settings.JWT_AUTH_COOKIE_SECURE,
        samesite=settings.JWT_AUTH_COOKIE_SAMESITE
    )
    
    # Set refresh token cookie
    response.set_cookie(
        settings.JWT_AUTH_REFRESH_COOKIE,
        refresh_token,
        max_age=int(refresh_max_age),
        httponly=settings.JWT_AUTH_COOKIE_HTTP_ONLY,
        secure=settings.JWT_AUTH_COOKIE_SECURE,
        samesite=settings.JWT_AUTH_COOKIE_SAMESITE
    )
    
    return response


def clear_jwt_cookies(response):
    """
    Helper function to clear JWT cookies on logout
    """
    response.delete_cookie(settings.JWT_AUTH_COOKIE)
    response.delete_cookie(settings.JWT_AUTH_REFRESH_COOKIE)
    return response


def get_csrf_token_view(request):
    """
    View to get CSRF token for frontend
    """
    from django.middleware.csrf import get_token
    csrf_token = get_token(request)
    return JsonResponse({'csrfToken': csrf_token})
