from django.contrib import admin
from django.urls import path, include
from django.views.generic import TemplateView
from rest_framework_simplejwt.views import TokenObtainPairView, TokenRefreshView
from users.views import (
    signup, 
    student_dashboard_api, 
    notifications_api, 
    student_profile_api, 
    get_user_profile, 
    teacher_dashboard_api, 
    teacher_courses_api, 
    modify_teacher_course_api
)

urlpatterns = [
    # 1. Admin Panel
    path('admin/', admin.site.urls),

    # 2. Static Template Serving (About Us)
    path('about/', TemplateView.as_view(template_name='About us.html'), name='about_page'),

    # 3. JWT Token Endpoints (Login & Refresh)
    path('api/token/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # 4. Users App Routes
    path('api/', include('users.urls')),

    # 5. AI Notes Generator Route
    path('api/notes/', include('notes.urls')),

    # 6. Courses App Routes 
    path('api/courses/', include('courses.urls')),

    # 7. Auth Routes (Login, Signup & Refresh)
    path('api/auth/signup/', signup, name='signup_auth'),
    path('api/auth/login/', TokenObtainPairView.as_view(), name='token_obtain_pair'),
    path('api/auth/token/refresh/', TokenRefreshView.as_view(), name='token_refresh'),

    # 8. Student Dashboard, Profile & Notifications Routes
    path('api/student/dashboard/', student_dashboard_api, name='student_dashboard_api'),
    path('api/teacher/dashboard/', teacher_dashboard_api, name='teacher_dashboard_api'), 
    path('api/student/profile/', student_profile_api, name='student_profile_api'),
    path('api/notifications/', notifications_api, name='notifications_api'),
    path('api/teacher/courses/', teacher_courses_api, name='teacher_courses_api'),
    path('api/teacher/courses/add/', teacher_courses_api, name='add_teacher_course_api'),
    path('api/teacher/courses/edit/<int:course_id>/', modify_teacher_course_api, name='edit_teacher_course_api'),
    path('api/teacher/courses/delete/<int:course_id>/', modify_teacher_course_api, name='delete_teacher_course_api'),
    
    # 9. Profile Fetch Routes
    path('api/user-profile/', get_user_profile, name='user_profile_api'),
    path('api/teacher-profile/', get_user_profile, name='teacher_profile_api'),
]