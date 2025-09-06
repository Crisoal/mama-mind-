import random
from datetime import datetime, timedelta
from django.utils import timezone
from chatbot.models import User, NutritionTip
from chatbot.utils.sonar import SonarAPI

class NutritionTipsService:
    """Service for managing nutrition tips"""
    
    def __init__(self):
        self.sonar = SonarAPI()
        
        # Pre-defined general tips by category
        self.general_tips = {
            "hydration": [
                "Aim for at least 8-10 glasses of water daily to support amniotic fluid levels and prevent dehydration.",
                "If plain water is unappealing, try adding slices of lemon, cucumber, or berries for natural flavor.",
                "Herbal teas like ginger or peppermint can count toward your daily fluid intake and may help with nausea.",
            ],
            "iron": [
                "Pair iron-rich foods like lentils with vitamin C sources (bell peppers, citrus) to enhance absorption.",
                "Cast-iron cookware can add small amounts of absorbable iron to your meals.",
                "Consider taking iron supplements with orange juice rather than with milk or calcium supplements.",
            ],
            "folate": [
                "Dark leafy greens like spinach, kale and collards are excellent natural sources of folate.",
                "Legumes including lentils, beans and peas are rich in folate needed for baby's neural development.",
                "Fortified cereals can be an excellent daily source of folate to complement your prenatal vitamin.",
            ],
            "calcium": [
                "If you're lactose intolerant, try calcium-fortified plant milks, tofu made with calcium sulfate, or bok choy.",
                "Weight-bearing exercise helps your body absorb calcium more effectively for stronger bones.",
                "Small fish with soft, edible bones like sardines and canned salmon are excellent calcium sources.",
            ],
            "protein": [
                "Aim for protein at every meal to help support your baby's growth and your changing body.",
                "Greek yogurt has nearly twice the protein of regular yogurt and makes a great breakfast or snack.",
                "Keep hard-boiled eggs in the fridge for quick protein when nausea strikes and cooking feels impossible.",
            ],
            "morning_sickness": [
                "Eat small amounts frequently rather than three large meals to help manage nausea.",
                                "Keep plain crackers by your bed to nibble on before getting up in the morning.",
                "Ginger tea or ginger candy can help alleviate nausea, and it's gentle on your stomach.",
                "Avoid strong smells and greasy or spicy foods if they trigger morning sickness.",
            ],
        }
    
    def generate_daily_tip(self, user):
        """
        Generate a daily nutrition tip based on the user's profile and preferences.
        
        Args:
            user (User): The user to generate a nutrition tip for.
        
        Returns:
            dict: A dictionary containing a nutrition tip.
        """
        # Prepare user profile
        user_profile = {
            'trimester': user.trimester,
            'dietary_preferences': user.get_dietary_preferences_list(),
            'allergies': user.allergies,
            'cultural_preferences': user.cultural_preferences,
            'pregnancy_conditions': user.get_pregnancy_conditions_list(),
        }
        
        # Generate a personalized tip using the Sonar API
        return self.sonar.generate_daily_tip(user_profile)
    
    def get_tip_by_category(self, category):
        """
        Retrieve a random tip from the pre-defined general tips based on category.
        
        Args:
            category (str): The category of tips (hydration, iron, folate, calcium, protein, morning_sickness).
        
        Returns:
            str: A random nutrition tip for the given category.
        """
        if category not in self.general_tips:
            return "Category not found. Please choose a valid category."
        
        return random.choice(self.general_tips[category])
    
    def get_random_tip(self):
        """
        Retrieve a random nutrition tip from all available categories.
        
        Returns:
            str: A random nutrition tip.
        """
        category = random.choice(list(self.general_tips.keys()))
        return self.get_tip_by_category(category)

