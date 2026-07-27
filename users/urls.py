from django.urls import path
from .views import signup, login_check, UserProfileUpdateView, student_profile_api, get_user_profile, user_list_view, wordpress_profile_api, reset_password_api, forgot_password_api,certificate_data_api

urlpatterns = [
    path('', user_list_view, name='user_list'),
    path('signup/', signup, name='signup'),
    path('login-check/', login_check, name='login_check'),
    path('profile/', UserProfileUpdateView.as_view(), name='profile-update'),
    path('user-profile/', get_user_profile, name='user_profile_api'),  # Yeh line add kar dein
    path('wordpress-profile/', wordpress_profile_api, name='wordpress_profile_api'),
    path('reset-password/', reset_password_api, name='reset_password_api'),
    path('forgot-password/', forgot_password_api, name='forgot_password_api'),
    path('certificate-data/', certificate_data_api, name='certificate_data_api'),
]