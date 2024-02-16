import openai

# Set your OpenAI API key here
openai.api_key = 'your_openai_api_key'

def chat_with_neet_instructor(user_input, history=[]):
    """
    Function to interact with OpenAI's ChatGPT model as a NEET instructor.
    
    Parameters:
    - user_input (str): The user's question or message.
    - history (list): The conversation history formatted as required by OpenAI's API.
    
    Returns:
    - response (str): The assistant's reply.
    """
    
    system_prompt = {
        "role": "system",
        "content": "You are a helpful assistant acting as a NEET instructor. You are knowledgeable in Physics, Chemistry, Biology, and NEET exam strategies. Your goal is to assist students in preparing for the NEET examination by providing accurate, clear, and helpful answers to their questions. You should stay focused on topics relevant to the NEET syllabus and exam preparation."
    }
    
    # Prepare messages including system prompt, past history, and the new user input
    messages = [system_prompt] + history + [{"role": "user", "content": user_input}]
    
    response = openai.ChatCompletion.create(
        model="gpt-3.5-turbo",
        messages=messages
    )
    
    # Assuming the response is successful and contains the expected data
    return response.choices[0].message['content'] if response.choices else "Sorry, I couldn't generate a response. Please try again."

def prepare_and_chat_with_neet_instructor(new_question, past_history):
    """
    Prepares the chat history in the required format and calls the chat_with_neet_instructor function.

    Parameters:
    - new_question (str): The new question from the user.
    - past_history (list): A list of past interactions, formatted as dictionaries with 'role' and 'content'.

    Returns:
    - str: The response from the NEET instructor.
    """
    # System message to guide the conversation, only add if starting a new conversation
    if not past_history:
        system_message = {
            "role": "system",
            "content": "You are a NEET instructor, knowledgeable in Physics, Chemistry, and Biology, focusing on NEET examination preparation. Answer queries based on the NEET syllabus, maintaining relevance and accuracy."
        }
        formatted_history = [system_message]
    else:
        formatted_history = []

    # Add past history to the formatted history
    for message in past_history:
        formatted_history.append({
            "role": message["role"],
            "content": message["content"]
        })

    # Call the NEET instructor chat function with the new question and prepared history
    response = chat_with_neet_instructor(new_question, formatted_history)
    return response

# Example usage
# past_history = [
#     {"role": "user", "content": "What is the structure of DNA?"},
#     {"role": "assistant", "content": "DNA structure is a double helix formed by base pairs attached to a sugar-phosphate backbone."},
#     # Add more past interactions here if any
# ]

# new_question = "Can you explain the process of photosynthesis?"

# # Call the helper function
# response = prepare_and_chat_with_neet_instructor(new_question, past_history)
# print(response)
