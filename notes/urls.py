from django.urls import path
from . import views
from .views import student_notes_api, delete_student_note_api

urlpatterns = [
    # AI Notes Generator Route
    path('generate/', views.generate_notes, name='generate_notes'),
    
    # === Ayesha's History Endpoints ===
    path('save-history/', views.save_history, name='save_history'),
    path('fetch-history/', views.fetch_history, name='fetch_history'),
    
    # === Saved Notes & Delete Endpoints (Yahan se 'student/' hata diya hai kyunke main urls mein hai) ===
    path('notes/', student_notes_api, name='student_notes_api'),
    path('notes/delete/<int:note_id>/', delete_student_note_api, name='delete_student_note_api'),
]