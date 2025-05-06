# mealplanner/models.py
from django.db import models

class Recipe(models.Model):
    """Model to store recipe information"""
    name = models.CharField(max_length=200)
    description = models.TextField()
    ingredients = models.JSONField()
    instructions = models.TextField()
    prep_time = models.IntegerField()  # in minutes
    cook_time = models.IntegerField()  # in minutes
    meal_type = models.CharField(max_length=50)  # breakfast, lunch, dinner, snack
    suitable_trimesters = models.CharField(max_length=20, default="1,2,3")  # comma-separated list of suitable trimesters
    
    # Nutritional information
    calories = models.IntegerField(null=True, blank=True)
    protein = models.FloatField(null=True, blank=True)
    carbs = models.FloatField(null=True, blank=True)
    fat = models.FloatField(null=True, blank=True)
    iron = models.FloatField(null=True, blank=True)
    folate = models.FloatField(null=True, blank=True)
    calcium = models.FloatField(null=True, blank=True)
    
    # Cultural classification
    cuisine = models.CharField(max_length=100, blank=True)
    
    # Dietary classification
    is_vegetarian = models.BooleanField(default=False)
    is_vegan = models.BooleanField(default=False)
    is_gluten_free = models.BooleanField(default=False)
    is_dairy_free = models.BooleanField(default=False)
    
    # Common allergens contained
    contains_allergens = models.JSONField(default=list)
    
    # Health condition benefits
    good_for_anemia = models.BooleanField(default=False)
    good_for_gestational_diabetes = models.BooleanField(default=False)
    good_for_hypertension = models.BooleanField(default=False)
    good_for_morning_sickness = models.BooleanField(default=False)
    
    def __str__(self):
        return self.name