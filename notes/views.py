import os
import json
import re
import yt_dlp
from django.shortcuts import render
from django.conf import settings
from rest_framework.decorators import api_view, permission_classes 
from rest_framework.response import Response
from rest_framework.permissions import IsAuthenticated 
from youtube_transcript_api import YouTubeTranscriptApi
from google import genai
from google.genai import types
from .models import VideoNote, QuizQuestion, UserQuizAttempt

# === AUTHENTICATION IMPORTS ===
from django.contrib.auth.models import User
from django.contrib.auth import authenticate, login, logout

# PRODUCTION API INITIALIZATION
RAW_KEY = getattr(settings, "GEMINI_API_KEY", None)
CLEAN_KEY = str(RAW_KEY).replace("..key", "").strip() if RAW_KEY else None

client = genai.Client(api_key=CLEAN_KEY) if CLEAN_KEY else None


@api_view(['POST'])
@permission_classes([IsAuthenticated]) 
def generate_notes(request):
    try:
        youtube_url = request.data.get('youtube_url', '').strip()
        print(f"\n[SMARTEDUX LIVE LOG]: Incoming Link from Frontend: {youtube_url}")

        if not youtube_url:
            return Response({"status": "failed", "error": "YouTube URL required"}, status=400)

        # Video ID Parser
        video_id = ""
        if "v=" in youtube_url:
            video_id = youtube_url.split("v=")[1].split("&")[0]
        elif "youtu.be/" in youtube_url:
            video_id = youtube_url.split("youtu.be/")[1].split("?")[0]
        else:
            video_id = youtube_url.rstrip("/").split("/")[-1]

        if not video_id:
            return Response({"status": "failed", "error": "Invalid YouTube URL format"}, status=400)

        # 1. CACHE CHECK
        existing = VideoNote.objects.filter(video_title=video_id).first()
        if existing:
            saved_questions = existing.questions.all()
            quiz_list = []
            for q in saved_questions:
                quiz_list.append({
                    "question": q.question_text,
                    "options": {"A": q.option_a, "B": q.option_b, "C": q.option_c, "D": q.option_d},
                    "answer": q.correct_answer
                })

            return Response({
                "status": "success",
                "source": "database",
                "summary": existing.summary,
                "quiz": quiz_list
            })

        # 2. ADVANCED TRANSCRIPT EXTRACTION
        raw_text = ""
        source_type = "gemini_transcript"
        
        try:
            transcript = YouTubeTranscriptApi.get_transcript(video_id, languages=['en', 'hi'])
            raw_text = " ".join([item['text'] for item in transcript])
        except Exception:
            try:
                transcript_list = YouTubeTranscriptApi.list_transcripts(video_id)
                try:
                    transcript = transcript_list.find_generated_transcript(['en', 'hi']).fetch()
                except Exception:
                    transcript = transcript_list.find_id_encoded_transcript(['en', 'hi']).fetch()
                raw_text = " ".join([item['text'] for item in transcript])
            except Exception:
                try:
                    ydl_opts = {'quiet': True, 'no_warnings': True}
                    with yt_dlp.YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(youtube_url, download=False)
                        raw_text = f"Title: {info.get('title', '')}\nDescription: {info.get('description', '')[:1500]}"
                    source_type = "gemini_metadata_fallback"
                except Exception:
                    raw_text = "Standard Educational Domain Video Content Text"
                    source_type = "fallback"

        raw_text = raw_text[:12000]

        # ==========================================================
        # SMARTEDUX PROFESSIONAL AI PROMPT
        # ==========================================================

        prompt = f"""
You are SmartEduX AI, an intelligent educational assistant.

Your responsibility is to convert educational video content into high-quality study material for university students.

=====================
RULES
=====================

1. ONLY focus on educational concepts.

2. Ignore:
- sponsorships
- advertisements
- promotions
- coupon codes
- course selling
- social media
- introductions
- greetings
- outros

3. Never mention:
"According to the video"
"The instructor says"

Instead write as if these are professional study notes.

4. If transcript quality is poor,
use the available educational context and your own verified knowledge
to produce accurate notes.

Never say:
"I don't know."

=====================
OUTPUT FORMAT
=====================

# Title

Generate a suitable title.

---

## Introduction

Explain the topic in 1-2 paragraphs.

---

## Key Concepts

Create clear headings.

For every heading explain:

• Definition

• Explanation

• Important Points

• Advantages (if applicable)

• Limitations (if applicable)

• Real World Example

---

## Important Terms

List important technical terms.

---

## Summary

Write 5-8 concise bullet points.

=====================
MCQ RULES
=====================

Generate EXACTLY 5 MCQs.

Each MCQ must contain

Question

A

B

C

D

Correct Answer

MCQs should test conceptual understanding.

Avoid trivial questions.

=====================
STYLE
=====================

Use professional English.

Use Markdown.

Avoid unnecessary symbols.

Make notes look like university lecture notes.

=====================
VIDEO CONTENT
=====================

    {raw_text}
"""

        # Corrected complete Schema Config
        config = types.GenerateContentConfig(
            response_mime_type="application/json",
            response_schema=types.Schema(
                type=types.Type.OBJECT,
                properties={
                    "summary": types.Schema(type=types.Type.STRING),
                    "quiz": types.Schema(
                        type=types.Type.ARRAY,
                        items=types.Schema(
                            type=types.Type.OBJECT,
                            properties={
                                "question": types.Schema(type=types.Type.STRING),
                                "options": types.Schema(
                                    type=types.Type.OBJECT,
                                    properties={
                                        "A": types.Schema(type=types.Type.STRING),
                                        "B": types.Schema(type=types.Type.STRING),
                                        "C": types.Schema(type=types.Type.STRING),
                                        "D": types.Schema(type=types.Type.STRING),
                                    }
                                ),
                                "answer": types.Schema(type=types.Type.STRING),
                            }
                        )
                    )
                }
            )
        )

        response = client.models.generate_content(
            model="gemini-2.5-flash",
            contents=prompt,
            config=config
        )
        
        data = json.loads(response.text, strict=False)

        # 4. DATABASE ENTRY LOCK WITH USER MAPPING FIXED
        video_note_obj = VideoNote.objects.create(
            user=request.user,
            video_title=video_id,
            video_url=youtube_url,
            transcript=raw_text,
            summary=data.get("summary", "")
        )

        # 5. LOOP AND SAVE QUIZ
        generated_quiz = data.get("quiz", [])
        for item in generated_quiz:
            options = item.get("options", {})
            QuizQuestion.objects.create(
                video_note=video_note_obj,
                question_text=item.get("question", ""),
                option_a=options.get("A", ""),
                option_b=options.get("B", ""),
                option_c=options.get("C", ""),
                option_d=options.get("D", ""),
                correct_answer=item.get("answer", "A")
            )

        print("-> Database Sync Complete for fresh conceptual video.")

        return Response({
            "status": "success",
            "source": source_type,
            "summary": data.get("summary", ""),
            "quiz": generated_quiz
        })

    except Exception as err:
        print(f"[CRITICAL BACKEND ERROR]: {str(err)}")
        return Response({"status": "failed", "error": str(err)}, status=500)


# =====================================================================
# HISTORY MANAGEMENT MODULE (Ayesha's Dashboard Storage & Fetch)
# =====================================================================

@api_view(['POST'])
@permission_classes([IsAuthenticated])  
def save_history(request):
    try:
        title = request.data.get('video_title')
        url = request.data.get('video_url')
        transcript_text = request.data.get('transcript')
        summary_text = request.data.get('summary')
        
        if not title or not url:
            return Response({"status": "failed", "error": "Video title and URL are required"}, status=400)

        history_item = VideoNote.objects.create(
            user=request.user,  
            video_title=title,
            video_url=url,
            transcript=transcript_text,
            summary=summary_text
        )
        
        print(f"\n[SMARTEDUX STORAGE LOG]: New history node successfully synced for: {request.user.username}")
        return Response({"status": "success", "message": "History saved successfully!"}, status=201)
        
    except Exception as err:
        return Response({"status": "failed", "error": str(err)}, status=500)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def fetch_history(request):
    try:
        user_history = VideoNote.objects.filter(user=request.user).order_by('-created_at')
        
        history_list = []
        for item in user_history:
            history_list.append({
                "id": item.id,
                "video_title": item.video_title,
                "video_url": item.video_url,
                "summary": item.summary,
                "created_at": item.created_at.strftime("%Y-%m-%d %H:%M")
            })
            
        return Response({
            "status": "success",
            "total_records": len(history_list),
            "history": history_list
        }, status=200)
        
    except Exception as err:
        return Response({"status": "failed", "error": str(err)}, status=500)
@api_view(['GET'])
@permission_classes([IsAuthenticated])
def student_notes_api(request):
    try:
        # User ke save kiye gaye video notes fetch karein
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