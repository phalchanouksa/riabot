import requests
import uuid
from datetime import timedelta
from rest_framework import status
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from django.conf import settings
from django.utils import timezone
from rest_framework_simplejwt.tokens import AccessToken
from .models import ChatSession, ChatMessage
from .serializers import MessageRequestSerializer, ChatMessageSerializer, ChatSessionSerializer


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
            
            # Use consistent sender ID for Rasa session continuity
            rasa_sender_id = f"user_{request.user.id}"
            
            payload = {
                'sender': rasa_sender_id,
                'message': message
            }
            
            response = requests.post(
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
                if isinstance(rasa_response, dict) and 'text' in rasa_response:
                    bot_message = ChatMessage.objects.create(
                        session=session,
                        message_type='bot',
                        content=rasa_response['text'],
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
            
            return Response({
                'session_id': session.session_id,
                'user_message': ChatMessageSerializer(user_message).data,
                'bot_responses': ChatMessageSerializer([bot_message], many=True).data,
                'session_restarted': session_restarted,
                'rasa_status': 'offline',
                'chat_timeout_minutes': settings.CHAT_SESSION_TIMEOUT,
            })
            
        except Exception as e:
            error_message = ChatMessage.objects.create(
                session=session,
                message_type='bot',
                content="Sorry, I'm having trouble right now. Please try again in a moment.",
                metadata={'error': str(e)}
            )
            
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
        "In the meantime, you can type **'start'** to begin the career assessment "
        "or **'help'** to see what I can do."
    )
