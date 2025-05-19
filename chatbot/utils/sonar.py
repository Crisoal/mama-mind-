# chatbot/utils/sonar.py
import os
import json
import requests
from django.conf import settings

class SonarAPI:
    """Wrapper for the Perplexity Sonar API"""
    
    BASE_URL = "https://api.perplexity.ai/chat/completions"
    
    def __init__(self):
        self.api_key = settings.PERPLEXITY_API_KEY
        if not self.api_key:
            raise ValueError("Perplexity API key not found in environment variables")
    
    def _get_headers(self):
        """Get headers for API requests"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
    
    def query(self, prompt, model="sonar-reasoning-pro", context=None, stream=False, follow_up=False):
        """
        Make a query to the Sonar API
        
        Args:
            prompt (str): The prompt to send to the API
            model (str): The model to use (sonar-reasoning-pro, sonar-reasoning, sonar-deep-research)
            context (dict, optional): Context information for the conversation
            stream (bool, optional): Whether to stream the response
            follow_up (bool, optional): Whether this is a follow-up question
            
        Returns:
            dict: The API response
        """
        url = f"{self.BASE_URL}/query"
        
        payload = {
            "model": model,
            "prompt": prompt,
            "stream": stream,
        }
        
        if context:
            payload["context"] = context
        
        if follow_up:
            payload["follow_up"] = True
        
        try:
            response = requests.post(url, headers=self._get_headers(), json=payload)
            response.raise_for_status()
            return response.json()
        except requests.exceptions.RequestException as e:
            print(f"Error making API request: {e}")
            return {"error": str(e)}
    
    def generate_meal_plan(self, user_profile):
        """
        Generate a meal plan based on user profile
        
        Args:
            user_profile (dict): User preferences and health information
            
        Returns:
            dict: A structured meal plan
        """
        # Create a detailed prompt for the meal plan generation
        trimester = user_profile.get('trimester', 1)
        dietary_prefs = user_profile.get('dietary_preferences', [])
        allergies = user_profile.get('allergies', '')
        cultural_prefs = user_profile.get('cultural_preferences', '')
        conditions = user_profile.get('pregnancy_conditions', [])
        
        prompt = f"""
        Generate a detailed 7-day meal plan for a pregnant woman with the following profile:
        - Trimester: {trimester}
        - Dietary Preferences: {', '.join(dietary_prefs)}
        - Allergies/Intolerances: {allergies}
        - Cultural Food Preferences: {cultural_prefs}
        - Pregnancy Conditions: {', '.join(conditions)}
        
        For each day, include:
        1. Breakfast
        2. Lunch
        3. Two snacks
        4. Dinner
        
        For each meal:
        - Include the name of the dish
        - A brief description or key ingredients
        - Note any nutritional benefits relevant to pregnancy
        - Tailor to the specified dietary needs and cultural preferences
        
        Format the response as a JSON structure that can be easily parsed.
        """
        
        response = self.query(prompt, model="sonar-reasoning-pro")
        
        # Extract the meal plan from the response
        try:
            # Try to parse the content directly as JSON
            if 'content' in response:
                content = response['content']
                # Sometimes the API might return markdown code blocks with JSON
                if '```json' in content:
                    json_str = content.split('```json')[1].split('```')[0].strip()
                    return json.loads(json_str)
                # Or it might return raw JSON
                return json.loads(content)
            else:
                return {"error": "Invalid response format from API"}
        except json.JSONDecodeError:
            # If direct parsing fails, try to extract JSON using regex or other methods
            try:
                import re
                json_match = re.search(r'\{.*\}', response['content'], re.DOTALL)
                if json_match:
                    return json.loads(json_match.group(0))
                else:
                    # If all parsing fails, create a structured format ourselves
                    return self._format_text_response_to_json(response['content'])
            except Exception as e:
                return {"error": f"Failed to parse meal plan: {str(e)}"}
    
    def _format_text_response_to_json(self, text):
        """
        Convert a text response to a structured JSON format
        Used as a fallback when the API doesn't return valid JSON
        """
        days = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
        meal_types = ["Breakfast", "Lunch", "Snack 1", "Snack 2", "Dinner"]
        
        meal_plan = {"days": []}
        
        current_day = None
        current_meals = {}
        
        lines = text.split('\n')
        for line in lines:
            line = line.strip()
            if not line:
                continue
                
            # Check if this is a day header
            day_match = any(day.lower() in line.lower() for day in days)
            if day_match:
                # Save the previous day if it exists
                if current_day and current_meals:
                    meal_plan["days"].append({
                        "day": current_day,
                        "meals": current_meals
                    })
                
                # Start a new day
                for day in days:
                    if day.lower() in line.lower():
                        current_day = day
                        current_meals = {}
                        break
                continue
            
            # Check if this is a meal type
            meal_match = None
            for meal in meal_types:
                if meal.lower() in line.lower() or (meal == "Snack 1" and "snack" in line.lower()):
                    meal_match = meal
                    # Extract content after the meal type
                    content = line.split(":", 1)[1].strip() if ":" in line else ""
                    if not content:
                        # If no content on this line, look at next lines
                        continue
                    
                    current_meals[meal_match] = {
                        "name": content,
                        "description": ""
                    }
                    break
            
            # If not a day or meal type, it's probably a description
            if meal_match is None and current_day and current_meals:
                # Add to the last meal's description
                last_meal = list(current_meals.keys())[-1] if current_meals else None
                if last_meal:
                    if "description" in current_meals[last_meal]:
                        current_meals[last_meal]["description"] += " " + line
                    else:
                        current_meals[last_meal]["description"] = line
        
        # Don't forget to add the last day
        if current_day and current_meals:
            meal_plan["days"].append({
                "day": current_day,
                "meals": current_meals
            })
        
        return meal_plan
    
    def get_nutrition_answer(self, question, user_profile):
        """
        Get an answer to a nutrition question based on user profile
        
        Args:
            question (str): The nutrition question
            user_profile (dict): User preferences and health information
            
        Returns:
            str: The answer to the question
        """
        trimester = user_profile.get('trimester', 1)
        dietary_prefs = user_profile.get('dietary_preferences', [])
        allergies = user_profile.get('allergies', '')
        conditions = user_profile.get('pregnancy_conditions', [])
        
        prompt = f"""
        I need a pregnancy nutrition expert answer for a pregnant woman with the following profile:
        - Trimester: {trimester}
        - Dietary Preferences: {', '.join(dietary_prefs)}
        - Allergies/Intolerances: {allergies}
        - Pregnancy Conditions: {', '.join(conditions)}
        
        Question: {question}
        
        Please provide a concise, evidence-based answer that addresses her specific situation. 
        Include a reputable medical source if available. Keep your answer under 150 words and 
        make it both accurate and reassuring.
        """
        
        response = self.query(prompt, model="sonar-reasoning-pro")
        if 'content' in response:
            return response['content']
        else:
            return "I'm sorry, I couldn't generate an answer at this time. Please try again later."
    
    def generate_daily_tip(self, user_profile):
        """
        Generate a daily nutrition tip based on user profile
        
        Args:
            user_profile (dict): User preferences and health information
            
        Returns:
            dict: A tip with title, content and source
        """
        trimester = user_profile.get('trimester', 1)
        conditions = user_profile.get('pregnancy_conditions', [])
        condition_focus = conditions[0] if conditions else "general pregnancy nutrition"
        
        prompt = f"""
        Generate a practical daily nutrition tip for a pregnant woman in trimester {trimester} 
        with a focus on {condition_focus}. The tip should be actionable, specific, and backed 
        by medical evidence. Include a reputable source for the information.
        
        Format the response as a short title followed by 2-3 sentences of content and the source.
        """
        
        response = self.query(prompt, model="sonar-reasoning")
        
        if 'content' in response:
            content = response['content']
            
            # Try to parse the tip into title, content and source
            lines = content.strip().split('\n')
            
            title = lines[0].strip()
            if ':' in title:
                title = title.split(':', 1)[1].strip()
            
            tip_content = '\n'.join(lines[1:-1]) if len(lines) > 2 else ''
            source = lines[-1] if "source" in lines[-1].lower() else ""
            
            return {
                "title": title,
                "content": tip_content,
                "source": source
            }
        else:
            return {
                "title": "Daily Nutrition Tip",
                "content": "Remember to stay hydrated and eat a variety of nutrient-rich foods.",
                "source": "General pregnancy nutrition guidelines"
            }