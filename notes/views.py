import os
import json
import re
import yt_dlp
from django.shortcuts import render
from django.conf import settings
from django.http import JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.views.decorators.http import require_GET
from rest_framework.decorators import api_view, permission_classes 
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated, AllowAny
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai

from .models import VideoNote, QuizQuestion, UserQuizAttempt

# PRODUCTION API INITIALIZATION
RAW_KEY = getattr(settings, "GEMINI_API_KEY", None)
CLEAN_KEY = str(RAW_KEY).replace("..key", "").strip() if RAW_KEY else None

client = genai.Client(api_key=CLEAN_KEY) if CLEAN_KEY else None


@api_view(['POST'])
@permission_classes([AllowAny]) 
def generate_notes(request):
    try:
        raw_url = (request.data.get('youtube_url') or request.data.get('video_url') or '').strip()
        print(f"\n[SMARTEDUX LIVE LOG]: Processing Incoming URL: {raw_url}")

        if not raw_url:
            return Response({"status": "failed", "error": "YouTube URL is required"}, status=400)

        # 1. CLEAN URL PARSING (Strip timestamps & tracking parameters)
        youtube_url = re.sub(r'([?&]t=\d+s?|&ab_channel=[^&]+)', '', raw_url).strip()

        # Extract Video ID
        video_id = ""
        if "v=" in youtube_url:
            video_id = youtube_url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in youtube_url:
            video_id = youtube_url.split("youtu.be/")[1].split("?")[0]
        else:
            video_id = youtube_url.rstrip("/").split("/")[-1]

        if not video_id or len(video_id) < 5:
            return Response({"status": "failed", "error": "Invalid YouTube URL format"}, status=400)

        # 2. ACCURATE DATABASE CACHE CHECK (Only return cache if summary belongs to valid format & URL)
        existing = VideoNote.objects.filter(video_url=youtube_url).order_by('-created_at').first()
        if existing and existing.summary and "Executive Summary" in existing.summary and "representative example" not in existing.summary:
            saved_questions = existing.questions.all()
            quiz_list = [
                {
                    "question": q.question_text,
                    "options": {"A": q.option_a, "B": q.option_b, "C": q.option_c, "D": q.option_d},
                    "answer": q.correct_answer
                } for q in saved_questions
            ]
            return Response({
                "status": "success",
                "source": "database",
                "title": existing.video_title or f"Notes for Video ({video_id})",
                "notes": existing.summary,
                "summary": existing.summary,
                "quiz": quiz_list
            })

        # 3. METADATA EXTRACTION (Fetch exact video title and description via yt_dlp)
        actual_title = f"YouTube Video ({video_id})"
        actual_description = ""
        try:
            ydl_opts = {'quiet': True, 'no_warnings': True, 'skip_download': True}
            with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(youtube_url, download=False)
                actual_title = info.get('title', actual_title)
                actual_description = info.get('description', '')[:3000]
        except Exception as meta_err:
            print(f"[METADATA FETCH WARNING]: {meta_err}")

        # 4. TRANSCRIPT EXTRACTION
        raw_transcript = ""
        has_transcript = False
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'hi', 'ur', 'es', 'pt'])
            raw_transcript = " ".join([item['text'] for item in transcript])
            has_transcript = True
        except Exception:
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                try:
                    fetched = transcript_list.find_transcript(['en', 'hi', 'ur', 'es', 'pt']).fetch()
                except Exception:
                    fetched = transcript_list.find_generated_transcript(['en', 'hi', 'ur', 'es', 'pt']).fetch()
                raw_transcript = " ".join([item['text'] for item in fetched])
                has_transcript = True
            except Exception:
                raw_transcript = ""
                has_transcript = False

        if not client:
            return Response({"status": "failed", "error": "GEMINI_API_KEY is not configured in settings.py"}, status=500)

        # 5. DYNAMIC PROMPT BUILDER (Strictly follows user rules)
        if has_transcript and len(raw_transcript.strip()) > 50:
            # Mode A: Transcript is present -> Generate strictly from spoken text
            prompt = f"""
You are SmartEduX AI, an expert educational tutor.
Generate structured study notes strictly and exclusively from the provided video transcript below.

STRICT RULES:
1. Base all facts, concepts, and bullet points ONLY on what is spoken in the transcript.
2. Do NOT add outside topics, unrelated CS/medical theories, or meta-commentary.
3. Keep the notes concise, clear, and organized for university students.

REQUIRED MARKDOWN FORMAT:
## 📌 Executive Summary
(2-3 sentences summarizing the exact video topic)

## 🎯 Key Concepts & Detailed Bullet Points
(Detailed sub-topics with **bold terms** and bullet points from the transcript)

## 💡 Key Takeaways
(3-5 actionable summary points)

VIDEO TITLE: {actual_title}
TRANSCRIPT CONTENT:
{raw_transcript[:12000]}
"""
        else:
            # Mode B: Transcript missing -> Gemini uses Title + Description to generate a clear, accurate topic summary
            prompt = f"""
You are SmartEduX AI, an expert educational tutor.
The spoken transcript for this video is unavailable. Generate accurate, topic-specific study notes based on the video title and description.

STRICT RULES:
1. Focus strictly on the subject matter indicated by the title: "{actual_title}".
2. Do NOT mention "no transcript provided", "as a representative example", or any meta-commentary.
3. Do NOT invent unrelated computer science or medical subjects unless the video title/description is explicitly about them.
4. Provide a clear, educational overview so the student easily understands the core topic of this video.

REQUIRED MARKDOWN FORMAT:
## 📌 Executive Summary
(2-3 concise lines explaining what the topic "{actual_title}" is about)

## 🎯 Key Concepts & Detailed Bullet Points
(Key concepts and principles related strictly to "{actual_title}" with **bold terms**)

## 💡 Key Takeaways
(3-5 key takeaways for quick understanding)

VIDEO TITLE: {actual_title}
DESCRIPTION CONTEXT: {actual_description[:3000]}
"""

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt
        )

        summary_res = response.text if response and response.text else f"## 📌 Executive Summary\nStudy notes compiled for {actual_title}."

        # 6. SAVE TO DATABASE
        if request.user.is_authenticated:
            VideoNote.objects.create(
                user=request.user,
                video_title=actual_title,
                video_url=youtube_url,
                transcript=raw_transcript or actual_description,
                summary=summary_res
            )

        return Response({
            "status": "success",
            "title": actual_title,
            "notes": summary_res,
            "summary": summary_res
        })

    except Exception as err:
        print(f"[CRITICAL BACKEND ERROR]: {str(err)}")
        return Response({
            "status": "failed",
            "error": f"Backend Generation Error: {str(err)}"
        }, status=500)


@csrf_exempt
def generate_ai_notes(request):
    return generate_notes(request)


# =====================================================================
# HISTORY MANAGEMENT MODULE
# =====================================================================

@api_view(['POST'])
@permission_classes([AllowAny])  
def save_history(request):
    try:
        title = request.data.get('video_title')
        url = request.data.get('video_url')
        transcript_text = request.data.get('transcript', '')
        summary_text = request.data.get('summary', '')
        
        if not title or not url:
            return Response({"status": "failed", "error": "Video title and URL are required"}, status=400)

        if request.user.is_authenticated:
            VideoNote.objects.create(
                user=request.user,  
                video_title=title,
                video_url=url,
                transcript=transcript_text,
                summary=summary_text
            )
        return Response({"status": "success", "message": "History saved successfully!"}, status=201)
        
    except Exception as err:
        return Response({"status": "failed", "error": str(err)}, status=500)


@api_view(['GET'])
@permission_classes([AllowAny])
def fetch_history(request):
    try:
        if request.user.is_authenticated:
            user_history = VideoNote.objects.filter(user=request.user).order_by('-created_at')
            history_list = [{
                "id": item.id,
                "video_title": item.video_title,
                "video_url": item.video_url,
                "summary": item.summary,
                "created_at": item.created_at.strftime("%Y-%m-%d %H:%M")
            } for item in user_history]
        else:
            history_list = []
            
        return Response({
            "status": "success",
            "total_records": len(history_list),
            "history": history_list
        }, status=200)
        
    except Exception as err:
        return Response({"status": "failed", "error": str(err)}, status=500)


# === Features Overview API ===
@require_GET
def features_overview_api(request):
    user_data = {
        "is_authenticated": request.user.is_authenticated,
        "username": request.user.username if request.user.is_authenticated else "",
        "role": getattr(request.user, 'role', 'student') if request.user.is_authenticated else 'guest'
    }
    
    return JsonResponse({
        "status": "success",
        "user": user_data
    }, status=200)


# === Student Notes APIs ===
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_notes_api(request):
    try:
        notes = VideoNote.objects.filter(user=request.user).order_by('-created_at')
        data = [{
            "id": note.id,
            "title": note.video_title,
            "date": note.created_at.strftime("%Y-%m-%d"),
            "content": note.summary
        } for note in notes]
        return Response(data, status=200)
    except Exception as err:
        return Response({"status": "failed", "error": str(err)}, status=500)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_student_note_api(request, note_id):
    try:
        note = VideoNote.objects.get(id=note_id, user=request.user)
        note.delete()
        return Response({"success": True, "message": "Note deleted successfully!"}, status=200)
    except VideoNote.DoesNotExist:
        return Response({"success": False, "message": "Note not found!"}, status=404)
    except Exception as err:
        return Response({"status": "failed", "error": str(err)}, status=500)