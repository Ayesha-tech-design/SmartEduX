from django.urls import path
from . import views
from .views import student_notes_api, delete_student_note_api

urlpatterns = [
    # Main AI Note Generator Endpoints
    path('generate/', views.generate_notes, name='generate_notes'),
    path('generate-ai-notes/', views.generate_ai_notes, name='generate_ai_notes'),
    
    # === Ayesha's History Endpoints ===
    path('save-history/', views.save_history, name='save_history'),
    path('fetch-history/', views.fetch_history, name='fetch_history'),

    # === Features Overview Endpoint ===
    path('api/features/overview/', views.features_overview_api, name='features_overview_api'),
    
    # === Saved Notes & Delete Endpoints ===
    path('notes/', student_notes_api, name='student_notes_api'),
    path('notes/delete/<int:note_id>/', delete_student_note_api, name='delete_student_note_api'),
]