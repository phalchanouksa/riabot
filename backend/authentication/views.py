from rest_framework import status, generics, permissions
from rest_framework.decorators import api_view, permission_classes
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from django.contrib.auth import authenticate
from django.views.decorators.csrf import ensure_csrf_cookie, csrf_protect
from django.utils.decorators import method_decorator
from django.middleware.csrf import get_token
from .models import User
from .serializers import UserRegistrationSerializer, UserSerializer, LoginSerializer, UserUpdateSerializer, PasswordChangeSerializer
from .cookie_auth import set_jwt_cookies, clear_jwt_cookies

@method_decorator(csrf_protect, name='dispatch')
class RegisterView(generics.CreateAPIView):
    queryset = User.objects.all()
    permission_classes = (permissions.AllowAny,)
    serializer_class = UserRegistrationSerializer

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        remember_me = request.data.get('remember_me', False)
        
        # If remember me is checked, extend token lifetimes
        if remember_me:
            from datetime import timedelta
            # Set extended lifetimes for remember me (30 days)
            refresh.set_exp(lifetime=timedelta(days=30))
            refresh.access_token.set_exp(lifetime=timedelta(days=30))
        
        response = Response({
            'user': UserSerializer(user).data,
            'message': 'User created successfully'
        }, status=status.HTTP_201_CREATED)
        
        # Set JWT tokens as httpOnly cookies
        return set_jwt_cookies(response, str(refresh.access_token), str(refresh), remember_me)

@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@ensure_csrf_cookie
@csrf_protect
def login_view(request):
    serializer = LoginSerializer(data=request.data)
    if serializer.is_valid():
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        remember_me = request.data.get('remember_me', False)
        print(f"Login request - remember_me: {remember_me}")
        
        user = authenticate(email=email, password=password)
        if user and user.is_active:
            refresh = RefreshToken.for_user(user)
            
            # If remember me is checked, extend token lifetimes
            if remember_me:
                from datetime import timedelta
                # Set extended lifetimes for remember me (30 days)
                refresh.set_exp(lifetime=timedelta(days=30))
                refresh.access_token.set_exp(lifetime=timedelta(days=30))
            
            response = Response({
                'user': UserSerializer(user).data,
                'message': 'Login successful'
            })
            # Set JWT tokens as httpOnly cookies with remember_me option
            return set_jwt_cookies(response, str(refresh.access_token), str(refresh), remember_me)
        else:
            return Response({
                'error': 'Invalid credentials.'
            }, status=status.HTTP_401_UNAUTHORIZED)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@method_decorator(csrf_protect, name='dispatch')
class ProfileView(generics.RetrieveUpdateAPIView):
    permission_classes = [permissions.IsAuthenticated]
    serializer_class = UserUpdateSerializer

    def get_object(self):
        return self.request.user

    def retrieve(self, request, *args, **kwargs):
        instance = self.get_object()
        serializer = UserSerializer(instance)
        return Response(serializer.data)
    
    def update(self, request, *args, **kwargs):
        partial = kwargs.pop('partial', False)
        instance = self.get_object()
        serializer = self.get_serializer(instance, data=request.data, partial=partial)
        serializer.is_valid(raise_exception=True)
        self.perform_update(serializer)
        
        # Return updated user data using UserSerializer
        response_serializer = UserSerializer(instance)
        return Response(response_serializer.data)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@csrf_protect
def change_password_view(request):
    """
    Change user password
    """
    serializer = PasswordChangeSerializer(data=request.data, context={'request': request})
    if serializer.is_valid():
        user = request.user
        user.set_password(serializer.validated_data['new_password'])
        user.save()
        
        return Response({
            'message': 'Password changed successfully'
        }, status=status.HTTP_200_OK)
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['POST'])
@permission_classes([permissions.IsAuthenticated])
@csrf_protect
def logout_view(request):
    """
    Logout view that clears httpOnly cookies
    """
    response = Response({
        'message': 'Logout successful'
    }, status=status.HTTP_200_OK)
    
    return clear_jwt_cookies(response)


@api_view(['GET'])
@permission_classes([permissions.AllowAny])
@ensure_csrf_cookie
def csrf_token_view(request):
    """
    Get CSRF token for frontend
    """
    from django.middleware.csrf import get_token
    csrf_token = get_token(request)
    response = Response({'csrfToken': csrf_token})
    # Ensure CSRF cookie is set
    response.set_cookie(
        'csrftoken',
        csrf_token,
        max_age=31449600,  # 1 year
        httponly=False,  # Must be False so frontend can read it
        secure=False,  # Set to True in production with HTTPS
        samesite='Lax'
    )
    return response


@api_view(['POST'])
@permission_classes([permissions.AllowAny])
@ensure_csrf_cookie
@csrf_protect
def refresh_token_view(request):
    """
    Custom token refresh view that works with httpOnly cookies
    """
    from rest_framework_simplejwt.tokens import RefreshToken
    from rest_framework_simplejwt.exceptions import TokenError
    from django.conf import settings
    
    refresh_token = request.COOKIES.get(settings.JWT_AUTH_REFRESH_COOKIE)
    
    if not refresh_token:
        return Response({
            'error': 'Refresh token not found'
        }, status=status.HTTP_401_UNAUTHORIZED)
    
    try:
        refresh = RefreshToken(refresh_token)
        access_token = str(refresh.access_token)
        
        response = Response({
            'message': 'Token refreshed successfully'
        })
        
        # Set new access token cookie
        response.set_cookie(
            settings.JWT_AUTH_COOKIE,
            access_token,
            max_age=settings.SIMPLE_JWT['ACCESS_TOKEN_LIFETIME'].total_seconds(),
            httponly=settings.JWT_AUTH_COOKIE_HTTP_ONLY,
            secure=settings.JWT_AUTH_COOKIE_SECURE,
            samesite=settings.JWT_AUTH_COOKIE_SAMESITE
        )
        
        return response
        
    except TokenError:
        response = Response({
            'error': 'Invalid refresh token'
        }, status=status.HTTP_401_UNAUTHORIZED)
        return clear_jwt_cookies(response)

