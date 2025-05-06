# chatbot/bot_logic.py
import json
import random
from datetime import datetime, timedelta
from django.utils import timezone

from .models import User, DietaryPreference, PregnancyCondition, Conversation, MealPlan, NutritionTip
from .utils.sonar import SonarAPI
from .whatsapp import WhatsAppHandler

class BotLogic:
    """Core logic for the chatbot"""
    
    def __init__(self):
        self.sonar = SonarAPI()
        self.whatsapp = WhatsAppHandler()
        
        # Initialize common data structures
        self.TRIMESTERS = [1, 2, 3]
        self.DIETARY_PREFERENCES = ["Vegetarian", "Vegan", "Gluten-free", "Dairy-free", "No restrictions", "Other"]
        self.PREGNANCY_CONDITIONS = ["Anemia or low iron", "Gestational diabetes", "Hypertension", "Morning sickness", "None", "Other"]
        self.USAGE_PREFERENCES = ["Weekly meal plans", "Daily nutrition tips", "Recipe suggestions", "Nutrition Q&A", "All of the above"]
        
        # Create necessary database objects
        self._ensure_preferences_exist()
    
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
            return "Thank you for using MamáMind! Your preferences have been saved. Type 'Start' anytime to chat again."
        
        if message_body.lower() == "start over":
            user.reset_preferences()
            user.conversation_state = "ONBOARDING_START"
            user.save()
            return self._handle_onboarding_start(user)
        
        if message_body.lower() == "update preferences":
            user.conversation_state = "ONBOARDING_START"
            user.save()
            return "Let's update your preferences. " + self._handle_onboarding_start(user)
        
        if message_body.lower() == "generate meal plan":
            return self._generate_meal_plan(user)
        
        # Handle user state
        if user.conversation_state == "ONBOARDING_START":
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
        
        # Default to Q&A mode if onboarding is complete
        else:
            return self._handle_nutrition_question(user, message_body)
    
    def _handle_onboarding_start(self, user):
        """Handle the start of onboarding"""
        user.conversation_state = "AWAITING_TRIMESTER"
        user.save()
        
        return (
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
            # Allow for multiple selections separated by commas
            selections = [int(x.strip()) for x in message.split(',')]
            
            # Validate selections
            if any(s < 1 or s > len(self.DIETARY_PREFERENCES) for s in selections):
                return f"Please enter valid numbers between 1 and {len(self.DIETARY_PREFERENCES)}."
            
            # Clear existing preferences
            user.dietary_preferences.clear()
            
            # Add new preferences
            for selection in selections:
                pref_name = self.DIETARY_PREFERENCES[selection - 1]
                pref = DietaryPreference.objects.get(name=pref_name)
                user.dietary_preferences.add(pref)
            
            user.conversation_state = "AWAITING_ALLERGIES"
            user.save()
            
            # Get the names of selected preferences for confirmation
            selected_prefs = [self.DIETARY_PREFERENCES[s - 1] for s in selections]
            
            return (
                f"Got it – {', '.join(selected_prefs)}!\n\n"
                "Any food allergies or intolerances I should know about? "
                "Please list them, or type NONE."
            )
            
        except ValueError:
            return "Please enter valid numbers for your dietary preferences."
    
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
            # Allow for multiple selections separated by commas
            selections = [int(x.strip()) for x in message.split(',')]
            
            # Validate selections
            if any(s < 1 or s > len(self.PREGNANCY_CONDITIONS) for s in selections):
                return f"Please enter valid numbers between 1 and {len(self.PREGNANCY_CONDITIONS)}."
            
            # Clear existing conditions
            user.pregnancy_conditions.clear()
            
            # Add new conditions
            for selection in selections:
                cond_name = self.PREGNANCY_CONDITIONS[selection - 1]
                if cond_name != "None":  # Skip 'None' option
                    cond = PregnancyCondition.objects.get(name=cond_name)
                    user.pregnancy_conditions.add(cond)
            
            user.conversation_state = "AWAITING_USAGE_PREFERENCES"
            user.save()
            
            # Get the names of selected conditions for confirmation
            selected_conds = [self.PREGNANCY_CONDITIONS[s - 1] for s in selections]
            confirmation = f"I'll focus on options to support {', '.join(selected_conds)}." if "None" not in selected_conds else "No specific conditions noted."
            
            options = "\n".join([f"{i+1}. {pref}" for i, pref in enumerate(self.USAGE_PREFERENCES)])
            
            return (
                f"Thanks – {confirmation}\n\n"
                "How would you like to use MamáMind? Choose your preferences:\n\n"
                f"{options}"
            )
            
        except ValueError:
            return "Please enter valid numbers for your pregnancy conditions."
    
    def _handle_usage_preferences_response(self, user, message):
        """Handle the usage preferences response"""
        try:
            # Handle 'All of the above' option
            if message.strip() == "5":
                user.wants_meal_plans = True
                user.wants_nutrition_tips = True
                user.wants_recipe_suggestions = True
                user.wants_nutrition_qa = True
            else:
                # Allow for multiple selections separated by commas
                selections = [int(x.strip()) for x in message.split(',')]
                
                # Validate selections
                if any(s < 1 or s > len(self.USAGE_PREFERENCES) for s in selections):
                    return f"Please enter valid numbers between 1 and {len(self.USAGE_PREFERENCES)}."
                
                # Set user preferences
                user.wants_meal_plans = 1 in selections
                user.wants_nutrition_tips = 2 in selections
                user.wants_recipe_suggestions = 3 in selections
                user.wants_nutrition_qa = 4 in selections
            
            user.conversation_state = "COMPLETED_ONBOARDING"
            user.save()
            
            # Prepare the profile summary
            trimester_text = f"Trimester {user.trimester}"
            diet_text = ", ".join(user.get_dietary_preferences_list())
            allergies_text = user.allergies if user.allergies else "No allergies"
            cuisine_text = user.cultural_preferences
            conditions_text = ", ".join(user.get_pregnancy_conditions_list()) if user.get_pregnancy_conditions_list() else "No specific conditions"
            
            profile_summary = (
                f"✅ {trimester_text}\n"
                f"✅ {diet_text}\n"
                f"✅ {allergies_text}\n"
                f"✅ {cuisine_text} cuisine preference\n"
                f"✅ {conditions_text}"
            )
            
            # If user wants meal plans, generate one now
            if user.wants_meal_plans:
                return (
                    f"Perfect! Your profile is set up. Based on your information:\n\n"
                    f"{profile_summary}\n\n"
                    "Let me generate your first meal plan. Type 'Generate meal plan' anytime to get a new one."
                )
            else:
                return (
                    f"Perfect! Your profile is set up. Based on your information:\n\n"
                    f"{profile_summary}\n\n"
                    "You can ask me nutrition questions anytime. Just type your question!"
                )
            
        except ValueError:
            return "Please enter valid numbers for your usage preferences."
    
    def _generate_meal_plan(self, user):
        """Generate a meal plan for the user"""
        # Calculate week number of pregnancy (approximate)
        if user.trimester == 1:
            week_number = random.randint(1, 12)
        elif user.trimester == 2:
            week_number = random.randint(13, 26)
        else:
            week_number = random.randint(27, 40)
        
        # Check if we already have a meal plan for this week
        existing_plan = MealPlan.objects.filter(user=user, week_number=week_number).first()
        if existing_plan:
            meal_plan_data = existing_plan.meal_plan_data
        else:
            # Prepare user profile for meal plan generation
            user_profile = {
                'trimester': user.trimester,
                'dietary_preferences': user.get_dietary_preferences_list(),
                'allergies': user.allergies,
                'cultural_preferences': user.cultural_preferences,
                'pregnancy_conditions': user.get_pregnancy_conditions_list(),
            }
            
            # Generate meal plan
            meal_plan_data = self.sonar.generate_meal_plan(user_profile)
            
            # Save the meal plan
            MealPlan.objects.create(
                user=user,
                week_number=week_number,
                meal_plan_data=meal_plan_data
            )
        
        # Update user state
        user.conversation_state = "AWAITING_MEAL_PLAN_DAY"
        user.save()
        
        # Return the meal plan summary
        days = [day.get('day', 'Day') for day in meal_plan_data.get('days', [])]
        days_text = " | ".join(days)
        
        return (
            f"Here's your Week {week_number} Meal Plan 🍽️ (type a day to view details):\n\n"
            f"🗓️ {days_text}"
        )
    
    def _handle_meal_plan_day_selection(self, user, message):
        """Handle day selection for a meal plan"""
        # Get the most recent meal plan
        meal_plan = MealPlan.objects.filter(user=user).order_by('-created_at').first()
        if not meal_plan:
            return "I don't have a meal plan generated for you yet. Type 'Generate meal plan' to create one."
        
        # Find the day that matches the message
        day_name = message.strip().capitalize()
        meal_plan_data = meal_plan.meal_plan_data
        
        selected_day = None
        for day in meal_plan_data.get('days', []):
            if day.get('day', '').lower() == day_name.lower():
                selected_day = day
                break
        
        if not selected_day:
            # If it's not a day name, return to Q&A mode
            user.conversation_state = "COMPLETED_ONBOARDING"
            user.save()
            return self._handle_nutrition_question(user, message)
        
        # Format the day's meal plan
        day_name = selected_day.get('day', 'Today')
        meals = selected_day.get('meals', {})
        
        meal_emojis = {
            "Breakfast": "🥣",
            "Lunch": "🍛",
            "Snack 1": "🍎",
            "Snack 2": "🍵",
            "Dinner": "🍲"
        }
        
        message_parts = [f"🗓️ {day_name}"]
        
        for meal_type, details in meals.items():
            emoji = meal_emojis.get(meal_type, "🍽️")
            name = details.get('name', 'Not specified')
            description = details.get('description', '')
            
            meal_text = f"{emoji} {meal_type}: {name}"
            if description:
                meal_text += f"\n   {description}"
                
            message_parts.append(meal_text)
        
        # Add a nutrition tip
        tip = "Remember to stay hydrated throughout the day for optimal nutrient absorption."
        message_parts.append(f"🧠 Tip: {tip}")
        
        return "\n\n".join(message_parts)
    
    def _handle_nutrition_question(self, user, message):
        """Handle nutrition questions"""
        # Save the conversation
        conversation = Conversation(
            user=user,
            message=message,
            response=""  # We'll update this later
        )
        
        # Prepare user profile for the AI
        user_profile = {
            'trimester': user.trimester,
            'dietary_preferences': user.get_dietary_preferences_list(),
            'allergies': user.allergies,
            'cultural_preferences': user.cultural_preferences,
            'pregnancy_conditions': user.get_pregnancy_conditions_list(),
        }
        
        # Get the answer from the AI
        response = self.sonar.get_nutrition_answer(message, user_profile)
        
        # Update and save the conversation
        conversation.response = response
        conversation.save()
        
        return response
    
    def send_daily_tip(self, user):
        """
        Send a daily nutrition tip to the user
        
        Args:
            user (User): The user to send the tip to
            
        Returns:
            dict: The response from the WhatsApp handler
        """
        # Check if the user wants nutrition tips
        if not user.wants_nutrition_tips:
            return None
        
        # Prepare user profile for the AI
        user_profile = {
            'trimester': user.trimester,
            'dietary_preferences': user.get_dietary_preferences_list(),
            'allergies': user.allergies,
            'cultural_preferences': user.cultural_preferences,
            'pregnancy_conditions': user.get_pregnancy_conditions_list(),
        }
        
        # Generate a tip
        tip = self.sonar.generate_daily_tip(user_profile)
        
        # Save the tip
        nutrition_tip = NutritionTip.objects.create(
            title=tip.get('title', 'Daily Nutrition Tip'),
            content=tip.get('content', ''),
            source=tip.get('source', ''),
            trimester=user.trimester
        )
        
        # Send the tip via WhatsApp
        return self.whatsapp.send_daily_tip(user.phone_number, tip)