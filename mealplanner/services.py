import json
import random
from datetime import datetime, timedelta
from django.utils import timezone

from chatbot.models import User, PregnancyCondition
from chatbot.utils.sonar import SonarAPI
from .models import Recipe

class MealPlannerService:
    """Service for generating meal plans and nutrition tips"""
    
    def __init__(self):
        self.sonar = SonarAPI()
    
    def generate_meal_plan(self, user):
        """
        Generate a weekly meal plan for a user
        
        Args:
            user (User): The user to generate a meal plan for
            
        Returns:
            dict: The generated meal plan
        """
        # Prepare user profile for meal plan generation
        user_profile = {
            'trimester': user.trimester,
            'dietary_preferences': user.get_dietary_preferences_list(),
            'allergies': user.allergies,
            'cultural_preferences': user.cultural_preferences,
            'pregnancy_conditions': user.get_pregnancy_conditions_list(),
        }
        
        # Generate meal plan using Perplexity Sonar API
        return self.sonar.generate_meal_plan(user_profile)
    
    def prepare_meal_plan_summary(self, meal_plan):
        """
        Prepare a summary of the meal plan
        
        Args:
            meal_plan (dict): The meal plan data
            
        Returns:
            str: A text summary of the meal plan
        """
        days = [day.get('day', 'Day') for day in meal_plan.get('days', [])]
        days_text = " | ".join(days)
        
        week_number = meal_plan.get('week_number', 'your')
        
        return f"Here's {week_number} Meal Plan 🍽️ (type a day to view details):\n\n🗓️ {days_text}"
    
    def get_day_meal_plan(self, meal_plan, day_name):
        """
        Get the meal plan for a specific day
        
        Args:
            meal_plan (dict): The meal plan data
            day_name (str): The name of the day
            
        Returns:
            dict: The day's meal plan data or None if not found
        """
        for day in meal_plan.get('days', []):
            if day.get('day', '').lower() == day_name.lower():
                return day
        return None
    
    def format_day_meal_plan(self, day_data):
        """
        Format a day's meal plan for display
        
        Args:
            day_data (dict): The day's meal plan data
            
        Returns:
            str: Formatted text for display
        """
        day_name = day_data.get('day', 'Today')
        meals = day_data.get('meals', {})
        
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
        tip = day_data.get('tip', "Remember to stay hydrated throughout the day.")
        message_parts.append(f"🧠 Tip: {tip}")
        
        return "\n\n".join(message_parts)
    
    def get_recommended_recipes(self, user, condition=None, meal_type=None, limit=5):
        """
        Get recommended recipes for a user based on their profile
        
        Args:
            user (User): The user to get recommendations for
            condition (str, optional): A specific condition to focus on
            meal_type (str, optional): The type of meal (breakfast, lunch, dinner, snack)
            limit (int, optional): Maximum number of recipes to return
            
        Returns:
            list: A list of recommended recipes
        """
        # Get user's dietary preferences
        dietary_prefs = user.get_dietary_preferences_list()
        
        # Start with all recipes
        recipes = Recipe.objects.all()
        
        # Filter by dietary preferences
        if "Vegetarian" in dietary_prefs:
            recipes = recipes.filter(is_vegetarian=True)
        if "Vegan" in dietary_prefs:
            recipes = recipes.filter(is_vegan=True)
        if "Gluten-free" in dietary_prefs:
            recipes = recipes.filter(is_gluten_free=True)
        if "Dairy-free" in dietary_prefs:
            recipes = recipes.filter(is_dairy_free=True)
        
        # Filter by trimester
        if user.trimester:
            recipes = recipes.filter(suitable_trimesters__contains=str(user.trimester))
        
        # Filter by condition
        condition_filters = {}
        if condition:
            condition_field = f"good_for_{condition.lower().replace(' ', '_')}"
            condition_filters[condition_field] = True
        else:
            # Check user's conditions
            conditions = user.get_pregnancy_conditions_list()
            for condition in conditions:
                condition_field = f"good_for_{condition.lower().replace(' ', '_')}"
                if hasattr(Recipe, condition_field):
                    condition_filters[condition_field] = True
        
        if condition_filters:
            recipes = recipes.filter(**condition_filters)
        
        # Filter by meal type
        if meal_type:
            recipes = recipes.filter(meal_type=meal_type)
        
        # If we have allergies, filter those out
        if user.allergies:
            allergens = [a.strip().lower() for a in user.allergies.split(',')]
            for allergen in allergens:
                recipes = recipes.exclude(contains_allergens__contains=allergen)
        
        # If there's a cultural preference, prioritize those recipes
        if user.cultural_preferences:
            cultural_recipes = recipes.filter(cuisine__icontains=user.cultural_preferences)
            if cultural_recipes.exists():
                # If we have enough cultural recipes, use only those
                if cultural_recipes.count() >= limit:
                    recipes = cultural_recipes
                # Otherwise, prioritize cultural recipes in the mix
                else:
                    cultural_limit = min(cultural_recipes.count(), limit // 2)
                    other_limit = limit - cultural_limit
                    return list(cultural_recipes[:cultural_limit]) + list(recipes.exclude(id__in=cultural_recipes.values_list('id', flat=True))[:other_limit])
        
        # Return a limited number of recipes
        return list(recipes[:limit])
    
    def generate_daily_tip(self, user):
        """
        Generate a daily nutrition tip for a user
        
        Args:
            user (User): The user to generate a tip for
            
        Returns:
            dict: The generated tip
        """
        # Prepare user profile
        user_profile = {
            'trimester': user.trimester,
            'dietary_preferences': user.get_dietary_preferences_list(),
            'allergies': user.allergies,
            'cultural_preferences': user.cultural_preferences,
            'pregnancy_conditions': user.get_pregnancy_conditions_list(),
        }
        
        # Generate tip using Perplexity Sonar API
        return self.sonar.generate_daily_tip(user_profile)
