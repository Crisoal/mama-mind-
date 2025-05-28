# chatbot/views.py
import logging
from django.http import HttpResponse, JsonResponse
from django.views.decorators.csrf import csrf_exempt
from django.utils import timezone
from .models import User
from .whatsapp import WhatsAppHandler
from .bot_logic import BotLogic
from threading import Thread
import time

# Enable logging
logger = logging.getLogger(__name__)
whatsapp_handler = WhatsAppHandler()

# Initialize BotLogic with initialize_db=False to defer database operations
# This will be replaced with a fully initialized instance after migrations
bot_logic = None

def get_bot_logic():
    """
    Get or initialize the BotLogic instance.
    This allows for lazy initialization after migrations are complete.
    """
    global bot_logic
    if bot_logic is None:
        try:
            bot_logic = BotLogic(initialize_db=True)
            logger.info("BotLogic initialized successfully")
        except Exception as e:
            logger.error(f"Error initializing BotLogic: {str(e)}")
            # Create instance without DB initialization as fallback
            bot_logic = BotLogic(initialize_db=False)
    return bot_logic

def process_message_async(from_number, message_body):
    """Process message asynchronously to prevent Twilio timeout"""
    try:
        logger.info(f"Processing message asynchronously for {from_number}: {message_body}")
        bot = get_bot_logic()
        response = bot.process_message(from_number, message_body)
        logger.info(f"Async BotLogic response: {response}")
        
        # If this was a meal plan generation, the response is already sent
        # within the _generate_meal_plan method, so we don't need to send again
        
    except Exception as e:
        logger.error(f"Error in async processing: {str(e)}")
        # Send error message to user
        try:
            error_response = "Sorry, something went wrong. Please try again later."
            whatsapp_handler.send_message(from_number, error_response)
        except Exception as send_error:
            logger.error(f"Failed to send error message: {str(send_error)}")

def is_meal_plan_request(message_body):
    """Check if the message is requesting a meal plan"""
    meal_plan_keywords = [
        'meal plan', 'mealplan', 'weekly plan', 'food plan', 
        'nutrition plan', 'eating plan', 'menu', 'meals'
    ]
    message_lower = message_body.lower().strip()
    return any(keyword in message_lower for keyword in meal_plan_keywords)

@csrf_exempt
def webhook(request):
    logger.info("Incoming WhatsApp webhook hit.")
    parsed_message = whatsapp_handler.parse_incoming_message(request)
    if not parsed_message:
        logger.error("Failed to parse incoming message.")
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    from_number = parsed_message['from_number']
    message_body = parsed_message['body']
    logger.info(f"Parsed message from {from_number}: {message_body}")

    # Check if this is a meal plan request that might take time
    if is_meal_plan_request(message_body):
        logger.info("Detected meal plan request - processing asynchronously")
        
        # Start async processing
        thread = Thread(target=process_message_async, args=(from_number, message_body))
        thread.daemon = True
        thread.start()
        
        # Return immediate response to Twilio to prevent timeout
        twiml = whatsapp_handler.build_response("")  # Empty response to Twilio
        logger.info("Sent immediate empty TwiML response for async processing.")
        return HttpResponse(twiml, content_type='application/xml')
    
    # For non-meal plan requests, process synchronously
    try:
        bot = get_bot_logic()
        response = bot.process_message(from_number, message_body)
        logger.info(f"BotLogic response: {response}")
    except Exception as e:
        logger.error(f"Error processing message: {str(e)}")
        response = "Sorry, something went wrong. Please try again later."
        return JsonResponse({'status': 'error', 'message': str(e)}, status=500)

    # Send the response via WhatsApp
    twiml = whatsapp_handler.build_response(response)
    logger.info("Sending TwiML response.")
    return HttpResponse(twiml, content_type='application/xml')

@csrf_exempt
def scheduled_tasks(request):
    """Endpoint for Celery to trigger scheduled tips, nudges, and meal plans"""
    if request.method != 'POST':
        logger.error("Invalid request method for scheduled tasks.")
        return JsonResponse({'status': 'error', 'message': 'Method not allowed'}, status=405)
    
    logger.info("Processing scheduled tasks.")
    current_day = timezone.now().strftime('%A')  # For weekly meal plans (e.g., Monday)
    
    # Get BotLogic instance using helper function
    bot = get_bot_logic()
    
    for user in User.objects.filter(last_active__isnull=False):
        try:
            # Send daily tip (8:00 AM)
            tip_result = bot.send_daily_tip(user)
            if tip_result:
                logger.info(f"Sent daily tip to {user.phone_number}: {tip_result}")
            
            # Send nudge (10:00 AM)
            nudge_result = bot.send_nudge(user)
            if nudge_result:
                logger.info(f"Sent nudge to {user.phone_number}: {nudge_result}")
            
            # Send weekly meal plan (Monday)
            if current_day == 'Monday' and user.wants_meal_plans:
                plan_result = bot.send_scheduled_meal_plan(user)
                if plan_result:
                    logger.info(f"Sent meal plan to {user.phone_number}: {plan_result}")
        except Exception as e:
            logger.error(f"Error processing scheduled tasks for {user.phone_number}: {str(e)}")
    
    return JsonResponse({'status': 'success', 'message': 'Scheduled tasks processed'}, status=200)