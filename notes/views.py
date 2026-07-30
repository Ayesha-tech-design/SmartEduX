import os
import json
import re
import urllib.request
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
from google.genai import types
from pydantic import BaseModel, Field
from typing import List

from .models import VideoNote, QuizQuestion, UserQuizAttempt

# PRODUCTION API INITIALIZATION
RAW_KEY = getattr(settings, "GEMINI_API_KEY", None)
CLEAN_KEY = str(RAW_KEY).replace("..key", "").strip() if RAW_KEY else None

client = genai.Client(api_key=CLEAN_KEY) if CLEAN_KEY else None


# =====================================================================
# PYDANTIC SCHEMAS FOR STRUCTURED MCQ OUTPUT
# =====================================================================

class MCQOptions(BaseModel):
    A: str = Field(description="Option A text")
    B: str = Field(description="Option B text")
    C: str = Field(description="Option C text")
    D: str = Field(description="Option D text")

class MCQItem(BaseModel):
    question: str = Field(description="Conceptual question text testing actual lecture understanding")
    options: MCQOptions
    answer: str = Field(description="Correct option key strictly matching 'A', 'B', 'C', or 'D'")

class QuizResponseSchema(BaseModel):
    quiz: List[MCQItem]


# =====================================================================
# 1. MAIN AI NOTES GENERATION ENDPOINT
# =====================================================================

@api_view(['POST'])
@permission_classes([AllowAny]) 
def generate_notes(request):
    try:
        raw_url = (request.data.get('youtube_url') or request.data.get('video_url') or '').strip()
        print(f"\n[SMARTEDUX LIVE LOG]: Processing Incoming URL: {raw_url}")

        if not raw_url:
            return Response({"status": "failed", "error": "YouTube URL is required"}, status=400)

        # Clean URL Parsing
        youtube_url = re.sub(r'([?&]t=\d+s?|&ab_channel=[^&]+)', '', raw_url).strip()

        video_id = ""
        if "v=" in youtube_url:
            video_id = youtube_url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in youtube_url:
            video_id = youtube_url.split("youtu.be/")[1].split("?")[0]
        else:
            video_id = youtube_url.rstrip("/").split("/")[-1]

        if not video_id or len(video_id) < 5:
            return Response({"status": "failed", "error": "Invalid YouTube URL format"}, status=400)

        # Database Cache Check
        existing = VideoNote.objects.filter(video_url=youtube_url).order_by('-created_at').first()
        if existing and existing.summary and "Executive Summary" in existing.summary and "I apologize" not in existing.summary:
            saved_questions = getattr(existing, 'questions', None)
            quiz_list = []
            if saved_questions and saved_questions.exists():
                quiz_list = [
                    {
                        "question": q.question_text,
                        "options": {"A": q.option_a, "B": q.option_b, "C": q.option_c, "D": q.option_d},
                        "answer": q.correct_answer
                    } for q in saved_questions.all()
                ]
            return Response({
                "status": "success",
                "source": "database",
                "title": existing.video_title or f"Notes for Video ({video_id})",
                "notes": existing.summary,
                "summary": existing.summary,
                "quiz": quiz_list
            })

        # Fast Title Extraction (oEmbed)
        actual_title = f"Define Computer and Its Basics"
        try:
            oembed_url = f"https://www.youtube.com/oembed?url=https://www.youtube.com/watch?v={video_id}&format=json"
            req = urllib.request.Request(oembed_url, headers={'User-Agent': 'Mozilla/5.0'})
            with urllib.request.urlopen(req, timeout=3) as res:
                if res.status == 200:
                    data = json.loads(res.read().decode())
                    actual_title = data.get('title', actual_title)
                    print(f"[SMARTEDUX TITLE SUCCESS]: Extracted Title -> {actual_title}")
        except Exception as t_err:
            print(f"[SMARTEDUX TITLE WARNING]: oEmbed Fetch Failed -> {t_err}")

        # Transcript Extraction
        raw_transcript = ""
        has_transcript = False
        
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'hi', 'ur', 'es', 'pt'])
            raw_transcript = " ".join([item['text'] for item in transcript])
            has_transcript = True if len(raw_transcript.strip()) > 30 else False
        except Exception:
            try:
                ytt_api = YouTubeTranscriptApi()
                fetched = None
                
                try:
                    transcript_list = ytt_api.list(video_id) if hasattr(ytt_api, 'list') else ytt_api.list_transcripts(video_id)
                    fetched = transcript_list.find_transcript(['en', 'hi', 'ur', 'es', 'pt']).fetch()
                except Exception:
                    try:
                        fetched = transcript_list.find_generated_transcript(['en', 'hi', 'ur', 'es', 'pt']).fetch()
                    except Exception:
                        if 'transcript_list' in locals() and transcript_list:
                            for tr in transcript_list:
                                fetched = tr.fetch()
                                break
                
                if fetched and isinstance(fetched, list):
                    raw_transcript = " ".join([item['text'] if isinstance(item, dict) else getattr(item, 'text', '') for item in fetched])
                has_transcript = True if len(raw_transcript.strip()) > 30 else False
            except Exception as tr_err:
                print(f"[TRANSCRIPT FETCH NOTICE]: {tr_err}")
                raw_transcript = ""
                has_transcript = False

        if not client:
            return Response({"status": "failed", "error": "GEMINI_API_KEY is not configured in settings.py"}, status=500)

        # Prompt Builder for Notes
        if has_transcript and len(raw_transcript.strip()) > 50:
            prompt = f"""
You are SmartEduX AI, an elite academic and technical tutor.
Generate structured study notes strictly based on the video transcript provided below.

INSTRUCTIONS:
1. TOPIC FOCUS: Focus on the main topic: "{actual_title}".
2. CODE/SYNTAX: If it involves programming, include code/syntax snippets.
3. NO APOLOGIES: Never output statements like "I cannot access YouTube". Always output study notes.

REQUIRED MARKDOWN FORMAT:
## 📌 Executive Summary
(2-3 sentences summarizing "{actual_title}")

## 🎯 Key Concepts & Detailed Points
(Core concepts with **bold key terms**)

## 💡 Key Takeaways
(3-4 high-impact summary points)

VIDEO TITLE: {actual_title}
TRANSCRIPT TEXT:
{raw_transcript[:15000]}
"""
        else:
            prompt = f"""
You are SmartEduX AI, an elite academic and technical tutor.
Act as a subject matter expert and generate comprehensive academic study notes for the lecture topic: "{actual_title}".

STRICT DIRECTIVES:
1. NEVER apologize or state that you cannot access external sites or watch videos.
2. Direct Output: Directly write accurate study notes covering definitions, key principles, components, and practical details for "{actual_title}".

REQUIRED MARKDOWN FORMAT:
## 📌 Executive Summary
(2-3 concise lines explaining specifically what "{actual_title}" covers)

## 🎯 Key Concepts & Detailed Points
(Detailed breakdown of points with **bold key terms**)

## 💡 Key Takeaways
(3-4 key summary points)

LECTURE TOPIC: {actual_title}
"""

        # Gemini Model Call for Notes
        try:
            response = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=prompt
            )
        except Exception:
            try:
                response = client.models.generate_content(
                    model="gemini-1.5-flash",
                    contents=prompt
                )
            except Exception:
                response = client.models.generate_content(
                    model="gemini-2.0-flash",
                    contents=prompt
                )

        summary_res = response.text if response and response.text else f"## 📌 Executive Summary\nStudy notes compiled for {actual_title}."

        # GENERATE 5 CONCEPTUAL MCQS IN SAME RESPONSE
        quiz_list = []
        try:
            quiz_prompt = f"""
You are SmartEduX AI, an elite university academic tutor.
Your task is to generate EXACTLY 5 high-quality conceptual Multiple Choice Questions (MCQs)
based strictly on the actual lecture content provided below.

STRICT INSTRUCTIONS:
1. Ignore all advertisements, sponsorships, greetings, promos, course offerings, social media handles, and non-academic chatter.
2. Focus exclusively on core concepts, formulas, definitions, processes, principles, and key takeaways.
3. Provide 4 distinct options (A, B, C, D) for each question with exactly one correct option ('A', 'B', 'C', or 'D').

LECTURE TOPIC: "{actual_title}"
LECTURE CONTENT:
{(raw_transcript if has_transcript else summary_res)[:15000]}
"""
            json_config = types.GenerateContentConfig(
                response_mime_type="application/json",
                response_schema=QuizResponseSchema,
                temperature=0.2
            )

            q_res = client.models.generate_content(
                model="gemini-2.5-flash",
                contents=quiz_prompt,
                config=json_config
            )
            raw_q = q_res.text if q_res and q_res.text else "{}"
            parsed_q = json.loads(raw_q)
            raw_quiz_items = parsed_q.get("quiz", [])

            for item in raw_quiz_items:
                opts = item.get("options", {})
                quiz_list.append({
                    "question": item.get("question", ""),
                    "options": {
                        "A": opts.get("A", ""),
                        "B": opts.get("B", ""),
                        "C": opts.get("C", ""),
                        "D": opts.get("D", "")
                    },
                    "answer": str(item.get("answer", "A")).upper().strip()
                })
            quiz_list = quiz_list[:5]
        except Exception as q_err:
            print(f"[UNIFIED MCQS GENERATION WARNING]: {q_err}")

        # Save to Database
        if request.user.is_authenticated:
            v_note = VideoNote.objects.create(
                user=request.user,
                video_title=actual_title,
                video_url=youtube_url,
                transcript=raw_transcript or f"Video Title: {actual_title}",
                summary=summary_res
            )

            if quiz_list and v_note:
                for q in quiz_list:
                    opts = q.get("options", {})
                    QuizQuestion.objects.create(
                        video_note=v_note,
                        question_text=q.get("question", ""),
                        option_a=opts.get("A", ""),
                        option_b=opts.get("B", ""),
                        option_c=opts.get("C", ""),
                        option_d=opts.get("D", ""),
                        correct_answer=q.get("answer", "A")
                    )

        return Response({
            "status": "success",
            "title": actual_title,
            "notes": summary_res,
            "summary": summary_res,
            "quiz": quiz_list
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
# 2. OTHER ENDPOINTS (UNTOUCHED)
# =====================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def generate_quiz_api(request):
    return generate_notes(request)


@api_view(['GET'])
@permission_classes([AllowAny])
def get_video_quiz_api(request, note_id):
    try:
        questions = QuizQuestion.objects.filter(video_note_id=note_id)
        quiz_data = [
            {
                "id": q.id,
                "question": q.question_text,
                "options": {
                    "A": q.option_a,
                    "B": q.option_b,
                    "C": q.option_c,
                    "D": q.option_d
                },
                "answer": q.correct_answer
            } for q in questions
        ]
        return Response({
            "status": "success",
            "total_questions": len(quiz_data),
            "quiz": quiz_data
        }, status=200)
    except Exception as err:
        return Response({"status": "failed", "error": str(err)}, status=500)


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


# =====================================================================
# 3. IMPORTANT NOTES / KEY POINTS ENDPOINT
# =====================================================================

@api_view(['POST'])
@permission_classes([AllowAny])
def generate_important_notes_api(request):
    try:
        raw_url = (request.data.get('youtube_url') or request.data.get('video_url') or '').strip()
        requested_count = request.data.get('count', 5)

        try:
            requested_count = int(requested_count)
        except (TypeError, ValueError):
            requested_count = 5

        if requested_count not in [5, 10]:
            requested_count = 5

        if not raw_url:
            return Response({"status": "failed", "error": "YouTube URL is required"}, status=400)

        youtube_url = re.sub(r'([?&]t=\d+s?|&ab_channel=[^&]+)', '', raw_url).strip()
        video_id = ""

        if "v=" in youtube_url:
            video_id = youtube_url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in youtube_url:
            video_id = youtube_url.split("youtu.be/")[1].split("?")[0]
        else:
            video_id = youtube_url.rstrip("/").split("/")[-1]

        if not video_id or len(video_id) < 5:
            return Response({"status": "failed", "error": "Invalid YouTube URL format"}, status=400)

        if not client:
            return Response({"status": "failed", "error": "GEMINI_API_KEY is not configured"}, status=500)

        existing = VideoNote.objects.filter(video_url=youtube_url).order_by('-created_at').first()
        transcript_text = existing.transcript if existing and existing.transcript else ""

        if not transcript_text.strip():
            try:
                transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'hi', 'ur', 'es', 'pt'])
                transcript_text = " ".join([item['text'] for item in transcript])
            except Exception:
                pass

        if not transcript_text.strip() and existing and existing.summary:
            transcript_text = existing.summary

        if not transcript_text.strip():
            return Response({"status": "failed", "error": "No educational content retrieved."}, status=404)

        important_prompt = f"""
You are SmartEduX AI. Generate EXACTLY {requested_count} important educational points based on:
{transcript_text[:15000]}
Return ONLY a valid JSON array of strings.
"""
        response = client.models.generate_content(model="gemini-2.5-flash", contents=important_prompt)
        raw_response = response.text if response and response.text else "[]"

        if "```json" in raw_response:
            raw_response = raw_response.split("```json", 1)[1].split("```", 1)[0].strip()
        elif "```" in raw_response:
            raw_response = raw_response.split("```", 1)[1].split("```", 1)[0].strip()

        important_notes = []
        try:
            parsed = json.loads(raw_response)
            if isinstance(parsed, list):
                important_notes = [str(item).strip() for item in parsed if str(item).strip()]
        except Exception:
            lines = raw_response.splitlines()
            for line in lines:
                cleaned = re.sub(r'^\s*(?:[-•*]|\d+[.)])\s*', '', line).strip()
                if cleaned:
                    important_notes.append(cleaned)

        important_notes = important_notes[:requested_count]

        return Response({
            "status": "success",
            "video_id": video_id,
            "count": len(important_notes),
            "important_notes": important_notes
        }, status=200)

    except Exception as err:
        return Response({"status": "failed", "error": str(err)}, status=500)