import json
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.views.decorators.http import require_GET
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework import status
from rest_framework.permissions import IsAuthenticated, AllowAny
from rest_framework.decorators import api_view, permission_classes
from rest_framework.parsers import MultiPartParser, FormParser

from .models import Course, Enrollment, Quiz, Certificate, AssignmentSubmission
from .serializers import EnrollmentSerializer, QuizSerializer, CertificateSerializer

# =====================================================================
# DYNAMIC COURSE LIST API (CONNECTED WITH Courses.html)
# =====================================================================

@api_view(['GET'])
@permission_classes([AllowAny])
def course_list_api(request):
    """
    Handles GET /courses/list/ for Courses.html dynamic grid execution
    """
    default_courses = [
        {
            "title": "Graphics Designing",
            "icon": "https://img.icons8.com/ios-filled/24/000000/design.png",
            "desc": "Learn design fundamentals, Photoshop, Illustrator, and create stunning visuals.",
            "img": "design.jpg",
            "link": "graphics.html"
        },
        {
            "title": "WordPress Websites",
            "icon": "https://img.icons8.com/ios-filled/24/000000/wordpress.png",
            "desc": "Build dynamic websites with WordPress, themes, plugins, and hosting basics.",
            "img": "wordpress.jpg",
            "link": "wordpress.html"
        },
        {
            "title": "Fiverr Freelancing",
            "icon": "https://img.icons8.com/ios-filled/24/000000/freelance.png",
            "desc": "Create gigs, attract clients, manage orders, and start earning online.",
            "img": "virtual-assistant-on-fivver.png",
            "link": "fiverr.html"
        },
        {
            "title": "Information Security",
            "icon": "https://img.icons8.com/ios-filled/24/000000/security-checked.png",
            "desc": "Learn cyber security, network protection, cryptography and secure information systems.",
            "img": "information_security.jpg",
            "link": "information_security.html"
        }
    ]
    
    try:
        db_courses = Course.objects.all()
        if db_courses.exists():
            courses_data = []
            for c in db_courses:
                courses_data.append({
                    "title": c.title,
                    "icon": "https://img.icons8.com/ios-filled/24/000000/course.png",
                    "desc": c.description,
                    "img": "design.jpg",
                    "link": "graphics.html"
                })
            return Response({"status": "success", "courses": courses_data}, status=status.HTTP_200_OK)
    except Exception:
        pass

    return Response({"status": "success", "courses": default_courses}, status=status.HTTP_200_OK)


# =====================================================================
# COURSE MANAGEMENT MODULE
# =====================================================================

@csrf_exempt
def create_course(request):
    """
    FR-4: Handles course creation for instructors (POST) and retrieves course list (GET).
    """
    if request.method == "POST":
        try:
            data = json.loads(request.body)
            instructor_id = data.get("instructor", 1) 

            course = Course.objects.create(
                title=data['title'],
                description=data['description'],
                instructor_id=instructor_id 
            )
            return JsonResponse({"message": "Course created successfully", "course_id": course.id}, status=201)
        except Exception as e:
            return JsonResponse({"error": str(e)}, status=400)
    
    courses = list(Course.objects.values())
    return JsonResponse(courses, safe=False)


class EnrollInCourseView(APIView):
    """
    FR-5: Enrolls a student in a specific course.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, course_id):
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)

        if Enrollment.objects.filter(student=request.user, course=course).exists():
            return Response(
                {"message": "You are already enrolled in this course"}, 
                status=status.HTTP_400_BAD_REQUEST
            )

        enrollment = Enrollment.objects.create(student=request.user, course=course)
        serializer = EnrollmentSerializer(enrollment)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

# =====================================================================
# QUIZ & EVALUATION MODULE
# =====================================================================

class SubmitQuizView(APIView):
    """
    FR-13 & FR-14: Handles quiz submission and auto-generates certificates if criteria met.
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, course_id):
        user_answers = request.data.get('answers')
        if not user_answers:
            return Response({"error": "Answers must be provided"}, status=status.HTTP_400_BAD_REQUEST)

        quizzes = Quiz.objects.filter(course_id=course_id)
        total_questions = quizzes.count()
        
        if total_questions == 0:
            return Response({"error": "No quiz available for this course"}, status=404)

        correct_count = 0
        for quiz in quizzes:
            if user_answers.get(str(quiz.id)) == quiz.correct_answer:
                correct_count += 1

        score_percentage = (correct_count / total_questions) * 100

        # SmartEduX Business Rule: Passing score threshold is 80%
        certificate_issued = False
        if score_percentage >= 80:
            certificate, created = Certificate.objects.update_or_create(
                student=request.user,
                course_id=course_id,
                defaults={'score': score_percentage}
            )
            certificate_issued = True

        return Response({
            "score": score_percentage,
            "total_questions": total_questions,
            "correct_answers": correct_count,
            "certificate_issued": certificate_issued,
            "message": "Congratulations! You have earned a certificate." if certificate_issued else "Score too low. Certificate not issued."
        })

# =====================================================================
# DASHBOARD MODULES
# =====================================================================

class StudentDashboardView(APIView):
    """
    FR-15: Fetches enrolled courses and achievements for the active student profile.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        enrollments = Enrollment.objects.filter(student=request.user)
        enrolled_courses = [e.course.title for e in enrollments]

        certs = Certificate.objects.filter(student=request.user)
        earned_certificates = []
        for c in certs:
            earned_certificates.append({
                "course": c.course.title,
                "score": c.score,
                "date": c.issued_at.strftime("%Y-%m-%d")
            })

        return Response({
            "user": request.user.username,
            "enrolled_in": enrolled_courses,
            "my_certificates": earned_certificates,
            "total_achievements": len(earned_certificates)
        })
    

class TeacherDashboardListView(APIView):
    """
    Fetches the list of all courses authored by the authenticated instructor.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request):
        if request.user.role != 'teacher':
            return Response({"error": "Access denied. Only teachers can view this dashboard."}, status=status.HTTP_403_FORBIDDEN)
        
        courses = Course.objects.filter(instructor=request.user)
        
        course_list = []
        for course in courses:
            course_list.append({
                "id": course.id,
                "title": course.title,
                "description": course.description,
                "created_at": course.created_at if hasattr(course, 'created_at') else None
            })
            
        return Response({
            "teacher_name": request.user.username,
            "total_courses": courses.count(),
            "courses": course_list
        }, status=status.HTTP_200_OK)


class TeacherEnrolledStudentsView(APIView):
    """
    Enables instructors to view the list of students enrolled in their courses.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        if request.user.role != 'teacher':
            return Response({"error": "Access denied."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            course = Course.objects.get(id=course_id, instructor=request.user)
        except Course.DoesNotExist:
            return Response({"error": "Course not found or authorization failed."}, status=status.HTTP_404_NOT_FOUND)
        
        enrollments = Enrollment.objects.filter(course=course)
        
        student_list = []
        for enroll in enrollments:
            student_list.append({
                "student_id": enroll.student.id,
                "student_name": enroll.student.username,
                "student_email": enroll.student.email,
                "enrolled_at": enroll.enrolled_at if hasattr(enroll, 'enrolled_at') else None
            })
            
        return Response({
            "course_title": course.title,
            "total_enrolled_students": enrollments.count(),
            "students": student_list
        }, status=status.HTTP_200_OK)

# =====================================================================
# ASSIGNMENT MANAGEMENT MODULE
# =====================================================================

class SubmitAssignmentView(APIView):
    """
    Handles multi-part form submissions for student assignments.
    """
    permission_classes = [IsAuthenticated]
    parser_classes = [MultiPartParser, FormParser]

    def post(self, request, course_id):
        if request.user.role != 'student':
            return Response({"error": "Access denied. Only students can submit assignments."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            course = Course.objects.get(id=course_id)
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)
        
        title = request.data.get('title', 'Project Assignment')
        submission_file = request.FILES.get('submission_file')

        if not submission_file:
            return Response({"error": "Assignment file is required."}, status=status.HTTP_400_BAD_REQUEST)

        submission = AssignmentSubmission.objects.create(
            course=course,
            student=request.user,
            title=title,
            submission_file=submission_file
        )

        return Response({
            "message": "Assignment successfully submitted!",
            "submission_id": submission.id,
            "student": request.user.username
        }, status=status.HTTP_201_CREATED)


class ViewTeacherAssignmentsView(APIView):
    """
    Retrieves all assignment submissions for a specific course assigned to the teacher.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        if request.user.role != 'teacher':
            return Response({"error": "Access denied. Only teachers can view submissions."}, status=status.HTTP_403_FORBIDDEN)
        
        try:
            course = Course.objects.get(id=course_id, instructor=request.user)
        except Course.DoesNotExist:
            return Response({"error": "Course not found or authorization failed."}, status=status.HTTP_404_NOT_FOUND)
        
        submissions = AssignmentSubmission.objects.filter(course=course).order_by('-submitted_at')
        
        submission_list = []
        for sub in submissions:
            submission_list.append({
                "id": sub.id,
                "student_name": sub.student.username,
                "student_email": sub.student.email,
                "title": sub.title,
                "file_url": sub.submission_file.url if sub.submission_file else None,
                "submitted_at": sub.submitted_at.strftime("%Y-%m-%d %H:%M")
            })

        return Response({
            "course_title": course.title,
            "total_submissions": len(submission_list),
            "submissions": submission_list
        }, status=status.HTTP_200_OK)


class CoursePlaylistView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request, course_id):
        try:
            course = Course.objects.get(id=course_id)
            modules = course.modules.all()
            
            playlist_data = []
            for module in modules:
                lessons = module.lessons.all().order_by('sequence')
                lesson_list = []
                for lesson in lessons:
                    lesson_list.append({
                        "id": lesson.id,
                        "title": lesson.title,
                        "video_url": lesson.video_url,
                        "video_file": lesson.video_file.url if lesson.video_file else None,
                    })
                
                playlist_data.append({
                    "module_name": module.name,
                    "section_type": module.get_section_type_display(),
                    "lessons": lesson_list
                })
            
            return Response({
                "course_title": course.title,
                "playlist": playlist_data
            }, status=status.HTTP_200_OK)
            
        except Course.DoesNotExist:
            return Response({"error": "Course not found"}, status=status.HTTP_404_NOT_FOUND)


# =====================================================================
# SPECIFIC COURSE ENDPOINTS
# =====================================================================

@require_GET
def fiverr_course_details_api(request):
    """
    API View to return Fiverr Course details and user authentication status.
    """
    user_authenticated = request.user.is_authenticated
    
    playlist_lessons = [
        {"id": 1, "title": "Lesson 1: Introduction to Fiverr", "file": "LWE Batch#137-138 Lect#01 Fiverr Freelancing By Sir Zeeshan Iqbal.mp4"},
        {"id": 2, "title": "Lesson 2: Creating Your Fiverr Profile", "file": "LWE Batch#137-138 Lect#02 Fiverr Freelancing By Sir Zeeshan Iqbal.mp4"},
        {"id": 3, "title": "Lesson 3: Gigs Setup & Pricing", "file": "LWE Batch#137-138 Lect#03 Fiverr Freelancing By Sir Zeeshan Iqbal.mp4"},
        {"id": 4, "title": "Lesson 4: Attracting Clients", "file": "LWE Batch#137-138 Lect#04 Fiverr Freelancing By Sir Zeeshan Iqbal.mp4"},
        {"id": 5, "title": "Lesson 5: Delivering & Managing Orders", "file": "LWE Batch#137-138 Lect#05 Fiverr Freelancing By Sir Zeeshan Iqbal.mp4"},
    ]

    return JsonResponse({
        "status": "success",
        "is_authenticated": user_authenticated,
        "is_paid": getattr(request.user, 'is_paid', False),
        "course": "Fiverr Freelancing",
        "lessons": playlist_lessons
    }, status=200)


@require_GET
def graphics_course_details_api(request):
    """
    API View to return Graphics Designing Course details and user authentication status.
    """
    user_authenticated = request.user.is_authenticated
    
    playlist_lessons = [
        {"id": 1, "title": "Lesson 1: Introduction to Graphic Designing", "file": "LWE Batch#137-138 Lect#02 Graphic Designing By Miss Memoona Mukhtar.mp4"},
        {"id": 2, "title": "Lesson 2: Tools Overview (Photoshop, Illustrator)", "file": "LWE Batch#137-138 Lect#03 Graphic Designing By Miss Memoona Mukhtar.mp4"},
        {"id": 3, "title": "Lesson 3: Basic Design Principles", "file": "LWE Batch#137-138 Lect#05 Graphic Designing By Miss Memoona Mukhtar.mp4"},
        {"id": 4, "title": "Lesson 4: Social Media Graphics", "file": "LWE Batch#137-138 Lect#09 Graphic Designing By Miss Memoona Mukhtar.mp4"},
        {"id": 5, "title": "Lesson 5: Portfolio Project", "file": "LWE Batch#137-138 Lect#08 Graphic Designing By Miss Memoona Mukhtar.mp4"},
    ]

    return JsonResponse({
        "status": "success",
        "is_authenticated": user_authenticated,
        "is_paid": getattr(request.user, 'is_paid', False),
        "course": "Graphic Designing",
        "lessons": playlist_lessons
    }, status=200)


@require_GET
def infosec_course_details_api(request):
    """
    API View to return Information Security Course details and user authentication status.
    """
    user_authenticated = request.user.is_authenticated
    
    return JsonResponse({
        "status": "success",
        "is_authenticated": user_authenticated,
        "is_paid": getattr(request.user, 'is_paid', False),
        "course": "Information Security",
        "total_lessons": 15
    }, status=200)


@require_GET
def teacher_verification_status_api(request):
    """
    API View to return teacher verification status.
    """
    if not request.user.is_authenticated:
        return JsonResponse({"error": "Authentication required"}, status=401)
    
    user_status = getattr(request.user, 'status', 'pending')
    
    return JsonResponse({
        "status": user_status,
        "username": request.user.username,
        "reason": getattr(request.user, 'rejection_reason', '')
    }, status=200)


# =====================================================================
# AI MCQ GENERATOR MODULE
# =====================================================================

@api_view(['POST', 'GET'])
@permission_classes([AllowAny])
def generate_mcqs_view(request):
    """
    Handles real-time MCQ generation requests for practice quizzes.
    """
    if request.method == 'POST':
        topic = request.data.get('topic', 'General Knowledge').strip()
        if not topic:
            topic = 'General Knowledge'
        
        mcqs_data = [
            {
                "id": 1,
                "question": f"What is the primary core objective when studying {topic}?",
                "options": {
                    "A": f"To master core fundamental principles of {topic}",
                    "B": "To write unoptimized synchronous code",
                    "C": "To bypass secure authentication protocols",
                    "D": "None of the above"
                },
                "correct": "A"
            },
            {
                "id": 2,
                "question": "Which HTTP method is used to send JSON data to Django API endpoints?",
                "options": {
                    "A": "GET",
                    "B": "POST",
                    "C": "DELETE",
                    "D": "OPTIONS"
                },
                "correct": "B"
            },
            {
                "id": 3,
                "question": "In SmartEduX platform, what passing score percentage is required for certificate graduation?",
                "options": {
                    "A": "50%",
                    "B": "70%",
                    "C": "80%",
                    "D": "90%"
                },
                "correct": "C"
            }
        ]

        return Response({
            "status": "success",
            "topic": topic,
            "mcqs": mcqs_data
        }, status=status.HTTP_200_OK)

    return Response({"status": "success", "message": "MCQ Generator Engine Ready"}, status=status.HTTP_200_OK)