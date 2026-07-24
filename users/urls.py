from django.urls import path
from .views import (
    signup, 
    login_check, 
    UserProfileUpdateView,
    admin_dashboard_stats, 
    approve_teacher, 
    reject_teacher, 
    create_course,
    update_admin_profile,
    change_admin_password,
    student_assignments,       # <-- Added
    complete_assignment        # <-- Added
)

urlpatterns = [
    # Auth & Profile Routes
    path('signup/', signup, name='signup'),
    path('login-check/', login_check, name='login_check'),
    path('profile/', UserProfileUpdateView.as_view(), name='profile-update'),

    # Admin Dashboard API Routes
    path('admin/dashboard-stats/', admin_dashboard_stats, name='admin_dashboard_stats'),
    path('admin/approve-teacher/', approve_teacher, name='approve_teacher'),
    path('admin/reject-teacher/', reject_teacher, name='reject_teacher'),
    path('admin/create-course/', create_course, name='create_course'),

    # Admin Profile API Routes
    path('admin/update-profile/', update_admin_profile, name='update_admin_profile'),
    path('admin/change-password/', change_admin_password, name='change_admin_password'),

    # Student Assignments API Routes
    path('student/assignments/', student_assignments, name='student_assignments'),
    path('student/complete-assignment/', complete_assignment, name='complete_assignment'),
]