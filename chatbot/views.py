# chatbot/views.py
from django.views.decorators.csrf import csrf_exempt
from django.http import HttpResponse, JsonResponse
from django.views import View

from .whatsapp import WhatsAppHandler

whatsapp_handler = WhatsAppHandler()

@csrf_exempt
def webhook(request):
    parsed_message = whatsapp_handler.parse_incoming_message(request)

    if not parsed_message:
        return JsonResponse({'status': 'error', 'message': 'Invalid request'}, status=400)

    from_number = parsed_message['from_number']
    message_body = parsed_message['body'].strip().lower()

    # Basic keyword handling
    if message_body in ['hi', 'hello']:
        response = "👋 Hi there! Welcome to our MamáMind.\nType `plan` to get your meal plan or `tip` for a nutrition tip."
    elif message_body == 'plan':
        sample_plan = {
            'days': [{'day': 'Monday'}, {'day': 'Tuesday'}, {'day': 'Wednesday'}]
        }
        whatsapp_handler.send_meal_plan_summary(from_number, sample_plan)
        return HttpResponse(status=200)
    elif message_body == 'tip':
        tip = {
            'title': 'Hydration Tip',
            'content': 'Drink at least 8 glasses of water a day to stay hydrated.',
            'source': 'Healthline'
        }
        whatsapp_handler.send_daily_tip(from_number, tip)
        return HttpResponse(status=200)
    else:
        response = "❓ Sorry, I didn’t understand that. Try typing `plan` or `tip`."

    twiml = whatsapp_handler.build_response(response)
    return HttpResponse(twiml, content_type='application/xml')
