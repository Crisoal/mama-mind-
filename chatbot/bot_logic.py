# chatbot/bot_logic.py
import json
import random
import os
import sys
import time
from django.db import IntegrityError
from twilio.twiml.messaging_response import MessagingResponse
from datetime import datetime, timedelta
from django.utils import timezone
from reportlab.lib.pagesizes import letter
from reportlab.platypus import SimpleDocTemplate, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
import io
from io import BytesIO  # Added missing import

from .models import User, DietaryPreference, PregnancyCondition, Conversation, MealPlan, NutritionTip
from .utils.sonar import SonarAPI
from .whatsapp import WhatsAppHandler
import logging

# Set up logging
logger = logging.getLogger(__name__)

logging.basicConfig(
    stream=sys.stdout,
    level=logging.INFO,
    format='%(asctime)s - %(levelname)s - %(message)s',
    encoding='utf-8'  # Add this
)

class BotLogic:
    """Core logic for the chatbot"""
    def __init__(self, initialize_db=True):
        self.sonar = SonarAPI()
        self.whatsapp = WhatsAppHandler()
        
        # Initialize common data structures
        self.TRIMESTERS = [1, 2, 3]
        self.DIETARY_PREFERENCES = ["Vegetarian", "Vegan", "Gluten-free", "Dairy-free", "No restrictions", "Other"]
        self.PREGNANCY_CONDITIONS = ["Anemia or low iron", "Gestational diabetes", "Hypertension", "Morning sickness", "None", "Other"]
        self.USAGE_PREFERENCES = ["Weekly meal plans", "Daily nutrition tips", "Recipe suggestions", "Nutrition Q&A", "All of the above"]
        
        # Create necessary database objects if requested
        # This parameter allows us to skip DB operations during migrations
        if initialize_db:
            try:
                self._ensure_preferences_exist()
            except Exception as e:
                print(f"Warning: Could not initialize preferences: {e}")

    def _ensure_preferences_exist(self):
        """Ensure all dietary preferences and pregnancy conditions exist in the database"""
        for pref in self.DIETARY_PREFERENCES:
            DietaryPreference.objects.get_or_create(name=pref)
        
        for condition in self.PREGNANCY_CONDITIONS:
            PregnancyCondition.objects.get_or_create(name=condition)

    def process_message(self, from_number, message_body):
        """
        Process an incoming message and generate a response
        Args:
            from_number (str): The sender's phone number
            message_body (str): The message body
        Returns:
            str: The response message
        """
        # Get or create the user
        user, created = User.objects.get_or_create(phone_number=from_number)
        
        # Update last active timestamp
        user.last_active = timezone.now()
        user.save()
        
        # Check for command messages
        if message_body.lower() in ["start", "hi", "hello"]:
            user.conversation_state = "ONBOARDING_START"
            user.save()
            return self._handle_onboarding_start(user)
        
        if message_body.lower() == "end":
            user.conversation_state = "COMPLETED_ONBOARDING"
            user.save()
            return "Thank you for using MamáMind! Your preferences have been saved. Type 'Start' anytime to chat again."
        
        if message_body.lower() == "start over":
            user.conversation_state = "CONFIRM_RESET"
            user.save()
            return "This will clear your profile. Confirm? (Yes/No)"
        
        if message_body.lower() in ["settings", "update preferences"]:
            user.conversation_state = "ONBOARDING_START"
            user.save()
            return "Let's update your preferences. " + self._handle_onboarding_start(user)
        
            # Add menu handling
        if message_body.lower() in ["menu", "help", "options"]:
            return self._show_menu(user)
        
        if message_body.lower() in ["meal plan", "generate meal plan"]:
            return self._generate_meal_plan(user)
        
        
        # Handle user state
        if user.conversation_state == "CONFIRM_RESET":
            return self._handle_reset_confirmation(user, message_body)
        
        elif user.conversation_state == "ONBOARDING_START":
            return self._handle_onboarding_start(user)
        
        elif user.conversation_state == "AWAITING_TRIMESTER":
            return self._handle_trimester_response(user, message_body)
        
        elif user.conversation_state == "AWAITING_DIETARY_PREFERENCES":
            return self._handle_dietary_preferences_response(user, message_body)
        
        elif user.conversation_state == "AWAITING_ALLERGIES":
            return self._handle_allergies_response(user, message_body)
        
        elif user.conversation_state == "AWAITING_CULTURAL_PREFERENCES":
            return self._handle_cultural_preferences_response(user, message_body)
        
        elif user.conversation_state == "AWAITING_PREGNANCY_CONDITIONS":
            return self._handle_pregnancy_conditions_response(user, message_body)
        
        elif user.conversation_state == "AWAITING_USAGE_PREFERENCES":
            return self._handle_usage_preferences_response(user, message_body)
        
        elif user.conversation_state == "AWAITING_MEAL_PLAN_DAY":
            return self._handle_meal_plan_day_selection(user, message_body)
        
        elif user.conversation_state == "AWAITING_SHARE_CONFIRMATION":
            return self._handle_share_confirmation(user, message_body)
        
        # Default to Q&A mode if onboarding is complete
        else:
            return self._handle_nutrition_question(user, message_body)

    def _show_menu(self, user):
        """Show available commands to user"""
        if user.conversation_state in ["COMPLETED_ONBOARDING", None]:
            return (
                "🌟 **MamáMind Menu**\n\n"
                "🍽️ **meal plan** - Get personalized weekly meals\n"
                "❓ **Ask questions** - Pregnancy nutrition Q&A\n"
                "💡 **daily tip** - Get today's nutrition tip\n"
                "⚙️ **settings** - Update your preferences\n"
                "📤 **share** - Share your meal plan\n\n"
                "💬 *Just type any option or ask me anything!*"
            )
        else:
            return "Let me help you complete your profile first! 😊"

    def _handle_reset_confirmation(self, user, message):
        """Handle confirmation for resetting user profile"""
        if message.lower() == "yes":
            user.reset_preferences()
            user.conversation_state = "ONBOARDING_START"
            user.save()
            return "Profile cleared. Let's start fresh! " + self._handle_onboarding_start(user)
        else:
            user.conversation_state = "COMPLETED_ONBOARDING"
            user.save()
            return "Okay, your profile remains unchanged. Type a question or 'Generate meal plan' to continue."

    def get_daily_tip():
        tips = [
            "🌿 Daily Tip: Add greens like spinach to your meals – they're high in folate and support the baby’s brain development.",
            "🍊 Daily Tip: Pair iron-rich foods with Vitamin C for better absorption. Try lentils with lemon or orange slices.",
            "🥥 Daily Tip: Coconut water helps keep you hydrated and balances electrolytes during pregnancy.",
            "🥬 Daily Tip: Ugu and spinach are packed with folate – essential for your baby’s brain and spine.",
            "💤 Daily Tip: Aim for 7-9 hours of sleep. Proper rest supports healthy fetal growth.",
        ]
        index = datetime.datetime.now().day % len(tips)
        return tips[index]

    def get_daily_tip(self):
        """Return a daily tip based on the day of the month"""
        tips = [
            "🌿 Daily Tip: Add greens like spinach to your meals – they're high in folate and support the baby’s brain development.",
            "🍊 Daily Tip: Pair iron-rich foods with Vitamin C for better absorption. Try lentils with lemon or orange slices.",
            "🥥 Daily Tip: Coconut water helps keep you hydrated and balances electrolytes during pregnancy.",
            "🥬 Daily Tip: Ugu and spinach are packed with folate – essential for your baby’s brain and spine.",
            "💤 Daily Tip: Aim for 7-9 hours of sleep. Proper rest supports healthy fetal growth.",
        ]
        import datetime
        index = datetime.datetime.now().day % len(tips)
        return tips[index]


    def _handle_onboarding_start(self, user):
        """Handle the start of onboarding with daily tip"""
        user.conversation_state = "AWAITING_TRIMESTER"
        user.save()

        tip = self.get_daily_tip()

        return (
            f"{tip}\n\n"
            "👋 Hi! I'm MamáMind, your AI-powered pregnancy nutrition coach. "
            "Let's create your personalized nutrition journey! 🍎🤰\n\n"
            "Which trimester are you in?\n"
            "1. First\n"
            "2. Second\n"
            "3. Third"
        )


    def _handle_trimester_response(self, user, message):
        """Handle the trimester response"""
        try:
            trimester = int(message.strip())
            if trimester not in self.TRIMESTERS:
                return "Please enter a valid trimester (1, 2, or 3)."
            
            user.trimester = trimester
            user.conversation_state = "AWAITING_DIETARY_PREFERENCES"
            user.save()
            
            options = "\n".join([f"{i+1}. {pref}" for i, pref in enumerate(self.DIETARY_PREFERENCES)])
            return f"Thanks! Do you have any dietary restrictions or preferences?\n\n{options}"
            
        except ValueError:
            return "Please enter a valid number for your trimester."

    def _handle_dietary_preferences_response(self, user, message):
        """Handle the dietary preferences response"""
        try:
            selections = [int(x.strip()) for x in message.split(',')]
            if any(s < 1 or s > len(self.DIETARY_PREFERENCES) for s in selections):
                return f"Please enter valid numbers between 1 and {len(self.DIETARY_PREFERENCES)}."
            
            user.dietary_preferences.clear()
            other_input = None
            for selection in selections:
                pref_name = self.DIETARY_PREFERENCES[selection - 1]
                if pref_name == "Other":
                    other_input = "Please specify your other dietary preferences:"
                    user.conversation_state = "AWAITING_OTHER_DIETARY"
                else:
                    pref = DietaryPreference.objects.get(name=pref_name)
                    user.dietary_preferences.add(pref)
            
            if other_input:
                user.save()
                return other_input
            else:
                user.conversation_state = "AWAITING_ALLERGIES"
                user.save()
                selected_prefs = [self.DIETARY_PREFERENCES[s - 1] for s in selections]
                return (
                    f"Got it – {', '.join(selected_prefs)}!\n\n"
                    "Any food allergies or intolerances I should know about? "
                    "Please list them, or type NONE."
                )
                
        except ValueError:
            return "Please enter valid numbers for your dietary preferences."

    def _handle_other_dietary_response(self, user, message):
        """Handle free-text input for 'Other' dietary preferences"""
        user.other_dietary_preferences = message.strip()
        user.conversation_state = "AWAITING_ALLERGIES"
        user.save()
        return (
            f"Got it – {message.strip()} added to your preferences!\n\n"
            "Any food allergies or intolerances I should know about? "
            "Please list them, or type NONE."
        )

    def _handle_allergies_response(self, user, message):
        """Handle the allergies response"""
        allergies = message.strip()
        if allergies.lower() == "none":
            allergies = ""
        
        user.allergies = allergies
        user.conversation_state = "AWAITING_CULTURAL_PREFERENCES"
        user.save()
        
        allergy_confirmation = "no allergies" if not allergies else f"avoiding {allergies}"
        
        return (
            f"Noted – {allergy_confirmation}.\n\n"
            "Which cuisine or cultural food traditions do you typically follow? "
            "This helps me suggest meals you'll enjoy."
        )

    def _handle_cultural_preferences_response(self, user, message):
        """Handle the cultural preferences response"""
        cultural_pref = message.strip()
        user.cultural_preferences = cultural_pref
        user.conversation_state = "AWAITING_PREGNANCY_CONDITIONS"
        user.save()
        
        options = "\n".join([f"{i+1}. {cond}" for i, cond in enumerate(self.PREGNANCY_CONDITIONS)])
        
        return (
            f"Wonderful! {cultural_pref} cuisine has many excellent options perfect for pregnancy.\n\n"
            "Have you been diagnosed with any pregnancy-related conditions? Select all that apply:\n\n"
            f"{options}"
        )

    def _handle_pregnancy_conditions_response(self, user, message):
        """Handle the pregnancy conditions response"""
        try:
            selections = [int(x.strip()) for x in message.split(',')]
            if any(s < 1 or s > len(self.PREGNANCY_CONDITIONS) for s in selections):
                return f"Please enter valid numbers between 1 and {len(self.PREGNANCY_CONDITIONS)}."
            
            user.pregnancy_conditions.clear()
            other_input = None
            for selection in selections:
                cond_name = self.PREGNANCY_CONDITIONS[selection - 1]
                if cond_name == "Other":
                    other_input = "Please specify your other pregnancy conditions:"
                    user.conversation_state = "AWAITING_OTHER_CONDITIONS"
                elif cond_name != "None":
                    cond = PregnancyCondition.objects.get(name=cond_name)
                    user.pregnancy_conditions.add(cond)
            
            if other_input:
                user.save()
                return other_input
            else:
                user.conversation_state = "AWAITING_USAGE_PREFERENCES"
                user.save()
                selected_conds = [self.PREGNANCY_CONDITIONS[s - 1] for s in selections if self.PREGNANCY_CONDITIONS[s - 1] != "None"]
                confirmation = f"I'll focus on options to support {', '.join(selected_conds)}." if selected_conds else "No specific conditions noted."
                
                options = "\n".join([f"{i+1}. {pref}" for i, pref in enumerate(self.USAGE_PREFERENCES)])
                
                return (
                    f"Thanks – {confirmation}\n\n"
                    "How would you like to use MamáMind? Choose your preferences:\n\n"
                    f"{options}"
                )
                
        except ValueError:
            return "Please enter valid numbers for your pregnancy conditions."

    def _handle_other_conditions_response(self, user, message):
        """Handle free-text input for 'Other' pregnancy conditions"""
        user.other_conditions = message.strip()
        user.conversation_state = "AWAITING_USAGE_PREFERENCES"
        user.save()
        options = "\n".join([f"{i+1}. {pref}" for i, pref in enumerate(self.USAGE_PREFERENCES)])
        return (
            f"Thanks – I'll note {message.strip()}.\n\n"
            "How would you like to use MamáMind? Choose your preferences:\n\n"
            f"{options}"
        )

    def _handle_usage_preferences_response(self, user, message):
        """Handle the usage preferences response"""
        try:
            if message.strip() == "5":
                user.wants_meal_plans = True
                user.wants_nutrition_tips = True
                user.wants_recipe_suggestions = True
                user.wants_nutrition_qa = True
            else:
                selections = [int(x.strip()) for x in message.split(',')]
                if any(s < 1 or s > len(self.USAGE_PREFERENCES) for s in selections):
                    return f"Please enter valid numbers between 1 and {len(self.USAGE_PREFERENCES)}."
                
                user.wants_meal_plans = 1 in selections
                user.wants_nutrition_tips = 2 in selections
                user.wants_recipe_suggestions = 3 in selections
                user.wants_nutrition_qa = 4 in selections
            
            user.conversation_state = "COMPLETED_ONBOARDING"
            user.save()
            
            # Use the new completion message method
            return self._get_onboarding_completion_message(user)
                
        except ValueError:
            return "Please enter valid numbers for your usage preferences."

    def _get_onboarding_completion_message(self, user):
        """Generate completion message with available options"""
        trimester_text = f"Trimester {user.trimester}"
        diet_text = ", ".join(user.get_dietary_preferences_list()) + (f", {user.other_dietary_preferences}" if user.other_dietary_preferences else "")
        allergies_text = user.allergies if user.allergies else "No allergies"
        cuisine_text = user.cultural_preferences
        conditions_text = ", ".join(user.get_pregnancy_conditions_list()) + (f", {user.other_conditions}" if user.other_conditions else "") if user.get_pregnancy_conditions_list() or user.other_conditions else "No specific conditions"
        
        profile_summary = (
            f"✅ {trimester_text}\n"
            f"✅ {diet_text}\n"
            f"✅ {allergies_text}\n"
            f"✅ {cuisine_text} cuisine preference\n"
            f"✅ {conditions_text}"
        )
        
        options_menu = (
            "\n\n✨ **What would you like to do?**\n"
            "🍽️ **meal plan** - Get personalized weekly meals\n"
            "❓ **Ask questions** - Pregnancy nutrition Q&A\n"
            "💡 **daily tip** - Get today's nutrition tip\n"
            "📋 **menu** - See all options anytime\n"
            "⚙️ **settings** - Update preferences\n\n"
            "💬 *Just type any option or ask me anything!*"
        )
        
        return (
            f"🎉 Perfect! Your profile is set up. Based on your information:\n\n"
            f"{profile_summary}"
            f"{options_menu}"
        )

    def _generate_meal_plan(self, user, is_scheduled=False):
        """Generate a meal plan for the user, always creating a new one"""
        logger.info(f"Generating meal plan for user {user.id}, trimester {user.trimester}")
        
        try:
            # Send immediate progress indicator to user (non-scheduled only)
            if not is_scheduled:
                progress_message = "🍽️ Generating your personalized meal plan... This may take a few moments."
                try:
                    from .whatsapp import WhatsAppHandler
                    whatsapp_handler = WhatsAppHandler()
                    whatsapp_handler.send_message(user.phone_number, progress_message)
                    logger.info(f"Sent progress indicator to user {user.id}")
                except Exception as progress_error:
                    logger.warning(f"Failed to send progress indicator: {str(progress_error)}")
            
            # Always generate a random week number for variety
            if user.trimester == 1:
                week_number = random.randint(1, 12)
            elif user.trimester == 2:
                week_number = random.randint(13, 26)
            else:
                week_number = random.randint(27, 40)
            
            # Build user profile
            user_profile = {
                'trimester': user.trimester,
                'dietary_preferences': user.get_dietary_preferences_list() + ([user.other_dietary_preferences] if user.other_dietary_preferences else []),
                'allergies': user.allergies,
                'cultural_preferences': user.cultural_preferences,
                'pregnancy_conditions': user.get_pregnancy_conditions_list() + ([user.other_conditions] if user.other_conditions else []),
            }
            
            # Generate a new meal plan
            logger.info("Generating new meal plan via Sonar API...")
            max_retries = 3
            retry_delay = 2  # seconds
            meal_plan_data = None
            
            for attempt in range(max_retries):
                try:
                    meal_plan_data = self.sonar.generate_meal_plan(user_profile)
                    
                    # Validate the meal plan data
                    if not meal_plan_data or not isinstance(meal_plan_data, dict):
                        logger.error("Invalid meal plan data returned from Sonar")
                        raise Exception("Invalid meal plan data")
                    
                    if 'error' in meal_plan_data:
                        logger.error(f"Sonar API returned error: {meal_plan_data['error']}")
                        raise Exception(f"Sonar API error: {meal_plan_data['error']}")
                    
                    # Check if we have valid days data
                    days_data = meal_plan_data.get('days', [])
                    if not days_data or len(days_data) == 0:
                        logger.error("Meal plan data contains no days")
                        raise Exception("No days in meal plan")
                    
                    # Additional validation for days structure
                    valid_days = []
                    for i, day_data in enumerate(days_data):
                        if not isinstance(day_data, dict):
                            logger.warning(f"Day {i+1} is not a valid dictionary, skipping")
                            continue
                        
                        if 'day' not in day_data or 'meals' not in day_data:
                            logger.warning(f"Day {i+1} missing required keys, skipping")
                            continue
                        
                        meals = day_data.get('meals', {})
                        if not isinstance(meals, dict) or len(meals) == 0:
                            logger.warning(f"Day {i+1} has no valid meals, skipping")
                            continue
                        
                        valid_days.append(day_data)
                    
                    if len(valid_days) == 0:
                        logger.error("No valid days found in meal plan data")
                        raise Exception("No valid days in meal plan")
                    
                    # Update the meal plan data with only valid days
                    meal_plan_data['days'] = valid_days
                    
                    logger.info(f"Valid meal plan generated with {len(valid_days)} days")
                    break  # Exit retry loop on success
                    
                except Exception as sonar_error:
                    if attempt < max_retries - 1:
                        logger.warning(f"Sonar API attempt {attempt + 1} failed: {str(sonar_error)}, retrying after {retry_delay} seconds...")
                        time.sleep(retry_delay)
                        continue
                    else:
                        logger.error(f"Sonar API call failed after {max_retries} attempts: {str(sonar_error)}")
                        import traceback
                        logger.error(f"Sonar API traceback: {traceback.format_exc()}")
                        # Send error message to user if not scheduled
                        if not is_scheduled:
                            error_message = "Sorry, I couldn't generate your meal plan right now. Please try again later."
                            try:
                                from .whatsapp import WhatsAppHandler
                                whatsapp_handler = WhatsAppHandler()
                                whatsapp_handler.send_message(user.phone_number, error_message)
                            except Exception as error_send_error:
                                logger.warning(f"Failed to send error message: {str(error_send_error)}")
                        return "Sorry, I couldn't generate your meal plan right now. Please try again later."
            
            # If we get here without meal_plan_data, something went wrong
            if not meal_plan_data:
                error_msg = "Failed to generate meal plan after all retries"
                logger.error(error_msg)
                if not is_scheduled:
                    try:
                        from .whatsapp import WhatsAppHandler
                        whatsapp_handler = WhatsAppHandler()
                        whatsapp_handler.send_message(user.phone_number, "Sorry, I couldn't generate your meal plan right now. Please try again later.")
                    except Exception as error_send_error:
                        logger.warning(f"Failed to send error message: {str(error_send_error)}")
                return "Sorry, I couldn't generate your meal plan right now. Please try again later."
            
            # Save the new meal plan to database, overwriting any existing one
            try:
                # Delete any existing meal plan for this user and week to avoid duplicate key error
                MealPlan.objects.filter(user=user, week_number=week_number).delete()
                new_plan = MealPlan.objects.create(
                    user=user,
                    week_number=week_number,
                    meal_plan_data=meal_plan_data
                )
                logger.info(f"New meal plan saved to database with ID: {new_plan.id}")
            except Exception as db_error:
                logger.error(f"Failed to save meal plan to database: {str(db_error)}")
                # Continue anyway, we still have the meal_plan_data to show the user
            
            # Update user state
            user.conversation_state = "AWAITING_MEAL_PLAN_DAY"
            user.save()
            
            # Extract day names from valid days
            valid_days = meal_plan_data.get('days', [])
            days = []
            for day_data in valid_days:
                day_name = day_data.get('day', f'Day {len(days)+1}')
                days.append(day_name)
            
            days_text = " | ".join(days)
            
            # Build response
            prefix = "Here's your scheduled " if is_scheduled else "Here's your "
            response = (
                f"{prefix}Week {week_number} Meal Plan 🍽️ (type a day to view details):\n\n"
                f"🗓️ {days_text}"
            )
            
            # Send the meal plan to user if not scheduled (for scheduled, it's handled elsewhere)
            if not is_scheduled:
                try:
                    from .whatsapp import WhatsAppHandler
                    whatsapp_handler = WhatsAppHandler()
                    whatsapp_handler.send_message(user.phone_number, response)
                    logger.info(f"Sent meal plan to user {user.id}")
                except Exception as send_error:
                    logger.warning(f"Failed to send meal plan message: {str(send_error)}")
            
            logger.info(f"Meal plan response generated successfully with {len(days)} days")
            return response
            
        except Exception as e:
            logger.error(f"Unexpected error in meal plan generation: {str(e)}")
            import traceback
            logger.error(f"Unexpected error traceback: {traceback.format_exc()}")
            
            # Send error message to user if not scheduled
            if not is_scheduled:
                error_message = "Sorry, I couldn't generate your meal plan right now. Please try again later."
                try:
                    from .whatsapp import WhatsAppHandler
                    whatsapp_handler = WhatsAppHandler()
                    whatsapp_handler.send_message(user.phone_number, error_message)
                except Exception as error_send_error:
                    logger.warning(f"Failed to send error message: {str(error_send_error)}")
            
            return "Sorry, I couldn't generate your meal plan right now. Please try again later."

    def _handle_meal_plan_day_selection(self, user, message):
        """Handle day selection for a meal plan"""
        meal_plan = MealPlan.objects.filter(user=user).order_by('-created_at').first()
        if not meal_plan:
            return "I don't have a meal plan generated for you yet. Type 'Generate meal plan' to create one."
        
        day_name = message.strip().capitalize()
        meal_plan_data = meal_plan.meal_plan_data
        
        # Extract days data from the new structure
        days_data = meal_plan_data.get('days', [])
        
        if not days_data:
            logger.error("No days data found in meal plan")
            return "Sorry, there was an issue with your meal plan. Please generate a new one."
        
        selected_day_data = None
        
        # Find the matching day by name
        for day_data in days_data:
            if day_data.get('day', '').lower() == day_name.lower():
                selected_day_data = day_data
                break
        
        # If exact match not found, try partial matching
        if not selected_day_data:
            for day_data in days_data:
                day_name_in_data = day_data.get('day', '').lower()
                if day_name.lower() in day_name_in_data or day_name_in_data.startswith(day_name.lower()[:3]):
                    selected_day_data = day_data
                    break
        
        if not selected_day_data:
            # List available days for user
            available_days = [day_data.get('day', f'Day {i+1}') for i, day_data in enumerate(days_data)]
            days_list = " | ".join(available_days)
            return f"I couldn't find '{day_name}' in your meal plan. Available days:\n🗓️ {days_list}\n\nPlease type one of these day names."
        
        # Get the actual day name for display
        display_day_name = selected_day_data.get('day', day_name.capitalize())
        
        # Extract meals from the selected day data
        meals_data = selected_day_data.get('meals', {})
        
        if not meals_data:
            logger.error(f"No meals data found for day: {display_day_name}")
            return f"Sorry, no meal data found for {display_day_name}. Please try generating a new meal plan."
        
        # Map meal types with consistent capitalization
        meal_type_mapping = {
            'breakfast': 'Breakfast',
            'lunch': 'Lunch', 
            'dinner': 'Dinner',
            'snack 1': 'Snack 1',
            'snack 2': 'Snack 2'
        }
        
        meals = {}
        
        # Extract meals based on the new data structure
        for meal_key, meal_data in meals_data.items():
            # Normalize the meal key for mapping
            normalized_key = meal_key.lower().strip()
            mapped_key = meal_type_mapping.get(normalized_key, meal_key.title())
            meals[mapped_key] = meal_data
        
        meal_emojis = {
            "Breakfast": "🥣",
            "Lunch": "🍛", 
            "Snack 1": "🍎",
            "Snack 2": "🍵",
            "Dinner": "🍲"
        }
        
        message_parts = [f"🗓️ {display_day_name}"]
        
        # Define meal order for consistent display
        meal_order = ["Breakfast", "Snack 1", "Lunch", "Snack 2", "Dinner"]
        
        # Build meals section with proper ordering
        for meal_type in meal_order:
            if meal_type in meals:
                details = meals[meal_type]
                emoji = meal_emojis.get(meal_type, "🍽️")
                name = details.get('name', 'Not specified')
                description = details.get('description', '')
                nutritional_benefits = details.get('nutritional_benefits', '')
                
                meal_text = f"{emoji} {meal_type}: {name}"
                if description:
                    # Truncate description if too long
                    if len(description) > 80:
                        description = description[:77] + "..."
                    meal_text += f"\n   {description}"
                
                # Add nutritional benefits if available and space permits
                if nutritional_benefits and len(nutritional_benefits) < 60:
                    meal_text += f"\n   ✨ {nutritional_benefits}"
                    
                message_parts.append(meal_text)
        
        # Add any remaining meals not in the standard order
        for meal_type, details in meals.items():
            if meal_type not in meal_order:
                emoji = meal_emojis.get(meal_type, "🍽️")
                name = details.get('name', 'Not specified')
                description = details.get('description', '')
                
                meal_text = f"{emoji} {meal_type}: {name}"
                if description:
                    if len(description) > 80:
                        description = description[:77] + "..."
                    meal_text += f"\n   {description}"
                    
                message_parts.append(meal_text)
        
        # Generate tip using user profile
        user_profile = {
            'trimester': user.trimester,
            'dietary_preferences': user.get_dietary_preferences_list() + ([user.other_dietary_preferences] if user.other_dietary_preferences else []),
            'allergies': user.allergies,
            'cultural_preferences': user.cultural_preferences,
            'pregnancy_conditions': user.get_pregnancy_conditions_list() + ([user.other_conditions] if user.other_conditions else []),
        }
        
        try:
            # Generate tip and clean it
            tip_response = self.sonar.generate_meal_plan_tip(user_profile, selected_day_data)
            tip_content = self._clean_tip_content(tip_response.get('content', 'Stay hydrated and eat regularly for optimal nutrient absorption.'))
        except Exception as e:
            logger.warning(f"Failed to generate tip: {str(e)}")
            tip_content = "Stay hydrated and eat regularly for optimal nutrient absorption."
        
        message_parts.append(f"🧠 Tip: {tip_content}")
        
        user.conversation_state = "AWAITING_SHARE_CONFIRMATION"
        user.save()
        
        # Join message and check length
        base_message = "\n\n".join(message_parts)
        footer = "\n\n📤 Want to share this plan with your partner or midwife? Reply 'Yes' or 'No'."
        full_message = base_message + footer
        
        # If message is too long, truncate descriptions further
        if len(full_message) > 1500:  # Leave buffer for WhatsApp
            logger.info(f"Message too long ({len(full_message)} chars), truncating...")
            # Rebuild with shorter descriptions
            message_parts = [f"🗓️ {display_day_name}"]
            
            for meal_type in meal_order:
                if meal_type in meals:
                    details = meals[meal_type]
                    emoji = meal_emojis.get(meal_type, "🍽️")
                    name = details.get('name', 'Not specified')
                    
                    # Just show meal name without description for brevity
                    meal_text = f"{emoji} {meal_type}: {name}"
                    message_parts.append(meal_text)
            
            message_parts.append(f"🧠 Tip: {tip_content}")
            full_message = "\n\n".join(message_parts) + footer
            logger.info(f"Truncated message length: {len(full_message)} chars")
        
        return full_message

    def _clean_tip_content(self, tip_content):
        """Clean tip content to remove any XML tags or debug info"""
        import re
        
        if not tip_content:
            return "Stay hydrated and eat regularly for optimal nutrient absorption."
        
        # Remove any XML-like tags (including <think> tags)
        tip_content = re.sub(r'<[^>]+>', '', tip_content)
        
        # Remove any leading/trailing whitespace
        tip_content = tip_content.strip()
        
        # If tip is too long, truncate to reasonable length
        if len(tip_content) > 150:
            # Find the first sentence
            sentences = tip_content.split('.')
            if sentences and len(sentences[0]) < 150:
                tip_content = sentences[0] + '.'
            else:
                tip_content = tip_content[:147] + "..."
        
        # If tip doesn't end with proper punctuation, add it
        if tip_content and not tip_content.endswith(('.', '!', '?')):
            tip_content += '.'
        
        return tip_content 
    

    def _format_meal_plan_for_sharing(self, meal_plan, day_name=None):
        """Format a meal plan or specific day for sharing"""
        meal_plan_data = meal_plan.meal_plan_data
        if day_name:
            selected_day = next((day for day in meal_plan_data.get('days', []) if day.get('day', '').lower() == day_name.lower()), None)
            if not selected_day:
                return "Day not found."
            
            meals = selected_day.get('meals', {})
            message_parts = [f"MamáMind Meal Plan - Week {meal_plan.week_number}, {selected_day.get('day', 'Today')}"]
            for meal_type, details in meals.items():
                name = details.get('name', 'Not specified')
                description = details.get('description', '')
                meal_text = f"{meal_type}: {name}"
                if description:
                    meal_text += f" ({description})"
                message_parts.append(meal_text)
            if 'tip' in selected_day:
                message_parts.append(f"Tip: {selected_day['tip']}")
            return "\n".join(message_parts)
        else:
            message_parts = [f"MamáMind Meal Plan - Week {meal_plan.week_number}"]
            for day in meal_plan_data.get('days', []):
                day_name = day.get('day', 'Day')
                message_parts.append(f"\n{day_name}:")
                for meal_type, details in day.get('meals', {}).items():
                    name = details.get('name', 'Not specified')
                    message_parts.append(f"  {meal_type}: {name}")
            return "\n".join(message_parts)

    def _generate_pdf_meal_plan(self, meal_plan, day_name=None):
        """Generate a PDF version of the meal plan"""
        buffer = BytesIO()
        doc = SimpleDocTemplate(buffer, pagesize=letter)
        styles = getSampleStyleSheet()
        story = []
        
        meal_plan_text = self._format_meal_plan_for_sharing(meal_plan, day_name)
        story.append(Paragraph(meal_plan_text.replace('\n', '<br/>'), styles['Normal']))
        
        doc.build(story)
        pdf_data = buffer.getvalue()
        buffer.close()
        return pdf_data

    def _handle_share_confirmation(self, user, message):
        """Handle confirmation for sharing the meal plan"""
        if message.lower() == "yes":
            meal_plan = MealPlan.objects.filter(user=user).order_by('-created_at').first()
            if not meal_plan:
                return "No meal plan found to share."
            
            # Generate text summary for the latest day's plan
            day_name = meal_plan.meal_plan_data.get('days', [])[-1].get('day')
            text_summary = self._format_meal_plan_for_sharing(meal_plan, day_name=day_name)
            
            # Send text summary
            self.whatsapp.send_message(user.phone_number, text_summary)
            
            # Generate PDF but inform user it's not directly sendable
            pdf_data = self._generate_pdf_meal_plan(meal_plan, day_name=day_name)
            pdf_message = (
                f"Your meal plan PDF for {day_name} is ready! "
                "PDF sharing via WhatsApp is coming soon. "
                "Please contact support to receive it via email."
            )
            self.whatsapp.send_pdf(user.phone_number, pdf_data, f"meal_plan_week_{meal_plan.week_number}.pdf")
            
            user.conversation_state = "COMPLETED_ONBOARDING"
            user.save()
            return "Plan shared as text! Check the message above for PDF details."
        else:
            user.conversation_state = "COMPLETED_ONBOARDING"
            user.save()
            return "Okay, let's continue. Type a day or ask a question."

    def _handle_nutrition_question(self, user, message):
        """Handle nutrition questions"""
        conversation = Conversation(
            user=user,
            message=message,
            response=""
        )
        
        user_profile = {
            'trimester': user.trimester,
            'dietary_preferences': user.get_dietary_preferences_list() + ([user.other_dietary_preferences] if user.other_dietary_preferences else []),
            'allergies': user.allergies,
            'cultural_preferences': user.cultural_preferences,
            'pregnancy_conditions': user.get_pregnancy_conditions_list() + ([user.other_conditions] if user.other_conditions else []),
        }
        
        try:
            response = self.sonar.get_nutrition_answer(message, user_profile)
            
            # Double-check character limit before saving/sending
            if len(response) > 1600:
                # Emergency truncation if somehow still too long
                response = response[:1550] + "..."
                
            conversation.response = response
            conversation.save()
            
            logger.info(f"Nutrition response length: {len(response)} characters")
            return response
            
        except Exception as e:
            logger.error(f"Error handling nutrition question: {str(e)}")
            fallback_response = "⚠️ I'm having trouble right now. For pregnancy nutrition questions, please consult your healthcare provider."
            conversation.response = fallback_response
            conversation.save()
            return fallback_response

    def send_daily_tip(self, user):
        """
        Send a daily nutrition tip to the user
        Args:
            user (User): The user to send the tip to
        Returns:
            dict: The response from the WhatsApp handler
        """
        # Should be triggered by a Celery task at 8:00 AM in user's time zone
        if not user.wants_nutrition_tips:
            return None
        
        user_profile = {
            'trimester': user.trimester,
            'dietary_preferences': user.get_dietary_preferences_list() + ([user.other_dietary_preferences] if user.other_dietary_preferences else []),
            'allergies': user.allergies,
            'cultural_preferences': user.cultural_preferences,
            'pregnancy_conditions': user.get_pregnancy_conditions_list() + ([user.other_conditions] if user.other_conditions else []),
        }
        
        tip = self.sonar.generate_daily_tip(user_profile)
        
        nutrition_tip = NutritionTip.objects.create(
            title=tip.get('title', 'Daily Nutrition Tip'),
            content=tip.get('content', ''),
            source=tip.get('source', ''),
            trimester=user.trimester
        )
        
        message = f"🌿 Tip of the Day: {tip.get('content', '')}\n\n👩‍⚕️ Source: {tip.get('source', 'General recommendation')}"
        return self.whatsapp.send_message(user.phone_number, message)

    def send_nudge(self, user):
        """
        Send a behavioral nudge to the user
        Args:
            user (User): The user to send the nudge to
        Returns:
            dict: The response from the WhatsApp handler
        """
        # Should be triggered by a Celery task at 10:00 AM in user's time zone
        if not user.wants_nutrition_tips:
            return None
        
        user_profile = {
            'trimester': user.trimester,
            'dietary_preferences': user.get_dietary_preferences_list() + ([user.other_dietary_preferences] if user.other_dietary_preferences else []),
            'allergies': user.allergies,
            'cultural_preferences': user.cultural_preferences,
            'pregnancy_conditions': user.get_pregnancy_conditions_list() + ([user.other_conditions] if user.other_conditions else []),
        }
        
        nudge = self.sonar.generate_nudge(user_profile)
        message = f"⏰ {nudge.get('content', 'Don’t forget your iron-rich meal today!')}"
        return self.whatsapp.send_message(user.phone_number, message)

    def send_scheduled_meal_plan(self, user):
        """
        Send a scheduled weekly meal plan to the user
        Args:
            user (User): The user to send the meal plan to
        Returns:
            dict: The response from the WhatsApp handler
        """
        # Should be triggered by a Celery task weekly (e.g., every Monday)
        if not user.wants_meal_plans:
            return None
        
        message = self._generate_meal_plan(user, is_scheduled=True)
        return self.whatsapp.send_message(user.phone_number, message)