from django.urls import path
from .views import (
    signup, 
    login_check, 
    UserProfileUpdateView,
    admin_dashboard_stats, 
    admin_pending_teachers_api,
    approve_teacher, 
    reject_teacher, 
    admin_recent_activities_api,
    admin_system_backup_api,
    admin_save_settings_api,
    create_course,
    update_admin_profile,
    change_admin_password,
    student_assignments,
    complete_assignment,
    student_profile_api, 
    get_user_profile, 
    user_list_view, 
    wordpress_profile_api, 
    reset_password_api, 
    forgot_password_api,
    certificate_data_api
)

urlpatterns = [
    # General & User List
    path('', user_list_view, name='user_list'),

    # Auth & Profile Routes
    path('signup/', signup, name='signup'),
    path('login-check/', login_check, name='login_check'),
    path('profile/', UserProfileUpdateView.as_view(), name='profile-update'),
    path('user-profile/', get_user_profile, name='user_profile_api'),
    path('wordpress-profile/', wordpress_profile_api, name='wordpress_profile_api'),
    path('reset-password/', reset_password_api, name='reset_password_api'),
    path('forgot-password/', forgot_password_api, name='forgot_password_api'),
    path('certificate-data/', certificate_data_api, name='certificate_data_api'),

    # Admin Dashboard API Routes
    path('admin/stats/', admin_dashboard_stats, name='admin_dashboard_stats'),
    path('admin/dashboard-stats/', admin_dashboard_stats, name='admin_dashboard_stats_alt'),
    path('admin/pending-teachers/', admin_pending_teachers_api, name='admin_pending_teachers'),
    path('admin/approve-teacher/', approve_teacher, name='approve_teacher_base'),
    path('admin/approve-teacher/<int:teacher_id>/', approve_teacher, name='approve_teacher_id'),
    path('admin/reject-teacher/', reject_teacher, name='reject_teacher'),
    path('admin/recent-activities/', admin_recent_activities_api, name='admin_recent_activities'),
    path('admin/backup/', admin_system_backup_api, name='admin_system_backup'),
    path('admin/settings/', admin_save_settings_api, name='admin_save_settings'),
    path('admin/create-course/', create_course, name='create_course'),

    # Admin Profile API Routes
    path('admin/update-profile/', update_admin_profile, name='update_admin_profile'),
    path('admin/change-password/', change_admin_password, name='change_admin_password'),

    # Student Assignments API Routes
    path('student/assignments/', student_assignments, name='student_assignments'),
    path('student/complete-assignment/', complete_assignment, name='complete_assignment'),
]