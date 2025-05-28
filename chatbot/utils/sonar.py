# chatbot/utils/sonar.py
import os
import json
import requests
from django.conf import settings
import logging
import re
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

# Set up logging with UTF-8 encoding
logger = logging.getLogger(__name__)
logging.basicConfig(
    level=logging.DEBUG,
    format='%(asctime)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('meal_plan_debug.log', encoding='utf-8'),
        logging.StreamHandler()
    ]
)

class SonarAPI:
    """Wrapper for the Perplexity Sonar API"""

    BASE_URL = "https://api.perplexity.ai/chat/completions"

    def __init__(self):
        self.api_key = settings.PERPLEXITY_API_KEY
        if not self.api_key:
            logger.error("Perplexity API key not found in environment variables")
            raise ValueError("Perplexity API key not found in environment variables")

    def _get_headers(self):
        """Get headers for API requests"""
        return {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
            "Accept": "application/json"
        }

    def query(self, prompt, model="sonar-reasoning-pro", context=None, stream=False, follow_up=False, retries=3):
        """
        Make a query to the Sonar API with retry logic
        
        Args:
            prompt (str): The prompt to send to the API
            model (str): The model to use
            context (dict, optional): Context information
            stream (bool, optional): Whether to stream the response
            follow_up (bool, optional): Whether this is a follow-up question
            retries (int): Number of retry attempts
            
        Returns:
            dict: The API response
        """
        logger.debug(f"Querying Sonar API with model={model}, stream={stream}, follow_up={follow_up}")
        messages = [{"role": "user", "content": prompt}]
        
        if context:
            messages.insert(0, {"role": "system", "content": json.dumps(context)})
        
        payload = {"model": model, "messages": messages, "stream": stream}
        
        session = requests.Session()
        retry = Retry(total=retries, backoff_factor=1, status_forcelist=[429, 500, 502, 503, 504])
        session.mount('https://', HTTPAdapter(max_retries=retry))
        
        for attempt in range(retries + 1):
            try:
                logger.debug(f"Sending API request (attempt {attempt + 1}): {json.dumps(payload, indent=2)}")
                response = session.post(
                    self.BASE_URL, 
                    headers=self._get_headers(), 
                    json=payload
                )
                response.raise_for_status()
                api_response = response.json()
                logger.debug(f"API response: {json.dumps(api_response, indent=2)}")
                return api_response
            except requests.exceptions.RequestException as e:
                logger.error(f"API request failed (attempt {attempt + 1}): {str(e)}")
                if attempt < retries:
                    logger.info(f"Retrying API call ({attempt + 1}/{retries})")
                    continue
                return {"error": f"API request failed after {retries} attempts: {str(e)}"}

    def extract_json_from_response(self, content):
        """
        Extract JSON content from Sonar API response that may contain <think> tags
        """
        try:
            # First, try to parse as direct JSON
            return json.loads(content)
        except json.JSONDecodeError:
            # If that fails, look for JSON within the content
            
            # Method 1: Look for content between ```json and ``` markers
            json_match = re.search(r'```json\s*(\{.*?\})\s*```', content, re.DOTALL)
            if json_match:
                try:
                    return json.loads(json_match.group(1))
                except json.JSONDecodeError:
                    pass
            
            # Method 2: Extract everything after </think> tag if present
            think_end = content.find('</think>')
            if think_end != -1:
                remaining_content = content[think_end + 8:].strip()
                # Look for JSON in the remaining content
                json_match = re.search(r'```json\s*(\{.*?\})\s*```', remaining_content, re.DOTALL)
                if json_match:
                    try:
                        return json.loads(json_match.group(1))
                    except json.JSONDecodeError:
                        pass
                
                # Also try to parse the remaining content directly as JSON
                try:
                    return json.loads(remaining_content)
                except json.JSONDecodeError:
                    pass
            
            # Method 3: Look for the largest JSON object in the content
            # Find all potential JSON objects (starting with { and ending with })
            brace_count = 0
            start_pos = -1
            
            for i, char in enumerate(content):
                if char == '{':
                    if start_pos == -1:
                        start_pos = i
                    brace_count += 1
                elif char == '}':
                    brace_count -= 1
                    if brace_count == 0 and start_pos != -1:
                        # Found a complete JSON object
                        json_str = content[start_pos:i+1]
                        try:
                            parsed = json.loads(json_str)
                            if isinstance(parsed, dict) and 'meal_plan' in parsed:
                                return parsed
                        except json.JSONDecodeError:
                            continue
                        finally:
                            start_pos = -1
            
            # If all methods fail, raise an error
            raise ValueError("No valid JSON found in response")

    def generate_meal_plan(self, user_profile):
        """Generate a meal plan based on user profile with enhanced debugging"""
        logger.info("=== SONAR MEAL PLAN GENERATION STARTED ===")
        logger.info(f"Input user_profile: {user_profile}")
        
        try:
            trimester = user_profile.get('trimester', 1)
            dietary_prefs = user_profile.get('dietary_preferences', [])
            allergies = user_profile.get('allergies', '')
            cultural_prefs = user_profile.get('cultural_preferences', '')
            conditions = user_profile.get('pregnancy_conditions', [])
            
            logger.info(f"Parsed profile - Trimester: {trimester}, Dietary: {dietary_prefs}, Cultural: {cultural_prefs}")
            
            # Updated prompt to include recipe and citations
            prompt = f"""
            Generate a detailed 7-day vegan meal plan for a pregnant woman with the following profile:
            - Trimester: {trimester}
            - Dietary Preferences: {', '.join(dietary_prefs)}
            - Allergies/Intolerances: {allergies}
            - Cultural Food Preferences: {cultural_prefs}
            - Pregnancy Conditions: {', '.join(conditions)}
            
            IMPORTANT: Return ONLY valid JSON in this exact format with no additional text, explanations, or thinking tags:
            
            {{
              "days": [
                {{
                  "day": "Monday",
                  "meals": {{
                    "Breakfast": {{
                      "name": "dish name",
                      "description": "description",
                      "nutritional_benefits": "benefits",
                      "recipe": "step-by-step recipe instructions",
                      "citations": ["source1", "source2"]
                    }},
                    "Lunch": {{
                      "name": "dish name",
                      "description": "description",
                      "nutritional_benefits": "benefits",
                      "recipe": "step-by-step recipe instructions",
                      "citations": ["source1", "source2"]
                    }},
                    "Snack 1": {{
                      "name": "dish name",
                      "description": "description",
                      "nutritional_benefits": "benefits",
                      "recipe": "step-by-step recipe instructions",
                      "citations": ["source1", "source2"]
                    }},
                    "Snack 2": {{
                      "name": "dish name",
                      "description": "description",
                      "nutritional_benefits": "benefits",
                      "recipe": "step-by-step recipe instructions",
                      "citations": ["source1", "source2"]
                    }},
                    "Dinner": {{
                      "name": "dish name",
                      "description": "description",
                      "nutritional_benefits": "benefits",
                      "recipe": "step-by-step recipe instructions",
                      "citations": ["source1", "source2"]
                    }}
                  }}
                }}
              ]
            }}
            
            Include all 7 days (Monday through Sunday) with proper nutritional benefits, recipes, and citations for pregnancy. Recipes should be concise and practical. Citations should reference relevant sources used for each meal.
            """
            
            context = {
                "instructions": "You must respond with ONLY valid JSON. Do not include any thinking process, explanations, or additional text. Return only the JSON structure requested."
            }
            
            logger.info("Calling Sonar API...")
            response = self.query(prompt, model="sonar-reasoning-pro", context=context)
            logger.info(f"Sonar API response type: {type(response)}")
            logger.info(f"Sonar API response keys: {list(response.keys()) if isinstance(response, dict) else 'Not a dict'}")
            
            # Enhanced response processing with JSON extraction
            try:
                if 'choices' in response and len(response['choices']) > 0:
                    content = response['choices'][0]['message']['content']
                    logger.info(f"Raw API content length: {len(content)}")
                    logger.info(f"Raw API content preview: {content[:300]}...")
                    
                    # Extract JSON from the response
                    try:
                        meal_plan_data = self.extract_json_from_response(content)
                        logger.info("Successfully extracted JSON from response")
                        
                        # Validate the structure
                        if not isinstance(meal_plan_data, dict):
                            raise ValueError("Response is not a valid dictionary")
                        
                        # Handle different JSON structures
                        if 'meal_plan' in meal_plan_data:
                            nested_data = meal_plan_data['meal_plan']
                            if isinstance(nested_data, dict):
                                days_array = []
                                day_names = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
                                for i in range(1, 8):
                                    day_key = f"day_{i}"
                                    if day_key in nested_data:
                                        day_data = {
                                            "day": day_names[i-1],
                                            "meals": nested_data[day_key]
                                        }
                                        days_array.append(day_data)
                                
                                if days_array:
                                    meal_plan_data = {"days": days_array}
                                    logger.info(f"Converted nested structure to days array with {len(days_array)} days")
                            elif isinstance(nested_data, list):
                                meal_plan_data = {"days": nested_data}
                        
                        # Validate final structure
                        if 'days' not in meal_plan_data:
                            logger.error("No 'days' key found in meal plan data")
                            return {"error": "Invalid meal plan structure - missing days"}
                        
                        days_data = meal_plan_data['days']
                        if not isinstance(days_data, list) or len(days_data) == 0:
                            logger.error("Days data is not a valid list or is empty")
                            return {"error": "Invalid meal plan structure - invalid days data"}
                        
                        logger.info(f"Successfully validated meal plan with {len(days_data)} days")
                        return meal_plan_data
                        
                    except ValueError as json_error:
                        logger.error(f"JSON extraction failed: {str(json_error)}")
                        # Fallback to text parsing
                        logger.info("Attempting fallback text parsing...")
                        fallback_result = self._format_text_response_to_json(content)
                        if fallback_result and fallback_result.get('days'):
                            logger.info("Fallback text parsing successful")
                            return fallback_result
                        else:
                            logger.error("Fallback text parsing also failed")
                            return {"error": f"Failed to extract JSON: {str(json_error)}"}
                    
                else:
                    logger.error(f"Invalid API response structure: {response}")
                    return {"error": "Invalid response format from API"}
                    
            except Exception as parse_error:
                logger.error(f"Failed to parse meal plan: {str(parse_error)}")
                logger.error(f"Parse error type: {type(parse_error)}")
                logger.error(f"Parse traceback: {traceback.format_exc()}")
                return {"error": f"Failed to parse meal plan: {str(parse_error)}"}
                
        except Exception as e:
            logger.error(f"=== SONAR MEAL PLAN GENERATION FAILED ===")
            logger.error(f"Sonar generation error: {str(e)}")
            logger.error(f"Error type: {type(e)}")
            logger.error(f"Full traceback: {traceback.format_exc()}")
            return {"error": f"Sonar generation failed: {str(e)}"}

    def _recover_partial_json(self, content):
        """
        Attempt to recover a partial JSON meal plan from a malformed string
        
        Args:
            content (str): The malformed JSON string
            
        Returns:
            dict: A partial meal plan if recoverable, else None
        """
        logger.debug("Attempting to recover partial JSON")
        try:
            # Find the last valid day entry
            last_valid_pos = content.rfind('},')  # Look for end of a day object
            if last_valid_pos == -1:
                return None
                
            # Truncate to the last valid day
            partial_content = content[:last_valid_pos + 1] + ']}'
            # Wrap in the days structure
            if not partial_content.startswith('{"days":'):
                partial_content = '{"days": [' + partial_content.lstrip('{').lstrip('[')
            
            parsed_json = json.loads(partial_content)
            
            if parsed_json.get('days') and isinstance(parsed_json['days'], list):
                logger.info(f"Recovered {len(parsed_json['days'])} days from partial JSON")
                return parsed_json
            return None
        except Exception as e:
            logger.error(f"Partial JSON recovery failed: {str(e)}")
            return None

    def _format_text_response_to_json(self, text):
        """
        Convert a text response to a structured JSON format
        Used as a fallback when the API doesn't return valid JSON
        """
        logger.debug(f"Formatting text response to JSON: {text[:200]}...")
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
                
            day_match = any(day.lower() in line.lower() for day in days)
            if day_match:
                if current_day and current_meals:
                    meal_plan["days"].append({
                        "day": current_day,
                        "meals": current_meals
                    })
                    logger.debug(f"Added day to meal plan: {current_day}")
                
                for day in days:
                    if day.lower() in line.lower():
                        current_day = day
                        current_meals = {}
                        logger.debug(f"Starting new day: {current_day}")
                        break
                continue
            
            meal_match = None
            for meal in meal_types:
                if meal.lower() in line.lower() or (meal == "Snack 1" and "snack" in line.lower()):
                    meal_match = meal
                    content = line.split(":", 1)[1].strip() if ":" in line else ""
                    if not content:
                        continue
                    
                    current_meals[meal_match] = {
                        "name": content,
                        "description": "",
                        "nutritional_benefits": ""
                    }
                    logger.debug(f"Added meal: {meal_match} - {content}")
                    break
            
            if meal_match is None and current_day and current_meals:
                last_meal = list(current_meals.keys())[-1] if current_meals else None
                if last_meal:
                    if "description" in current_meals[last_meal]:
                        current_meals[last_meal]["description"] += " " + line
                    else:
                        current_meals[last_meal]["description"] = line
                    logger.debug(f"Appended description to {last_meal}: {line}")
        
        if current_day and current_meals:
            meal_plan["days"].append({
                "day": current_day,
                "meals": current_meals
            })
            logger.debug(f"Final day added: {current_day}")
        
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
        
        # Create context string for user profile
        profile_context = []
        if trimester:
            profile_context.append(f"Trimester {trimester}")
        if dietary_prefs:
            profile_context.append(f"Diet: {', '.join(dietary_prefs)}")
        if allergies:
            profile_context.append(f"Allergies: {allergies}")
        if conditions:
            profile_context.append(f"Conditions: {', '.join(conditions)}")
        
        profile_str = " | ".join(profile_context) if profile_context else "General pregnancy"
        
        prompt = f"""
        Answer this pregnancy nutrition question for: {profile_str}
        
        Question: {question}
        
        CRITICAL REQUIREMENTS:
        - Maximum 120 words total
        - Use emojis for visual appeal (✅ ⚠️ 💡 🍽️ etc.)
        - Include 1-2 practical tips with source citations
        - Add numbered citations [1][2] when referencing research
        - Be reassuring but medically accurate
        - Format: Brief answer + key points + tip
        - No thinking process or explanations about response length
        
        Example format:
        "✅ [Food] is generally safe during pregnancy in moderation.
        
        ⚠️ Key considerations: [2-3 bullet points]
        
        💡 Tip: [Practical advice]
        
        📚 Consult your OB-GYN for personalized guidance."
        """
        
        try:
            response = self.query(prompt, model="sonar-reasoning-pro")
            
            if 'choices' in response and len(response['choices']) > 0:
                content = response['choices'][0]['message']['content']
                
                # Remove any thinking process wrapped in <think> tags
                content = re.sub(r'<think>.*?</think>', '', content, flags=re.DOTALL)
                
                # Clean up extra whitespace
                content = re.sub(r'\n\s*\n', '\n\n', content.strip())
                
                # Add citations if available
                citations = response.get('citations', [])
                if citations:
                    content += self._format_citations(content, citations)
                
                # Truncate if still too long (keep under 1400 chars for safety margin)
                if len(content) > 1400:
                    # Find last complete sentence within limit
                    truncated = content[:1350]
                    last_period = truncated.rfind('.')
                    last_question = truncated.rfind('?')
                    last_exclamation = truncated.rfind('!')
                    
                    last_sentence_end = max(last_period, last_question, last_exclamation)
                    
                    if last_sentence_end > 1000:  # Ensure we have substantial content
                        content = content[:last_sentence_end + 1]
                    else:
                        content = content[:1350] + "..."
                
                return content
            else:
                return "⚠️ I couldn't generate an answer right now. Please try asking again or consult your healthcare provider for guidance."
                
        except Exception as e:
            logger.error(f"Error getting nutrition answer: {str(e)}")
            return "⚠️ I'm experiencing technical difficulties. Please try again later or consult your healthcare provider."

    def _format_citations(self, content, citations):
        """
        Format citations for inclusion in the response
        
        Args:
            content (str): The main response content
            citations (list): List of citation URLs from Sonar API
            
        Returns:
            str: Formatted citations to append to content
        """
        if not citations:
            return ""
        
        # Check if content has citation markers like [1], [2], etc.
        citation_markers = re.findall(r'\[(\d+)\]', content)
        
        if citation_markers:
            # Format citations with markers
            citation_text = "\n\n🔗 Sources:\n"
            used_indices = set(int(marker) for marker in citation_markers)
            
            for i, url in enumerate(citations[:5]):  # Limit to 5 citations
                if (i + 1) in used_indices:
                    # Try to get domain name for readability
                    domain = re.search(r'https?://(?:www\.)?([^/]+)', url)
                    domain_name = domain.group(1) if domain else url
                    citation_text += f"[{i+1}] {domain_name}\n"
        else:
            # No specific markers, just add general sources
            citation_text = "\n\n🔗 Sources: "
            domains = []
            for url in citations[:3]:  # Limit to 3 for space
                domain = re.search(r'https?://(?:www\.)?([^/]+)', url)
                if domain:
                    domain_name = domain.group(1)
                    if domain_name not in domains:
                        domains.append(domain_name)
            
            citation_text += ", ".join(domains)
        
        return citation_text

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
        
        if 'choices' in response and len(response['choices']) > 0:
            content = response['choices'][0]['message']['content']
            
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
        
    # Updated sonar.py tip generation method

    def generate_meal_plan_tip(self, user_profile, day_data):
        """
        Generate a nutrition tip based on user profile and selected day's meal plan
        
        Args:
            user_profile (dict): User preferences and health information
            day_data (dict): Selected day's meal plan data
        
        Returns:
            dict: A tip with content and source
        """
        trimester = user_profile.get('trimester', 1)
        dietary_prefs = user_profile.get('dietary_preferences', [])
        allergies = user_profile.get('allergies', '')
        conditions = user_profile.get('pregnancy_conditions', [])
        
        # Extract key ingredients from the day's meals
        # Handle both data structures: with and without 'meals' wrapper
        meals_data = day_data.get('meals', day_data)
        meals = []
        
        for meal_type in ['breakfast', 'lunch', 'dinner', 'snacks']:
            if meal_type in meals_data:
                if meal_type == 'snacks':
                    meals.extend([snack.get('description', '') for snack in meals_data[meal_type]])
                else:
                    meals.append(meals_data[meal_type].get('description', ''))
        
        # Create a list of ingredients from meal descriptions
        ingredients = ' '.join(meals).lower()
        
        # Define a comprehensive mapping of ingredients to nutrients and benefits
        nutrient_map = {
            'millet': {'nutrient': 'iron', 'benefit': 'essential for preventing anemia', 'source': 'ACOG guidelines'},
            'spinach': {'nutrient': 'folate', 'benefit': 'supports fetal development', 'source': 'March of Dimes'},
            'salmon': {'nutrient': 'omega-3 fatty acids', 'benefit': 'promotes brain development', 'source': 'APA'},
            'mackerel': {'nutrient': 'omega-3 fatty acids', 'benefit': 'promotes brain development', 'source': 'APA'},
            'tilapia': {'nutrient': 'protein', 'benefit': 'supports tissue growth', 'source': 'Mayo Clinic'},
            'fish': {'nutrient': 'omega-3 fatty acids', 'benefit': 'promotes brain development', 'source': 'APA'},
            'chicken': {'nutrient': 'protein', 'benefit': 'supports muscle development', 'source': 'ACOG'},
            'turkey': {'nutrient': 'iron', 'benefit': 'prevents anemia', 'source': 'ACOG'},
            'beef': {'nutrient': 'iron', 'benefit': 'prevents anemia', 'source': 'ACOG'},
            'eggs': {'nutrient': 'choline', 'benefit': 'supports brain development', 'source': 'NIH'},
            'avocado': {'nutrient': 'folate', 'benefit': 'prevents birth defects', 'source': 'CDC'},
            'plantain': {'nutrient': 'potassium', 'benefit': 'regulates blood pressure', 'source': 'AHA'},
            'sweet potato': {'nutrient': 'beta-carotene', 'benefit': 'supports vision development', 'source': 'NIH'},
            'beans': {'nutrient': 'fiber', 'benefit': 'aids digestion', 'source': 'ACOG'},
            'quinoa': {'nutrient': 'protein', 'benefit': 'provides complete amino acids', 'source': 'Harvard Health'},
            'brown rice': {'nutrient': 'complex carbs', 'benefit': 'provides sustained energy', 'source': 'Mayo Clinic'},
            'coconut': {'nutrient': 'healthy fats', 'benefit': 'supports nutrient absorption', 'source': 'NIH'},
            'peanuts': {'nutrient': 'protein', 'benefit': 'supports growth', 'source': 'ACOG'},
            'cashews': {'nutrient': 'magnesium', 'benefit': 'supports bone health', 'source': 'NIH'},
            'water': {'nutrient': 'hydration', 'benefit': 'aids nutrient transport', 'source': 'ACOG'},
        }
        
        # Find a matching ingredient for the tip
        selected_nutrient = None
        for ingredient, data in nutrient_map.items():
            if ingredient in ingredients:
                selected_nutrient = data
                break
        
        # Default tip based on trimester and conditions
        if not selected_nutrient:
            if 'gestational diabetes' in conditions:
                selected_nutrient = {
                    'nutrient': 'fiber',
                    'benefit': 'helps regulate blood sugar',
                    'source': 'ADA'
                }
            elif trimester == 3:
                selected_nutrient = {
                    'nutrient': 'calcium',
                    'benefit': 'supports final bone development',
                    'source': 'ACOG'
                }
            else:
                selected_nutrient = {
                    'nutrient': 'iron',
                    'benefit': 'prevents pregnancy anemia',
                    'source': 'ACOG'
                }
        
        # Create a simple, direct tip without using the AI model
        # This avoids the XML debug content issue
        tip_content = f"{selected_nutrient['nutrient'].capitalize()} {selected_nutrient['benefit']} - {selected_nutrient['source']}"
        
        return {
            'content': tip_content,
            'source': selected_nutrient['source']
        }