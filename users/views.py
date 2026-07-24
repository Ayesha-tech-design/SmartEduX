from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.contrib.auth import get_user_model, authenticate
import json
from rest_framework_simplejwt.tokens import RefreshToken  # Token generate karne ke liye

User = get_user_model()

@csrf_exempt
def signup(request):
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            # Validation
            if not data.get("username") or not data.get("password"):
                return JsonResponse({"error": "Username and password are required"}, status=400)

            # User Creation
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

            # User authenticate karna
            user = authenticate(username=username, password=password)
            
            if user is not None:
                # Agar user approved nahi hai (Teachers ke liye admin approval lazmi hai)
                if not user.is_approved:
                    return JsonResponse({"error": "Your account is pending admin approval."}, status=403)

                # Asli JWT Tokens generate karna
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


# Django REST Framework Views for Profile (Baari baari baki team ke kaam ke sath sync ho jayega)
from rest_framework import generics
from rest_framework.permissions import IsAuthenticated
from .serializers import UserProfileSerializer

class UserProfileUpdateView(generics.RetrieveUpdateAPIView):
    serializer_class = UserProfileSerializer
    permission_classes = [IsAuthenticated]

    def get_object(self):
        return self.request.user

        from django.shortcuts import render
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
import json

# 1. Admin Dashboard Stats Endpoint
def admin_dashboard_stats(request):
    data = {
        "status": "success",
        "total_users": 120,
        "total_educators": 24,
        "ai_operations": "1,482",
        "pending_approvals": 1
    }
    return JsonResponse(data)

# 2. Approve Teacher Endpoint
@csrf_exempt
def approve_teacher(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            teacher_name = body.get('teacher_name')
            return JsonResponse({"status": "success", "message": f"{teacher_name} approved successfully"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

# 3. Reject Teacher Endpoint
@csrf_exempt
def reject_teacher(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            teacher_name = body.get('teacher_name')
            reason = body.get('reason')
            return JsonResponse({"status": "success", "message": f"{teacher_name} rejected"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

# 4. Create New Course Endpoint
@csrf_exempt
def create_course(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            title = body.get('title')
            return JsonResponse({"status": "success", "message": f"Course {title} deployed"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

            # 5. Admin Update Profile Endpoint
@csrf_exempt
def update_admin_profile(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            full_name = body.get('full_name')
            email = body.get('email')
            # Profile DB Save Logic
            return JsonResponse({"status": "success", "message": "Profile updated successfully"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

# 6. Admin Change Password Endpoint
@csrf_exempt
def change_admin_password(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            # Password Change Logic
            return JsonResponse({"status": "success", "message": "Password changed successfully"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)

            # 7. Student Assignments Endpoint
def student_assignments(request):
    data = {
        "status": "success",
        "assignments": [
            { "id": 1, "title": "UI Design Homework", "course": "Graphic Designing", "due": "2026-04-15", "status": "Pending" },
            { "id": 2, "title": "WordPress Project", "course": "Wordpress Web Development", "due": "2026-04-18", "status": "Pending" },
            { "id": 3, "title": "Freelancing Case Study", "course": "Fiverr Freelancing", "due": "2026-04-20", "status": "Pending" }
        ]
    }
    return JsonResponse(data)

# 8. Complete Student Assignment Endpoint
@csrf_exempt
def complete_assignment(request):
    if request.method == 'POST':
        try:
            body = json.loads(request.body)
            assignment_id = body.get('assignment_id')
            return JsonResponse({"status": "success", "message": f"Assignment {assignment_id} completed"})
        except Exception as e:
            return JsonResponse({"status": "error", "message": str(e)}, status=400)