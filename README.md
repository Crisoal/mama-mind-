# MamáMind: AI-Powered Pregnancy Nutrition Chatbot

## Introduction
MamáMind is a WhatsApp-based chatbot designed to support pregnant women with personalized, culturally relevant, and evidence-based nutrition guidance. Built for the **Perplexity Sonar Hackathon**, MamáMind leverages the Perplexity AI Sonar API to generate tailored meal plans, provide nutritional insights, and answer pregnancy-related dietary questions. The project aims to empower expectant mothers by addressing their unique needs based on trimester, dietary preferences, allergies, cultural food traditions, and pregnancy conditions.

**Project Name**: MamáMind  
**Tagline**: Nourishing Your Pregnancy Journey, One Meal at a Time  
**Platform**: WhatsApp Chatbot  
**Target Audience**: Pregnant women seeking accessible, personalized nutrition support

## Features
- **Personalized Onboarding**: Collects user profile details (trimester, dietary preferences, allergies, cultural preferences, pregnancy conditions) via text input to tailor the experience.
- **Weekly Meal Plans**: Generates a 7-day meal plan with breakfast, lunch, dinner, and two snacks, aligned with user preferences and nutritional needs for pregnancy.
- **Meal Details**: Allows users to view detailed meal information, including recipes, nutritional benefits, and citations, by selecting a specific day and meal.
- **Nutrition Q&A**: Provides answers to user-initiated dietary questions (e.g., "Is turmeric safe during pregnancy?") using the Sonar API.
- **Cultural Sensitivity**: Incorporates culturally relevant dishes (e.g., Fijian, Indian) based on user preferences.
- **Twilio Integration**: Ensures messages stay within the 1600-character limit for reliable WhatsApp delivery.


## User Flow
MamáMind operates as a conversational WhatsApp chatbot with a structured flow:

1. **Onboarding & Preferences Setup**:
   - User initiates with "Hi" or "Start".
   - Bot collects:
     - Trimester (e.g., "First")
     - Dietary preferences (e.g., "Vegetarian")
     - Allergies (e.g., "Peanuts")
     - Cultural preferences (e.g., "Indian")
     - Pregnancy conditions (e.g., "Anemia")
     - Usage preferences (e.g., "Weekly meal plans")
   - Input is text-based (e.g., user types "Vegetarian" instead of selecting radio buttons).
   - Example:
     ```
     User: Hi
     Bot: 👋 Hi! I’m MamáMind, your AI-powered pregnancy nutrition coach. Which trimester are you in? (First/Second/Third)
     User: First
     Bot: Thanks! Do you have any dietary preferences? (e.g., Vegetarian, Vegan, No restrictions)
     User: Vegetarian
     ```

2. **Weekly Meal Plan Generator**:
   - User types "Generate meal plan" or receives it automatically (if scheduled).
   - Bot generates a 7-day meal plan using the Sonar API, considering user profile.
   - User selects a day (e.g., "Monday") to view meals, then a meal (e.g., "Breakfast") for details.
   - Example:
     ```
     Bot: Here’s your Week 8 Meal Plan 🍽️ (type a day to view details):
     🗓️ Monday | Tuesday | Wednesday...
     User: Monday
     Bot: 🗓️ Monday
     🥣 Breakfast: Fonio Pancakes
        Ancient grain pancakes with peanut butter
        ✨ Gluten-free with complete protein
     🍎 Snack 1: Palmnut Soup Bread...
     🍴 Select a meal for details: Breakfast | Snack 1 | Lunch | Snack 2 | Dinner
     User: Breakfast
     Bot: 🥣 Breakfast: Fonio Pancakes
     📝 Description: Ancient grain pancakes with peanut butter
     ✨ Benefits: Gluten-free with complete protein
     👩‍🍳 Recipe: Mix 1 cup fonio flour, 1 tsp baking powder, 1 cup plant milk. Cook batter on a hot pan, 2 mins per side. Spread 1 tbsp peanut butter.
     📚 Sources: dpuhospital.com, krishnamedicalcentre.org
     🧠 Tip: Iron prevents pregnancy anemia - ACOG.
     📤 Want to share this meal plan? Reply 'Yes' or 'No'.
     ```

3. **Daily Tips & Nudges** (Incomplete):
   - Basic tips are generated for meal plans (e.g., "Iron prevents pregnancy anemia").
   - Planned but not implemented: Scheduled daily tips at 8:00 AM and nudges (e.g., "Don’t forget your iron-rich smoothie!").
   - Example (current):
     ```
     🧠 Tip: Stay hydrated and eat regularly for optimal nutrient absorption.
     ```

4. **User-Initiated Q&A**:
   - Users ask dietary questions (e.g., "Can I eat jackfruit in pregnancy?").
   - Bot responds with concise, evidence-based answers using the Sonar API.
   - Example:
     ```
     User: Is turmeric safe daily?
     Bot: Turmeric is safe in small amounts (e.g., in cooking) during pregnancy but avoid high-dose supplements. Consult your doctor. Source: ACOG.
     ```

5. **Share Meal Plan** (Incomplete):
   - Prompts users to share plans ("Reply 'Yes' or 'No'"), but sharing functionality is not implemented.
   - Planned: Generate a text or PDF for sharing with partners or midwives.

6. **Exit or Restart**:
   - User types "End" to save preferences and exit.
   - "Start over" clears the profile after confirmation.
   - "Update preferences" restarts onboarding.
   - Example:
     ```
     User: End
     Bot: Thank you for using MamáMind! Your preferences have been saved. Type 'Start' anytime to chat again.
     ```

## Technical Implementation
### Tech Stack
- **Backend**: Python, Django
- **Database**: Django ORM (PostgreSQL assumed)
- **AI**: Perplexity Sonar API for meal plan generation and Q&A
- **Messaging**: Twilio WhatsApp API
- **Logging**: Python `logging` module for debugging
- **Deployment**: Not specified (assumed local or cloud-based)

### Key Components
1. **BotLogic (bot_logic.py)**:
   - Core logic for handling user messages and conversation states.
   - Manages onboarding, meal plan generation, day/meal selection, and Q&A.
   - Uses state machine (e.g., `AWAITING_TRIMESTER`, `AWAITING_MEAL_SELECTION`) to track user progress.
   - Integrates with Sonar API for meal plans and tips.
   - Ensures messages stay within Twilio’s 1600-character limit by truncating descriptions, recipes, and citations.

2. **SonarAPI (sonar.py)**:
   - Interfaces with the Perplexity Sonar API to generate JSON-formatted meal plans.
   - Includes fields: meal name, description, nutritional benefits, recipe, citations.
   - Handles JSON parsing and fallback text processing for robustness.

3. **Models (models.py)**:
   - `User`: Stores phone number, trimester, dietary preferences, allergies, cultural preferences, pregnancy conditions, conversation state, and selected day.
   - `MealPlan`: Saves generated meal plans with week number and JSON data.
   - `DietaryPreference` and `PregnancyCondition`: Store predefined options.

4. **WhatsAppHandler**:
   - Manages Twilio WhatsApp API integration for sending/receiving messages.
   - Ensures reliable message delivery within character limits.

### Project Structure



### Limitations
- **Text Input**: User input is text-based (e.g., "Vegetarian" instead of radio buttons), which may lead to parsing errors for unexpected inputs. Input validation could be improved.
- **Scalability**: Current implementation assumes a single user interaction at a time. High user volumes may require queuing or async processing.
- **Error Handling**: While robust, some edge cases (e.g., malformed Sonar API responses) may need additional handling.

## Setup Instructions
1. **Clone the Repository**:
   ```bash
   git clone https://github.com/Crisoal/mama-mind-.git
   cd mamamind


Install Dependencies:
pip install -r requirements.txt


Set Up Environment Variables:Create a .env file with:
TWILIO_ACCOUNT_SID=your_sid
TWILIO_AUTH_TOKEN=your_token
SONAR_API_KEY=your_key
DATABASE_URL=your_db_url


Run Migrations:
python manage.py makemigrations
python manage.py migrate


Start the Server:
python manage.py runserver


Configure Twilio Webhook:

Set the Twilio WhatsApp webhook to http://your-server/chatbot/webhook/.
Test with a WhatsApp message to the Twilio number.



Future Enhancements

Complete Daily Tips & Nudges:
Implement a task scheduler (e.g., Celery with Redis) for automated 8:00 AM tips.
Add personalized nudges based on user behavior (e.g., reminders for missed meals).


Implement Share Plan:
Generate a formatted text or PDF for meal plans using a library like reportlab.
Allow sharing via WhatsApp to specified contacts.


Improve Input Handling:
Enhance text parsing with fuzzy matching or NLP to handle misspelled inputs.
Optionally integrate WhatsApp interactive buttons for structured responses.


Multilingual Support:
Add support for languages like Hindi or Swahili to broaden accessibility.


Analytics Dashboard:
Build a dashboard to track user engagement, popular meals, and Q&A trends.


Offline Mode:
Cache meal plans for users with limited internet access.



MamáMind: Empowering Expectant Mothers with Nutrition, One Chat at a Time 🌟

### Key Sections Explained
- **Introduction**: Introduces MamáMind, its purpose, and the hackathon context.
- **Features**: Lists implemented features (onboarding, meal plans, Q&A) and notes partially implemented ones (tips, sharing).
- **User Flow**: Details the conversational flow, emphasizing text-based input (no radio buttons) and including examples from the provided meal plan (e.g., Fonio Pancakes).
- **Technical Implementation**: Describes the tech stack, key components (BotLogic, SonarAPI, models), and project structure.
- **Limitations**: Acknowledges incomplete features (tips, sharing) and other constraints (text input, scalability).
- **Setup Instructions**: Provides clear steps for running the project locally.
- **Future Enhancements**: Suggests improvements like completing tips, sharing, and adding multilingual support.
- **Hackathon Context**: Ties the project to the Perplexity Sonar Hackathon, highlighting its relevance.


