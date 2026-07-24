from django.urls import path
from . import views

urlpatterns = [
    # Main AI Note Generator Endpoints
    path('generate/', views.generate_notes, name='generate_notes'),
    path('generate-ai-notes/', views.generate_ai_notes, name='generate_ai_notes'),
    
    # === Ayesha's History Endpoints ===
    path('save-history/', views.save_history, name='save_history'),
    path('fetch-history/', views.fetch_history, name='fetch_history'),

    # === Features Overview Endpoint ===
    path('api/features/overview/', views.features_overview_api, name='features_overview_api'),
]