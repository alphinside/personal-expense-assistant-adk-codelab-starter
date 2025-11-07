# fitness_manager_agent/callbacks.py

import hashlib
from google.genai import types
from google.adk.agents.callback_context import CallbackContext
from google.adk.models.llm_request import LlmRequest

def modify_image_data_in_history(
    callback_context: CallbackContext, llm_request: LlmRequest) -> None:
    """
    Modifies the request sent to the LLM to manage the size of the conversation 
    history by limiting image data to the last 3 user messages.
    A text placeholder ([IMAGE-ID <hash>]) is used to preserve the reference 
    to older images for tool usage.
    """

    # Count how many user messages we've processed
    user_message_count = 0

    # Process the reversed list of conversation contents
    for content in reversed(llm_request.contents):
        # Only count for user manual query, not function call responses
        if (content.role == "user") and (content.parts[0].function_response is None):
            user_message_count += 1
            modified_content_parts = []

            # Check for images and manage their presence
            for idx, part in enumerate(content.parts):
                if part.inline_data is None:
                    modified_content_parts.append(part)
                    continue

                # Check if the next part is an existing placeholder. 
                # This handles subsequent calls to prevent duplicate placeholders.
                is_placeholder_missing = (
                    (idx + 1 >= len(content.parts))
                    or (content.parts[idx + 1].text is None)
                    or (not content.parts[idx + 1].text.startswith("[IMAGE-ID "))
                )

                if is_placeholder_missing:
                    # Generate hash ID for the image and create a placeholder
                    image_data = part.inline_data.data
                    hasher = hashlib.sha256(image_data)
                    image_hash_id = hasher.hexdigest()[:12]
                    placeholder = f"[IMAGE-ID {image_hash_id}]"

                    # Only keep image data in the last 3 user messages
                    if user_message_count <= 3:
                        modified_content_parts.append(part)

                    # Always add the placeholder text part
                    modified_content_parts.append(types.Part(text=placeholder))

                else:
                    # Placeholder exists, so we only need to manage the image data itself
                    if user_message_count <= 3:
                        modified_content_parts.append(part)
                    # The placeholder text part will be copied over in the next iteration

            # This updates the conversation history for the current LLM request
            content.parts = modified_content_parts