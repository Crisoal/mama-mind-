# chatbot/models.py
from django.db import models

class User(models.Model):
    """User model to store user preferences and information"""
    phone_number = models.CharField(max_length=20, unique=True)
    created_at = models.DateTimeField(auto_now_add=True)
    last_active = models.DateTimeField(auto_now=True)
    
    # Onboarding info
    trimester = models.IntegerField(null=True, blank=True)
    dietary_preferences = models.ManyToManyField('DietaryPreference', blank=True)
    allergies = models.TextField(blank=True)
    cultural_preferences = models.CharField(max_length=100, blank=True)
    pregnancy_conditions = models.ManyToManyField('PregnancyCondition', blank=True)
    
    # User preferences
    wants_meal_plans = models.BooleanField(default=False)
    wants_nutrition_tips = models.BooleanField(default=False)
    wants_recipe_suggestions = models.BooleanField(default=False)
    wants_nutrition_qa = models.BooleanField(default=False)
    
    # Current conversation state
    conversation_state = models.CharField(max_length=50, default='START')
    
    def __str__(self):
        return f"User {self.phone_number}"
    
    def get_dietary_preferences_list(self):
        return [pref.name for pref in self.dietary_preferences.all()]
    
    def get_pregnancy_conditions_list(self):
        return [cond.name for cond in self.pregnancy_conditions.all()]
    
    def reset_preferences(self):
        """Reset all user preferences"""
        self.trimester = None
        self.dietary_preferences.clear()
        self.allergies = ''
        self.cultural_preferences = ''
        self.pregnancy_conditions.clear()
        self.wants_meal_plans = False
        self.wants_nutrition_tips = False
        self.wants_recipe_suggestions = False
        self.wants_nutrition_qa = False
        self.conversation_state = 'START'
        self.save()

class DietaryPreference(models.Model):
    """Model to store dietary preferences"""
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name

class PregnancyCondition(models.Model):
    """Model to store pregnancy-related conditions"""
    name = models.CharField(max_length=50, unique=True)
    
    def __str__(self):
        return self.name

class Conversation(models.Model):
    """Model to store conversation history"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='conversations')
    message = models.TextField()
    response = models.TextField()
    timestamp = models.DateTimeField(auto_now_add=True)
    
    def __str__(self):
        return f"Conversation with {self.user.phone_number} at {self.timestamp}"

class MealPlan(models.Model):
    """Model to store generated meal plans"""
    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name='meal_plans')
    week_number = models.IntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    meal_plan_data = models.JSONField()  # Store the entire meal plan as JSON
    
    class Meta:
        unique_together = ('user', 'week_number')
    
    def __str__(self):
        return f"Meal plan for {self.user.phone_number}, Week {self.week_number}"

class NutritionTip(models.Model):
    """Model to store nutrition tips"""
    title = models.CharField(max_length=200)
    content = models.TextField()
    source = models.CharField(max_length=200, blank=True)
    trimester = models.IntegerField(null=True, blank=True)  # Which trimester this tip is for, null means all
    condition = models.ForeignKey(PregnancyCondition, null=True, blank=True, on_delete=models.SET_NULL)
    
    def __str__(self):
        return self.title