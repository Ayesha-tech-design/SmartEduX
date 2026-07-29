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
    teacher_verification_status_api,
    generate_mcqs_view
)

urlpatterns = [
    path('create/', create_course, name='create_course'),
    path('enroll/<int:course_id>/', EnrollInCourseView.as_view(), name='enroll_course'),
    path('submit-quiz/<int:course_id>/', SubmitQuizView.as_view(), name='submit_quiz'),
    path('student-dashboard/', StudentDashboardView.as_view(), name='student_dashboard'),
    path('teacher-dashboard/', TeacherDashboardListView.as_view(), name='teacher_dashboard'),
    path('teacher/enrolled-students/<int:course_id>/', TeacherEnrolledStudentsView.as_view(), name='teacher_enrolled_students'),
    path('submit-assignment/<int:course_id>/', SubmitAssignmentView.as_view(), name='submit_assignment'),
    path('teacher/assignments/<int:course_id>/', ViewTeacherAssignmentsView.as_view(), name='view_teacher_assignments'),
    path('playlist/<int:course_id>/', CoursePlaylistView.as_view(), name='course_playlist'),
    path('fiverr-details/', fiverr_course_details_api, name='fiverr_details'),
    path('graphics-details/', graphics_course_details_api, name='graphics_details'),
    path('infosec-details/', infosec_course_details_api, name='infosec_details'),
    path('teacher-status/', teacher_verification_status_api, name='teacher_status'),
    
    # MCQ Generator Endpoints
    path('mcqs/generate/', generate_mcqs_view, name='generate_mcqs_api'),
    path('generate-mcqs/', generate_mcqs_view, name='generate_mcqs_alt'),
]