import json
import logging
from django.conf import settings
from twilio.rest import Client
from twilio.twiml.messaging_response import MessagingResponse

# Enable logging
logger = logging.getLogger(__name__)

class WhatsAppHandler:
    """Handler for WhatsApp messaging using Twilio"""

    def __init__(self):
        self.account_sid = settings.TWILIO_ACCOUNT_SID
        self.auth_token = settings.TWILIO_AUTH_TOKEN
        self.phone_number = settings.TWILIO_PHONE_NUMBER

        if not all([self.account_sid, self.auth_token, self.phone_number]):
            logger.warning("Warning: Twilio credentials not fully configured")
            self.client = None
        else:
            self.client = Client(self.account_sid, self.auth_token)
            
        # Log configuration for debugging
        logger.info(f"WhatsApp Handler initialized - From number: {self.phone_number}")

    def send_message(self, to_number, message_body):
        """Send a text message via WhatsApp"""
        if not self.client:
            logger.info(f"[Debug Mode] Would send to {to_number}: {message_body}")
            return {"status": "debug_mode"}

        # Clean and validate phone numbers
        clean_to_number = to_number.replace('whatsapp:', '').strip()
        clean_from_number = self.phone_number.replace('whatsapp:', '').strip()
        
        # Log the numbers for debugging
        logger.info(f"[send_message] Attempting to send from {clean_from_number} to {clean_to_number}")
        
        # Check if From and To are the same (this causes Twilio error 63031)
        if clean_to_number == clean_from_number:
            logger.error(f"CONFIGURATION ERROR: Twilio From number ({clean_from_number}) is the same as recipient ({clean_to_number})")
            logger.error("Check your TWILIO_PHONE_NUMBER setting - it should be your Twilio WhatsApp sandbox number, not the user's number")
            return {"status": "error", "message": "Invalid Twilio configuration - From and To numbers are identical"}
        
        # Validate phone number format
        if not clean_to_number.startswith('+'):
            logger.warning(f"Phone number may be missing country code: {clean_to_number}")
        
        # Additional validation for Twilio WhatsApp sandbox
        if not clean_from_number.startswith('+'):
            logger.error(f"Twilio phone number missing country code: {clean_from_number}")
            return {"status": "error", "message": "Invalid Twilio phone number format"}
        
        try:
            logger.info(f"[send_message] Sending message to {clean_to_number}: {message_body[:100]}...")
            
            message = self.client.messages.create(
                body=message_body,
                from_=f"whatsapp:{clean_from_number}",
                to=f"whatsapp:{clean_to_number}"
            )
            logger.info(f"[send_message] Success. Message SID: {message.sid}")
            return {"status": "success", "sid": message.sid}
        except Exception as e:
            logger.error(f"[send_message] Twilio API Error: {str(e)}")
            logger.error(f"[send_message] From: whatsapp:{clean_from_number}, To: whatsapp:{clean_to_number}")
            return {"status": "error", "message": str(e)}


    def send_pdf(self, to_number, pdf_data, filename):
        """Handle PDF sharing request (WhatsApp doesn't support direct PDFs)"""
        if not self.client:
            print(f"[Debug Mode] Would send PDF {filename} to {to_number}")
            return {"status": "debug_mode"}

        try:
            # Twilio WhatsApp doesn't support direct PDF sending
            # Send a message indicating PDF availability
            message_body = (
                f"Your meal plan PDF ({filename}) is ready! "
                "PDF sharing via WhatsApp is coming soon. "
                "Please contact support to receive it via email."
            )
            print(f"[send_pdf] Sending PDF availability message to {to_number}")
            message = self.client.messages.create(
                body=message_body,
                from_=f"whatsapp:{self.phone_number}",
                to=f"whatsapp:{to_number}"
            )
            print(f"[send_pdf] Success. Message SID: {message.sid}")
            return {"status": "success", "sid": message.sid}
        except Exception as e:
            print(f"[send_pdf] Error: {str(e)}")
            return {"status": "error", "message": str(e)}
        
    def send_interactive_message(self, to_number, header_text, message_body, buttons=None):
        """Send an interactive message with numbered options"""
        if not buttons:
            return self.send_message(to_number, message_body)

        options_text = "\n".join([f"{i+1}. {button}" for i, button in enumerate(buttons)])
        full_message = f"{header_text}\n\n{message_body}\n\n{options_text}\n\nReply with a number to select an option."
        return self.send_message(to_number, full_message)

    def send_meal_plan_summary(self, to_number, meal_plan):
        """Send a summary of the weekly meal plan"""
        days = [day['day'] for day in meal_plan.get('days', [])]
        days_text = " | ".join(days)
        message = f"Here's your Meal Plan 🍽️\n\nType a day to view details:\n🗓️ {days_text}"
        return self.send_message(to_number, message)

    def send_meal_plan_day(self, to_number, day_data):
        """Send details of a specific day's meal plan"""
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
        """Send a daily nutrition tip"""
        content = tip.get('content', '')
        source = tip.get('source', '')

        message = f"🌿 Tip of the Day: {content}"
        if source:
            message += f"\n\n👩‍⚕️ Source: {source}"
        return self.send_message(to_number, message)

    def send_nudge(self, to_number, nudge):
        """Send a behavioral nudge"""
        content = nudge.get('content', '')
        message = f"⏰ {content}"
        return self.send_message(to_number, message)

    def parse_incoming_message(self, request):
        """Parse incoming WhatsApp message"""
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
                logger.error(f"Error parsing Twilio webhook: {e}")
                return None
        else:
            try:
                import json
                data = json.loads(request.body)
                return {
                    'from_number': data.get('from', ''),
                    'body': data.get('message', ''),
                    'media_url': data.get('media_url', None),
                    'message_sid': data.get('id', ''),
                    'num_media': 0
                }
            except Exception as e:
                logger.error(f"Error parsing direct API request: {e}")
                return None

    def build_response(self, message_text):
        """Build TwiML response for Twilio"""
        try:
            response = MessagingResponse()
            if message_text:  # Only add message if there's content
                response.message(message_text)
            return str(response)
        except Exception as e:
            logger.error(f"Error building TwiML response: {str(e)}")
            # Return empty response on error
            response = MessagingResponse()
            return str(response)
