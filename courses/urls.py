from django.urls import path
from .views import (
    create_course, 
    EnrollInCourseView, 
    SubmitQuizView, 
    StudentDashboardView,
    TeacherDashboardListView,      
    TeacherEnrolledStudentsView,
    SubmitAssignmentView,          
    ViewTeacherAssignmentsView,   
    CoursePlaylistView,
    fiverr_course_details_api,
    graphics_course_details_api,
    infosec_course_details_api,
    teacher_verification_status_api  # <--- Teacher verification status view import
)

urlpatterns = [
    # --- Static / Specific Paths (Hamesha upar hone chahiye) ---
    path('create/', create_course, name='create_course'),
    path('dashboard/', StudentDashboardView.as_view(), name='student-dashboard'),
    path('teacher/dashboard/', TeacherDashboardListView.as_view(), name='teacher-dashboard'),
    
    # --- Specific Course & Status APIs ---
    path('fiverr/', fiverr_course_details_api, name='fiverr-course-details'),
    path('graphics/', graphics_course_details_api, name='graphics-course-details'),
    path('infosec/', infosec_course_details_api, name='infosec-course-details'),
    path('teacher/verification-status/', teacher_verification_status_api, name='teacher-verification-status'),  # <--- Status route added

    # --- Dynamic / Parameterized Paths (<int:course_id>) ---
    path('courses/<int:course_id>/playlist/', CoursePlaylistView.as_view(), name='ayesha-course-playlist'),
    path('<int:course_id>/enroll/', EnrollInCourseView.as_view(), name='enroll-course'),
    path('<int:course_id>/submit-quiz/', SubmitQuizView.as_view(), name='submit-quiz'),
    path('<int:course_id>/submit-assignment/', SubmitAssignmentView.as_view(), name='submit-assignment'),
    
    # --- Teacher Dynamic Paths ---
    path('teacher/course/<int:course_id>/students/', TeacherEnrolledStudentsView.as_view(), name='teacher-enrolled-students'),
    path('teacher/course/<int:course_id>/assignments/', ViewTeacherAssignmentsView.as_view(), name='view-assignments'),
]