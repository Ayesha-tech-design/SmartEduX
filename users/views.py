from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth import get_user_model, authenticate
import json
from rest_framework_simplejwt.tokens import RefreshToken  # Token generate karne ke liye
from rest_framework.response import Response
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from .serializers import UserProfileSerializer
from django.contrib.auth.models import User

User = get_user_model()

@csrf_exempt
def signup(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            if not data.get("username") or not data.get("password"):
                return JsonResponse({"error": "Username and password are required"}, status=400)

            user = User.objects.create_user(
                username=data["username"],
                password=data["password"],
                role=data.get("role", "student"),
                qualification=data.get("qualification"),
                experience_years=data.get("experience_years", 0),
            )
            
            return JsonResponse({
                "message": "User created successfully", 
                "user": user.username,
                "role": user.role
            }, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Only POST allowed"}, status=405)


@csrf_exempt
def login_check(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            username = data.get("username")
            password = data.get("password")

            if not username or not password:
                return JsonResponse({"error": "Username and password are required"}, status=400)

            user = authenticate(username=username, password=password)
            
            if user is not None:
                if not user.is_approved:
                    return JsonResponse({"error": "Your account is pending admin approval."}, status=403)

                refresh = RefreshToken.for_user(user)
                
                return JsonResponse({
                    "message": "Login successful",
                    "access": str(refresh.access_token),
                    "refresh": str(refresh),
                    "user": user.username,
                    "role": user.role,
                    "is_approved": user.is_approved
                }, status=200)
                
            return JsonResponse({"error": "Invalid credentials"}, status=401)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    return JsonResponse({"error": "Only POST allowed"}, status=405)


class UserProfileUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_dashboard_api(request):
    user = request.user
    data = {
        "welcome_name": user.first_name if hasattr(user, 'first_name') and user.first_name else user.username,
        "course_count": 0,      
        "assignment_count":   0, 
        "gpa": 0.0,              # Naye user ke liye 0 GPA
        "progress": "0%",        # Naye user ke liye 0% progress
        "certifications": 0,     # Naye user ke liye 0 certifications
        "courses": []            # Naye user ke liye empty courses list
    }
    return Response(data)


@api_view(['GET', 'PUT'])
@permission_classes([IsAuthenticated])
def student_profile_api(request):
    user = request.user
    if request.method == 'GET':
        display_name = user.first_name if (hasattr(user, 'first_name') and user.first_name) else user.username
        data = {
            "full_name": display_name,
            "username": user.username,
            "email": user.email,
            "registration_number": getattr(user, 'registration_number', ''),
            "department": getattr(user, 'department', ''),
            "profile_image": getattr(user, 'profile_image', None)
        }
        return Response(data)
    
    elif request.method == 'PUT':
        user.first_name = request.data.get("full_name", user.first_name)
        user.email = request.data.get("email", user.email)
        if hasattr(user, 'registration_number'):
            user.registration_number = request.data.get("registration_number", user.registration_number)
        if hasattr(user, 'department'):
            user.department = request.data.get("department", user.department)
        user.save()
        return Response({"success": "Profile updated successfully!"})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def notifications_api(request):
    return Response([])


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_user_profile(request):
    user = request.user
    data = {
        "first_name": user.first_name,
        "last_name": user.last_name,
        "email": user.email,
        "role": "Teacher" if getattr(user, 'role', '') == 'teacher' else user.role
    }
    return JsonResponse(data)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def teacher_dashboard_api(request):
    user = request.user
    data = {
        "welcome_name": user.first_name if hasattr(user, 'first_name') and user.first_name else user.username,
        "course_count": 3,
        "assignment_count": 12,
        "student_count": 150,
        "pending_submissions": 8,
        "certifications_awarded": 2
    }
    return Response(data)


@api_view(['GET'])
def get_notifications_api(request):
    notifications = [
        {"message": "New student registered 👨‍🎓"},
        {"message": "New assignment submission 📄"},
        {"message": "Course updated 🎓"},
        {"message": "Website updated 🚀"}
    ]
    return Response(notifications)


@api_view(['GET', 'POST'])
def teacher_courses_api(request):
    if request.method == 'GET':
        courses = [
            {"id": 1, "name": "Graphic Designing", "students": 25, "status": "Active"},
            {"id": 2, "name": "Wordpress Web Dev", "students": 40, "status": "Active"},
            {"id": 3, "name": "Fiverr Freelancing", "students": 30, "status": "Inactive"},
            {"id": 4, "name": "JavaScript Advanced", "students": 20, "status": "Active"}
        ]
        return Response(courses)
    
    elif request.method == 'POST':
        course_name = request.data.get('name')
        return Response({"success": True, "message": "Course added successfully!"})


@api_view(['PUT', 'DELETE'])
def modify_teacher_course_api(request, course_id):
    if request.method == 'PUT':
        return Response({"success": True, "message": "Course updated successfully!"})
    
    elif request.method == 'DELETE':
        return Response({"success": True, "message": "Course deleted successfully!"})


def user_list_view(request):
    users = User.objects.all()
    data = []
    for u in users:
        data.append({
            "name": f"{u.first_name} {u.last_name}".strip() or u.username,
            "email": u.email or "N/A",
            "role": "Admin" if u.is_superuser else ("Teacher" if u.is_staff else "Student"),
            "status": "Active" if u.is_active else "Inactive"
        })
    return JsonResponse(data, safe=False)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def wordpress_profile_api(request):
    user = request.user
    data = {
        "username": user.username,
        "has_purchased": getattr(user, 'has_purchased', False),
        "is_premium": getattr(user, 'is_premium', False)
    }
    return Response(data)


@api_view(['POST'])
@permission_classes([AllowAny])
def reset_password_api(request):
    email = request.data.get('email')
    new_password = request.data.get('new_password')

    if not email or not new_password:
        return Response({"error": "Email and new password are required."}, status=400)

    try:
        user = User.objects.get(email=email)
        user.set_password(new_password)
        user.save()
        return Response({"success": "Password updated successfully!"}, status=200)
    except User.DoesNotExist:
        return Response({"error": "User with this email does not exist."}, status=404)
@api_view(['POST'])
@permission_classes([AllowAny])
def forgot_password_api(request):
    email = request.data.get('email')

    if not email:
        return Response({"error": "Email is required."}, status=400)

    try:
        user = User.objects.get(email=email)
        # Yahan aap email sending logic (jaise Django send_mail) bhi laga sakti hain agar chahyein
        return Response({"success": "Email verified successfully!"}, status=200)
    except User.DoesNotExist:
        return Response({"error": "This email is not registered with SmartEduX!"}, status=404)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def certificate_data_api(request):
    user = request.user
    display_name = user.first_name if (hasattr(user, 'first_name') and user.first_name) else user.username
    
    # Aap yahan user ke completed courses database se fetch kar sakti hain
    data = {
        "full_name": display_name,
        "email": user.email,
        "course_name": getattr(user, 'completed_course', 'Graphics Designing')
    }
    return Response(data)