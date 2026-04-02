import requests
import uuid
import json
import logging
from datetime import timedelta
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from django.utils import timezone
from .models import ChatSession, ChatMessage, SurveyResult
from .serializers import MessageRequestSerializer, ChatMessageSerializer, ChatSessionSerializer
from ml_engine.services.question_mapper import get_question_info
from ml_engine.services.recommender import MajorRecommender

logger = logging.getLogger(__name__)
RASA_HTTP_SESSION = requests.Session()


def _build_answer_trace(answers: dict) -> list[dict]:
    """
    Convert raw answer map into an ordered, admin-friendly survey trace.
    Keeps the original ask order when the JSON object preserves insertion order.
    """
    if not isinstance(answers, dict):
        return []

    trace = []
    for order, (question_idx, answer_value) in enumerate(answers.items(), start=1):
        try:
            question_idx_int = int(question_idx)
            answer_value_int = int(answer_value)
        except (TypeError, ValueError):
            continue

        if question_idx_int < 96:
            category_id = question_idx_int // 6
            dimension = 'interest'
        else:
            category_id = (question_idx_int - 96) // 10
            dimension = 'skill'

        question_info = get_question_info(question_idx_int) or {}
        trace.append({
            'order': order,
            'question_index': question_idx_int,
            'question_text': question_info.get('text', ''),
            'dimension': dimension,
            'category_id': category_id,
            'category_name': MajorRecommender.get_major_name(category_id),
            'answer_value': answer_value_int,
        })

    return trace


@api_view(['POST'])
@permission_classes([IsAuthenticated])
def send_message(request):
    """
    Send a message to Rasa and return bot responses.
    Flow: React -> Django -> Rasa -> Custom Actions (Qwen + ML) -> Django -> React
    """
    serializer = MessageRequestSerializer(data=request.data)
    if serializer.is_valid():
        message = serializer.validated_data['message']
        session_id = serializer.validated_data.get('session_id')
        
        session = None
        session_restarted = False
        
        # Check for existing chat session
        if session_id:
            try:
                session = ChatSession.objects.get(
                    session_id=session_id, 
                    user=request.user,
                    is_active=True
                )
                
                # Check session timeout
                timeout_threshold = timezone.now() - timedelta(minutes=settings.CHAT_SESSION_TIMEOUT)
                
                if session.updated_at < timeout_threshold:
                    session.is_active = False
                    session.save()
                    session = None
                    session_restarted = True
                    
            except ChatSession.DoesNotExist:
                session_restarted = True
        
        # Create new session if needed
        if not session:
            session_id = str(uuid.uuid4())
            session = ChatSession.objects.create(
                user=request.user,
                session_id=session_id
            )
            session_restarted = True
        
        # Save user message
        user_message = ChatMessage.objects.create(
            session=session,
            message_type='user',
            content=message
        )
        
        try:
            # Send to Rasa
            rasa_url = f"{settings.RASA_URL}/webhooks/rest/webhook"
            
            # Keep one Rasa tracker per Django chat session so refresh/history
            # can resume the same conversation without leaking across sessions.
            rasa_sender_id = session.session_id
            
            payload = {
                'sender': rasa_sender_id,
                'message': message
            }
            
            response = RASA_HTTP_SESSION.post(
                rasa_url, 
                json=payload, 
                headers={'Content-Type': 'application/json'}, 
                timeout=60  # Longer timeout since Qwen generation takes time
            )
            
            if response.status_code == 200:
                rasa_responses = response.json()
            else:
                print(f"Rasa returned status {response.status_code}: {response.text}")
                rasa_responses = []
            
            # Save bot responses
            bot_messages = []
            for rasa_response in rasa_responses:
                if isinstance(rasa_response, dict) and any(
                    key in rasa_response for key in ('text', 'buttons', 'custom')
                ):
                    bot_message = ChatMessage.objects.create(
                        session=session,
                        message_type='bot',
                        content=rasa_response.get('text', ''),
                        metadata=rasa_response
                    )
                    bot_messages.append(bot_message)
            
            # Fallback if Rasa returns nothing
            if not bot_messages:
                # Try using Qwen directly as fallback
                fallback_text = _get_fallback_response(message)
                bot_message = ChatMessage.objects.create(
                    session=session,
                    message_type='bot',
                    content=fallback_text,
                    metadata={'fallback': True}
                )
                bot_messages.append(bot_message)

            session.save()
            
            return Response({
                'session_id': session.session_id,
                'user_message': ChatMessageSerializer(user_message).data,
                'bot_responses': ChatMessageSerializer(bot_messages, many=True).data,
                'session_restarted': session_restarted,
                'chat_timeout_minutes': settings.CHAT_SESSION_TIMEOUT,
                'user_still_authenticated': True
            })
            
        except requests.ConnectionError:
            # Rasa is not running - use Qwen directly as fallback
            fallback_text = _get_fallback_response(message)
            
            bot_message = ChatMessage.objects.create(
                session=session,
                message_type='bot',
                content=fallback_text,
                metadata={'rasa_offline': True, 'qwen_fallback': True}
            )
            session.save()
            
            return Response({
                'session_id': session.session_id,
                'user_message': ChatMessageSerializer(user_message).data,
                'bot_responses': ChatMessageSerializer([bot_message], many=True).data,
                'session_restarted': session_restarted,
                'rasa_status': 'offline',
                'chat_timeout_minutes': settings.CHAT_SESSION_TIMEOUT,
            })
            
        except Exception as e:
            logger.exception("Chat send_message failed for session %s", session.session_id if session else "unknown")
            error_message = ChatMessage.objects.create(
                session=session,
                message_type='bot',
                content="Sorry, I'm having trouble right now. Please try again in a moment.",
                metadata={'error': str(e)}
            )
            session.save()
            
            return Response({
                'session_id': session.session_id,
                'user_message': ChatMessageSerializer(user_message).data,
                'bot_responses': ChatMessageSerializer([error_message], many=True).data,
                'session_restarted': session_restarted,
                'error': 'Connection failed'
            })
    
    return Response(serializer.errors, status=status.HTTP_400_BAD_REQUEST)


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_sessions(request):
    """Get all chat sessions for the authenticated user."""
    sessions = ChatSession.objects.filter(
        user=request.user
    ).order_by('-updated_at')[:20]
    
    serializer = ChatSessionSerializer(sessions, many=True)
    return Response({'sessions': serializer.data})


@api_view(['GET'])
@permission_classes([IsAuthenticated])
def get_chat_history(request, session_id):
    """Get chat history for a specific session."""
    try:
        session = ChatSession.objects.get(
            session_id=session_id,
            user=request.user
        )
        messages = ChatMessage.objects.filter(session=session).order_by('timestamp')
        serializer = ChatMessageSerializer(messages, many=True)
        return Response({
            'session_id': session_id,
            'messages': serializer.data
        })
    except ChatSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['DELETE'])
@permission_classes([IsAuthenticated])
def delete_session(request, session_id):
    """Delete a chat session."""
    try:
        session = ChatSession.objects.get(
            session_id=session_id,
            user=request.user
        )
        session.delete()
        return Response({'message': 'Session deleted successfully'})
    except ChatSession.DoesNotExist:
        return Response({'error': 'Session not found'}, status=status.HTTP_404_NOT_FOUND)


@api_view(['POST'])
@permission_classes([AllowAny])
def store_survey_result_internal(request):
    """
    Save a completed survey result from the Rasa action server.
    Uses the Django chat session id as the conversation key.
    """
    expected_token = getattr(settings, 'RASA_TOKEN_SECRET', '')
    provided_token = request.headers.get('X-RiaBot-Internal-Token') or request.data.get('internal_token')

    if expected_token and provided_token != expected_token:
        return Response({'error': 'Forbidden'}, status=status.HTTP_403_FORBIDDEN)

    session_id = request.data.get('session_id')
    result = request.data.get('result') or {}
    explanation = request.data.get('explanation', '')
    answers = request.data.get('answers') or {}

    if not session_id:
        return Response({'error': 'session_id is required'}, status=status.HTTP_400_BAD_REQUEST)

    if not isinstance(result, dict):
        return Response({'error': 'result must be an object'}, status=status.HTTP_400_BAD_REQUEST)

    is_unclear_profile = result.get('final_state') == 'unclear'
    if not result.get('major') and not is_unclear_profile:
        return Response({'error': 'result.major is required'}, status=status.HTTP_400_BAD_REQUEST)

    try:
        session = ChatSession.objects.select_related('user').get(session_id=session_id)
    except ChatSession.DoesNotExist:
        return Response({'error': 'Chat session not found'}, status=status.HTTP_404_NOT_FOUND)

    answer_trace = _build_answer_trace(answers)
    saved_result = SurveyResult.objects.create(
        user=session.user,
        session=session,
        recommended_major='Unclear' if is_unclear_profile else str(result.get('major', '')),
        confidence=float(result.get('confidence') or 0.0),
        questions_answered=int(result.get('questions_asked') or 0),
        explanation=explanation or '',
        result_payload={
            'major_id': result.get('major_id'),
            'top_3': result.get('top_3', []),
            'university_recommendations': result.get('university_recommendations', []),
            'stage': result.get('stage'),
            'final_state': result.get('final_state'),
            'questions_asked': result.get('questions_asked'),
            'raw_answers': answers,
            'answer_trace': answer_trace,
        },
    )

    return Response({
        'status': 'saved',
        'survey_result_id': saved_result.id,
        'trace_count': len(answer_trace),
    })


def _get_fallback_response(message: str) -> str:
    """
    Generate a fallback response when Rasa is offline.
    Tries Qwen first, then uses static fallback.
    """
    try:
        from ml_engine.services.llm_service import generate_response, is_available
        
        if is_available():
            response = generate_response(
                message,
                system_prompt=(
                    "You are RiaBot, a friendly career guidance chatbot. "
                    "Note: The main dialogue system (Rasa) is currently offline, "
                    "so you're responding directly. Be helpful and suggest the user "
                    "try again later for the full career assessment experience. "
                    "Keep responses short (1-3 sentences)."
                ),
                max_tokens=200
            )
            if response:
                return response
    except Exception:
        pass
    
    # Static fallback
    return (
        "Hello! I'm RiaBot, your career guidance assistant. 😊\n\n"
        "I'm currently setting up my systems. Please try again in a moment!\n\n"
    )
