# fitness_manager_agent/tools.py

import datetime
from typing import Dict, List, Any, Optional # <-- Added Optional
from google.cloud import firestore
from google.cloud.firestore_v1.vector import Vector
from google.cloud.firestore_v1 import FieldFilter
from google.cloud.firestore_v1.base_query import Or 
from settings import get_settings
from google import genai
import json 

SETTINGS = get_settings()
DB_CLIENT = firestore.Client(
    project=SETTINGS.GCLOUD_PROJECT_ID
)

# --- NEW COLLECTIONS ---
MEAL_LOGS = DB_CLIENT.collection("meal_logs")
WORKOUT_PLANS = DB_CLIENT.collection("workout_plans")
FORM_FEEDBACK = DB_CLIENT.collection("form_feedback")

GENAI_CLIENT = genai.Client(
    vertexai=True, location=SETTINGS.GCLOUD_LOCATION, project=SETTINGS.GCLOUD_PROJECT_ID
)

# --- CONSTANTS ---
EMBEDDING_DIMENSION = 768
EMBEDDING_FIELD_NAME = "embedding"

MEAL_LOG_FORMAT = """
Date: {log_time}
Meal: {meal_type}
Total Calories: {calories} kcal
Protein: {protein_g}g | Carbs: {carbs_g}g | Fat: {fat_g}g
Details: {description}
"""

WORKOUT_PLAN_FORMAT = """
Date: {creation_time}
Goal: {goal}
Duration: {duration_min} minutes
Workout: {name}
Exercises: {exercises}
"""
# --------------------

def sanitize_image_id(image_id: str) -> str:
    """Sanitize image ID by removing any leading/trailing whitespace."""
    if image_id.startswith("[IMAGE-"):
        image_id = image_id.split("ID ")[1].split("]")[0]
    return image_id.strip()

def log_meal_data(
    meal_type: str,
    calories: int,
    protein_g: float,
    carbs_g: float,
    fat_g: float,
    description: str,
    image_id: Optional[str] = None, # <-- CORRECTED
    log_time: Optional[str] = None,  # <-- CORRECTED
) -> str:
    """
    Store the nutritional data for a meal. This tool is called after analyzing
    a meal photo or text input.
    
    Args:
        meal_type (str): The type of meal (e.g., 'Breakfast', 'Lunch', 'Snack').
        calories (int): Total estimated calories for the meal.
        protein_g (float): Total protein in grams.
        carbs_g (float): Total carbohydrates in grams.
        fat_g (float): Total fat in grams.
        description (str): A brief description of the meal (e.g., "Scrambled eggs and toast").
        image_id (str, optional): The ID of the image, if provided.
        log_time (str, optional): The time of the meal in ISO format ("YYYY-MM-DDTHH:MM:SS.ssssssZ"). 
                                  Defaults to current time if not provided.

    Returns:
        str: A success message with the logged meal details.
    """
    try:
        if image_id:
            image_id = sanitize_image_id(image_id)
            
        if not log_time:
            log_time = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")

        doc = {
            "meal_type": meal_type,
            "calories": calories,
            "protein_g": protein_g,
            "carbs_g": carbs_g,
            "fat_g": fat_g,
            "description": description,
            "image_id": image_id,
            "log_time": log_time,
            "user_id": "default_user", 
        }

        MEAL_LOGS.add(doc)

        return (f"Meal '{description}' ({meal_type}) successfully logged. "
                f"Nutrition: {calories} kcal, {protein_g}g P, {carbs_g}g C, {fat_g}g F.")
    except Exception as e:
        raise Exception(f"Failed to log meal data: {str(e)}")


def create_workout_plan(
    name: str,
    goal: str,
    duration_min: int,
    exercises: List[Dict[str, Any]],
) -> str:
    """
    Generates and stores a structured workout plan in the database.
    
    Args:
        name (str): A descriptive name for the workout (e.g., 'Leg Day Power Lift').
        goal (str): The primary goal of the workout (e.g., 'Strength', 'Cardio', 'Endurance').
        duration_min (int): The planned duration of the workout in minutes.
        exercises (List[Dict[str, Any]]): A list of exercises. Each item must have:
            - name (str): Name of the exercise (e.g., 'Squat').
            - sets (int): Number of sets.
            - reps (str): Repetition scheme (e.g., '5x5', '10-12 reps').
            - notes (str, optional): Specific instructions (e.g., 'Use moderate weight').

    Returns:
        str: A string confirming the workout plan was saved.
    """
    try:
        if not all(isinstance(ex, dict) and 'name' in ex and 'sets' in ex for ex in exercises):
            raise ValueError("Invalid exercises format. Must be a list of dicts with 'name' and 'sets'.")

        creation_time = datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z")
        
        doc = {
            "name": name,
            "goal": goal,
            "duration_min": duration_min,
            "exercises": exercises,
            "creation_time": creation_time,
            "user_id": "default_user",
        }

        WORKOUT_PLANS.add(doc)
        
        exercise_summary = ", ".join([f"{ex['name']} ({ex['sets']} sets)" for ex in exercises])
        
        return (f"Workout Plan '{name}' successfully created and saved! "
                f"Goal: {goal}. Key exercises: {exercise_summary}.")
    except Exception as e:
        raise Exception(f"Failed to create workout plan: {str(e)}")


def analyze_form_and_store(
    image_id: str,
    exercise_name: str,
    main_feedback: str,
    correction_tips: List[str],
) -> str:
    """
    Stores the AI's detailed analysis of a user's exercise form based on an image.
    This tool should be called when the user uploads an image and asks for form review.

    Args:
        image_id (str): The unique identifier for the uploaded image.
        exercise_name (str): The name of the exercise shown in the image (e.g., 'Squat', 'Deadlift').
        main_feedback (str): A summary of the key observation (e.g., 'Good depth, but back is slightly rounded').
        correction_tips (List[str]): A list of 2-3 specific, actionable tips for improvement.

    Returns:
        str: A string confirming the analysis was logged successfully.
    """
    try:
        image_id = sanitize_image_id(image_id)
        
        doc = {
            "image_id": image_id,
            "exercise_name": exercise_name,
            "main_feedback": main_feedback,
            "correction_tips": correction_tips,
            "analysis_time": datetime.datetime.now(datetime.timezone.utc).isoformat().replace("+00:00", "Z"),
            "user_id": "default_user",
        }
        
        FORM_FEEDBACK.add(doc)

        return (f"Form analysis for {exercise_name} (Image ID: {image_id}) logged. "
                f"Main Feedback: {main_feedback}. Tips: {', '.join(correction_tips)}.")
    except Exception as e:
        raise Exception(f"Failed to store form analysis: {str(e)}")


def get_user_logs(
    start_date: str,
    end_date: str,
    log_type: str,
    limit: int = 5,
) -> str:
    """
    Retrieves the user's past meal logs, workout plans, or form feedback within a time range.

    Args:
        start_date (str): The start date for the filter (in ISO format, e.g. 'YYYY-MM-DD').
        end_date (str): The end date for the filter (in ISO format, e.g. 'YYYY-MM-DD').
        log_type (str): The type of log to retrieve ('meal', 'workout', or 'feedback').
        limit (int): Maximum number of results to return (default: 5).

    Returns:
        str: A string containing the list of matching log data.
    """
    try:
        # ... (rest of function logic remains the same)
        if log_type == 'meal':
            collection_ref = MEAL_LOGS
            time_field = "log_time"
            format_str = MEAL_LOG_FORMAT
        elif log_type == 'workout':
            collection_ref = WORKOUT_PLANS
            time_field = "creation_time"
            format_str = WORKOUT_PLAN_FORMAT
        elif log_type == 'feedback':
            collection_ref = FORM_FEEDBACK
            time_field = "analysis_time"
            format_str = "\nFeedback Time: {analysis_time}\nExercise: {exercise_name}\nFeedback: {main_feedback}\nTips: {correction_tips}"
        else:
            raise ValueError("Invalid log_type. Must be 'meal', 'workout', or 'feedback'.")

        start_datetime_iso = start_date + "T00:00:00.000000Z"
        end_datetime_iso = end_date + "T23:59:59.999999Z"

        # Base query with date range
        query = collection_ref.where(
            filter=firestore.And(
                [
                    FieldFilter(time_field, ">=", start_datetime_iso),
                    FieldFilter(time_field, "<=", end_datetime_iso),
                ]
            )
        ).limit(limit).order_by(time_field, direction=firestore.Query.DESCENDING)

        search_result_description = f"**User {log_type.upper()} Logs ({start_date} to {end_date}):**\n"
        results_found = False
        
        for doc in query.stream():
            data = doc.to_dict()
            
            if 'exercises' in data and log_type == 'workout':
                data['exercises'] = json.dumps(data['exercises'], indent=2)
            if 'correction_tips' in data and log_type == 'feedback':
                data['correction_tips'] = ", ".join(data['correction_tips'])
                
            search_result_description += format_str.format(**data)
            search_result_description += "\n---\n"
            results_found = True

        if not results_found:
            return f"No {log_type} logs found between {start_date} and {end_date}."

        return search_result_description
    except Exception as e:
        raise Exception(f"Error retrieving logs: {str(e)}")