from django.utils import timezone
from django.contrib.auth import authenticate
from rest_framework import status, permissions
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.exceptions import TokenError
from apps.accounts.serializers import RegisterSerializer, LoginSerializer, ChangePasswordSerializer
from core.throttles import LoginRateLimitThrottle
from core.exceptions import InvalidOperationException

class RegisterView(APIView):
    permission_classes = [permissions.AllowAny]

    def post(self, request, *args, **kwargs):
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        
        refresh = RefreshToken.for_user(user)
        return Response({
            "id": user.id,
            "username": user.username,
            "email": user.email,
            "full_name": user.full_name,
            "role": user.role,
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh)
        }, status=status.HTTP_201_CREATED)


class LoginView(APIView):
    permission_classes = [permissions.AllowAny]
    throttle_classes = [LoginRateLimitThrottle]

    def post(self, request, *args, **kwargs):
        serializer = LoginSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        email = serializer.validated_data['email']
        password = serializer.validated_data['password']
        
        throttle = LoginRateLimitThrottle()
        ip = throttle.get_ident(request)
        
        user = authenticate(request, username=email, password=password)
        
        if user is None:
            LoginRateLimitThrottle.record_failed_attempt(ip)
            return Response({
                "timestamp": timezone.now().isoformat(),
                "status": 401,
                "error_code": "NOT_AUTHENTICATED",
                "message": "Invalid email or password.",
                "path": request.path,
                "errors": []
            }, status=status.HTTP_401_UNAUTHORIZED)
            
        if not user.is_active:
            LoginRateLimitThrottle.record_failed_attempt(ip)
            return Response({
                "timestamp": timezone.now().isoformat(),
                "status": 403,
                "error_code": "PERMISSION_DENIED",
                "message": "This account is inactive.",
                "path": request.path,
                "errors": []
            }, status=status.HTTP_403_FORBIDDEN)
            
        user.last_login_at = timezone.now()
        user.save(update_fields=['last_login_at'])
        LoginRateLimitThrottle.clear_attempts(ip)
        
        refresh = RefreshToken.for_user(user)
        return Response({
            "access_token": str(refresh.access_token),
            "refresh_token": str(refresh),
            "user_id": user.id,
            "username": user.username,
            "role": user.role
        }, status=status.HTTP_200_OK)


class LogoutView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        refresh_token = request.data.get('refresh_token')
        if not refresh_token:
            return Response({
                "timestamp": timezone.now().isoformat(),
                "status": 400,
                "error_code": "VALIDATION_FAILED",
                "message": "refresh_token is required.",
                "path": request.path,
                "errors": [{"field": "refresh_token", "message": "This field is required."}]
            }, status=status.HTTP_400_BAD_REQUEST)
            
        try:
            token = RefreshToken(refresh_token)
            token.blacklist()
            return Response(status=status.HTTP_200_OK)
        except TokenError as e:
            return Response({
                "timestamp": timezone.now().isoformat(),
                "status": 400,
                "error_code": "INVALID_OPERATION",
                "message": str(e),
                "path": request.path,
                "errors": []
            }, status=status.HTTP_400_BAD_REQUEST)


class ChangePasswordView(APIView):
    permission_classes = [permissions.IsAuthenticated]

    def post(self, request, *args, **kwargs):
        serializer = ChangePasswordSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        
        user = request.user
        old_password = serializer.validated_data['old_password']
        new_password = serializer.validated_data['new_password']
        
        if not user.check_password(old_password):
            return Response({
                "timestamp": timezone.now().isoformat(),
                "status": 400,
                "error_code": "VALIDATION_FAILED",
                "message": "Invalid old password.",
                "path": request.path,
                "errors": [{"field": "old_password", "message": "Invalid password."}]
            }, status=status.HTTP_400_BAD_REQUEST)
            
        user.set_password(new_password)
        user.save()
        return Response(status=status.HTTP_200_OK)
