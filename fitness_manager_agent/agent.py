# fitness_manager_agent/agent.py

from google.adk.agents import Agent
from fitness_manager_agent.tools import ( # Using correct package name
    log_meal_data,            
    create_workout_plan,      
    get_user_logs,            
    analyze_form_and_store    
)
from fitness_manager_agent.callbacks import modify_image_data_in_history # Using correct package name

import os
from settings import get_settings
from google.adk.planners import BuiltInPlanner
from google.genai import types

SETTINGS = get_settings()
# Setup environment variables for Vertex AI/Gemini access
os.environ["GOOGLE_CLOUD_PROJECT"] = SETTINGS.GCLOUD_PROJECT_ID
os.environ["GOOGLE_CLOUD_LOCATION"] = SETTINGS.GCLOUD_LOCATION
os.environ["GOOGLE_GENAI_USE_VERTEXAI"] = "TRUE"

# Load the task prompt/instructions for the agent
current_dir = os.path.dirname(os.path.abspath(__file__))
prompt_path = os.path.join(current_dir, "task_prompt.md")
with open(prompt_path, "r") as file:
    task_prompt = file.read()

root_agent = Agent(
    name="fitness_coach_agent",
    model="gemini-2.5-flash",
    description=(
        "Personalized fitness and nutrition coach to help the user log meals, "
        "analyze exercise form from images, and create structured workout plans."
    ),
    instruction=task_prompt,
    tools=[
        log_meal_data,
        create_workout_plan,
        get_user_logs,
        analyze_form_and_store,
    ],
    planner=BuiltInPlanner(
        thinking_config=types.ThinkingConfig(
            thinking_budget=2048,
        )
    ),
    before_model_callback=modify_image_data_in_history, 
)