import mimetypes
import gradio as gr
import requests
import base64
from typing import List, Dict, Any
from settings import get_settings
from PIL import Image
import io
# NOTE: Assuming you have 'schema.py' defining ImageData, ChatRequest, and ChatResponse
from schema import ImageData, ChatRequest, ChatResponse

SETTINGS = get_settings()

def encode_image_to_base64_and_get_mime_type(image_path: str) -> ImageData:
    """Encode a file to base64 string and get MIME type.
    Reads an image file and returns the base64-encoded image data and its MIME type.
    """
    # Read the image file
    with open(image_path, "rb") as file:
        image_content = file.read()

    # Get the mime type
    mime_type = mimetypes.guess_type(image_path)[0]

    # Base64 encode the image
    base64_data = base64.b64encode(image_content).decode("utf-8")

    # Return as ImageData object
    return ImageData(serialized_image=base64_data, mime_type=mime_type)

def decode_base64_to_image(base64_data: str) -> Image.Image:
    """Decode a base64 string to PIL Image.
    Converts a base64-encoded image string back to a PIL Image object.
    """
    # Decode the base64 string and convert to PIL Image
    image_data = base64.b64decode(base64_data)
    image_buffer = io.BytesIO(image_data)
    image = Image.open(image_buffer)

    return image

def get_response_from_llm_backend(
    message: Dict[str, Any],
    history: List[Dict[str, Any]],
) -> List[str | gr.Image]:
    """Send the message and history to the backend and get a response.
    The response includes text and any image attachments.
    """
    # Extract files and convert to base64
    image_data = []
    if uploaded_files := message.get("files", []):
        for file_path in uploaded_files:
            image_data.append(encode_image_to_base64_and_get_mime_type(file_path))

    # Prepare the request payload
    payload = ChatRequest(
        text=message["text"],
        files=image_data,
        session_id="default_session",
        user_id="default_user",
    )

    # Send request to backend
    try:
        response = requests.post(SETTINGS.BACKEND_URL, json=payload.model_dump())
        response.raise_for_status()  # Raise exception for HTTP errors

        result = ChatResponse(**response.json())
        if result.error:
            return [f"Error: {result.error}"]

        chat_responses = []

        # Check if the thinking process is available (for developer/debug view)
        if result.thinking_process:
            chat_responses.append(
                gr.ChatMessage(
                    role="assistant",
                    content=result.thinking_process,
                    metadata={"title": "🧠 Thinking Process"},
                )
            )

        # Main response
        chat_responses.append(gr.ChatMessage(role="assistant", content=result.response))

        # Handle image attachments from the backend
        if result.attachments:
            for attachment in result.attachments:
                image_data = attachment.serialized_image
                chat_responses.append(gr.Image(decode_base64_to_image(image_data)))

        return chat_responses
    except requests.exceptions.RequestException as e:
        return [f"Error connecting to backend service: {str(e)}"]

if __name__ == "__main__":
    demo = gr.ChatInterface(
        get_response_from_llm_backend,
        # --- ADJUSTED TEXT FOR FITNESS COACH AGENT ---
        title="🏋️‍♀️ Personal Fitness & Nutrition Coach", 
        description=(
            "Your AI coach to help you log meals, get form analysis, and create custom workouts."
        ),
        # ---------------------------------------------
        type="messages",
        multimodal=True,
        textbox=gr.MultimodalTextbox(file_count="multiple", file_types=["image"]),
    )

    demo.launch(
        server_name="0.0.0.0",
        server_port=8080,
    )