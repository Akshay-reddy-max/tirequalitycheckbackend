import os
import uuid
from django.conf import settings
from rest_framework.views import APIView
from rest_framework.parsers import MultiPartParser
from rest_framework.response import Response
from rest_framework import status
from django.core.files.storage import default_storage
from django.core.files.base import ContentFile
import google.generativeai as genai
from django.views.decorators.csrf import csrf_exempt
from django.http import JsonResponse
from django.db import connection
from django.contrib.auth.hashers import make_password, check_password
import json
from datetime import datetime
import jwt
from datetime import datetime, timedelta
import traceback
from rest_framework.pagination import PageNumberPagination
from .models import TyreScan
from .serializers import TyreScanSerializer


class TyreScanPagination(PageNumberPagination):
    page_size = 10  # Adjust as needed
    page_size_query_param = 'page_size'
    max_page_size = 50
    
    

SECRET_KEY = 'tireTestai'  # Replace with Django's SECRET_KEY in real apps
TOKEN_EXPIRY_HOURS = 12

from .models import TyreScan

# Configure Gemini
genai.configure(api_key=settings.GOOGLE_API_KEY)

def dictfetchone(cursor):
    "Return one row from a cursor as a dict"
    desc = cursor.description
    row = cursor.fetchone()
    if row is None:
        return None
    return {desc[i][0]: row[i] for i in range(len(desc))}


@csrf_exempt
def signup_view(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            username = data.get('username')
            email = data.get('email')
            password = data.get('password')

            if not username or not email or not password:
                return JsonResponse({'success': False, 'error': 'All fields are required'}, status=400)

            with connection.cursor() as cursor:
                # Check if username or email already exists
                cursor.execute("SELECT * FROM userDetails WHERE username = %s OR email = %s", [username, email])
                existing = cursor.fetchone()
                if existing:
                    return JsonResponse({'success': False, 'error': 'Username or Email already exists'}, status=409)

                # Insert new user
                hashed_password = make_password(password)
                now = datetime.now().strftime('%Y-%m-%d %H:%M:%S')

                cursor.execute(
                    "INSERT INTO userDetails (username, email, password, createdAt) VALUES (%s, %s, %s, %s)",
                    [username, email, hashed_password, now]
                )

            return JsonResponse({'success': True, 'message': 'User created successfully'})

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': False, 'error': 'Only POST method allowed'}, status=405)


@csrf_exempt
def login_api(request):
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            login_input = data.get('email') or data.get('username')
            password = data.get('password')

            if not login_input or not password:
                return JsonResponse({'success': False, 'error': 'Email/Username and password required'}, status=400)

            with connection.cursor() as cursor:
                # ✅ Match by email OR username
                cursor.execute("SELECT * FROM userDetails WHERE email = %s OR username = %s", [login_input, login_input])
                user = dictfetchone(cursor)

                if user and check_password(password, user['password']):
                    payload = {
                        'email': user['email'],
                        'username': user['username'],
                        'exp': datetime.utcnow() + timedelta(hours=TOKEN_EXPIRY_HOURS)
                    }
                    token = jwt.encode(payload, SECRET_KEY, algorithm='HS256')

                    return JsonResponse({
                        'success': True,
                        'message': 'Login successful',
                        'token': token
                    })

                else:
                    return JsonResponse({'success': False, 'message': 'Invalid credentials'}, status=401)

        except Exception as e:
            return JsonResponse({'success': False, 'error': str(e)}, status=500)

    return JsonResponse({'success': False, 'error': 'Only POST method allowed'}, status=405)


class ScanTyreView(APIView):
    parser_classes = [MultiPartParser]

    def post(self, request, *args, **kwargs):
        image_file = request.FILES.get('image')
        if not image_file:
            return Response({'error': 'No image uploaded.'}, status=status.HTTP_400_BAD_REQUEST)

        try:
            # Save image temporarily
            filename = f"tyres/{uuid.uuid4().hex}_{image_file.name}"
            saved_path = default_storage.save(filename, ContentFile(image_file.read()))
            full_path = os.path.join(settings.MEDIA_ROOT, filename)

            # Read image as bytes
            with open(full_path, "rb") as img:
                image_bytes = img.read()

            # Use Gemini 1.5 Flash for analysis
            model = genai.GenerativeModel('models/gemini-1.5-flash')

            prompt = (
                "This image shows a vehicle tyre. "
                "Based on the visible tread depth, wear pattern, and cracks or damage, "
                "determine the quality of the tyre as Good, Average, or Bad. "
                "If this is not an image of a tyre, return: Invalid Image. "
                "Return only one of these words exactly: Good, Average, Bad, Invalid Image."
            )

            response = model.generate_content([
                prompt,
                {"mime_type": image_file.content_type, "data": image_bytes}
            ])

            result = response.text.strip()
            allowed_responses = ["Good", "Average", "Bad", "Invalid Image"]

            if result not in allowed_responses:
                result = "Invalid Image"

            # ✅ Save result to database
            TyreScan.objects.create(
                image=filename,
                result=result
            )

            # ✅ Return API response
            return Response({
                'result': result,
                'image_url': request.build_absolute_uri(settings.MEDIA_URL + filename)
            })

        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)


class TyreScanResultsView(APIView):
    def get(self, request):
        tyrescans = TyreScan.objects.all().order_by('-scanned_at')
        paginator = TyreScanPagination()
        result_page = paginator.paginate_queryset(tyrescans, request)
        serializer = TyreScanSerializer(result_page, many=True, context={'request': request})
        return paginator.get_paginated_response(serializer.data)
