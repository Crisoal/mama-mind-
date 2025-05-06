# chatbot/whatsapp.py
import json
from django.conf import settings
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

class WhatsAppHandler:
    """Handler for WhatsApp messaging using Twilio"""

    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.phone_number = settings.TWILIO_PHONE_NUMBER

        if not all([self.account_sid, self.auth_token, self.phone_number]):
            print("Warning: Twilio credentials not fully configured")
            self.client = None
        else:
            self.client = Client(self.account_sid, self.auth_token)

    def send_message(self, to_number, message_body):
        if not self.client:
            print(f"[Debug Mode] Would send to {to_number}: {message_body}")
            return {"status": "debug_mode"}

        try:
            message = self.client.messages.create(
                body=message_body,
                from_=f"whatsapp:{self.phone_number}",
                to=f"whatsapp:{to_number}"
            )
            return {"status": "success", "sid": message.sid}
        except Exception as e:
            return {"status": "error", "message": str(e)}

    def build_response(self, message_body):
        response = MessagingResponse()
        response.message(message_body)
        return str(response)

    def send_interactive_message(self, to_number, header_text, message_body, buttons=None):
        if not buttons:
            return self.send_message(to_number, message_body)

        options_text = "\n".join([f"{i+1}. {button}" for i, button in enumerate(buttons)])
        full_message = f"{header_text}\n\n{message_body}\n\n{options_text}\n\nReply with a number to select an option."
        return self.send_message(to_number, full_message)

    def send_meal_plan_summary(self, to_number, meal_plan):
        days = [day['day'] for day in meal_plan.get('days', [])]
        days_text = " | ".join(days)
        message = f"Here's your Meal Plan 🍽️\n\nType a day to view details:\n{days_text}"
        return self.send_message(to_number, message)

    def send_meal_plan_day(self, to_number, day_data):
        day = day_data.get('day', 'Today')
        meals = day_data.get('meals', {})

        message_parts = [f"🗓️ {day}"]

        meal_emojis = {
            "Breakfast": "🥣",
            "Lunch": "🍛",
            "Snack 1": "🍎",
            "Snack 2": "🍵",
            "Dinner": "🍲"
        }

        for meal_type, details in meals.items():
            emoji = meal_emojis.get(meal_type, "🍽️")
            name = details.get('name', 'Not specified')
            description = details.get('description', '')
            meal_text = f"{emoji} {meal_type}: {name}"
            if description:
                meal_text += f"\n   {description}"
            message_parts.append(meal_text)

        if 'tip' in day_data:
            message_parts.append(f"🧠 Tip: {day_data['tip']}")

        message = "\n\n".join(message_parts)
        return self.send_message(to_number, message)

    def send_daily_tip(self, to_number, tip):
        title = tip.get('title', 'Daily Nutrition Tip')
        content = tip.get('content', '')
        source = tip.get('source', '')

        message = f"🌿 {title}\n\n{content}"
        if source:
            message += f"\n\n👩‍⚕️ Source: {source}"
        return self.send_message(to_number, message)

    def parse_incoming_message(self, request):
        if request.POST:
            try:
                return {
                    'from_number': request.POST.get('From', '').replace('whatsapp:', ''),
                    'body': request.POST.get('Body', ''),
                    'media_url': request.POST.get('MediaUrl0', None),
                    'message_sid': request.POST.get('MessageSid', ''),
                    'num_media': int(request.POST.get('NumMedia', 0))
                }
            except Exception as e:
                print(f"Error parsing Twilio webhook: {e}")
                return None
        else:
            try:
                data = json.loads(request.body)
                return {
                    'from_number': data.get('from', ''),
                    'body': data.get('message', ''),
                    'media_url': data.get('media_url', None),
                    'message_sid': data.get('id', ''),
                    'num_media': 0
                }
            except Exception as e:
                print(f"Error parsing direct API request: {e}")
                return None
