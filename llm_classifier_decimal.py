import pandas as pd
from openai import OpenAI


# --- Credentials (replace placeholder before running) ---
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"


def generate_decision_GPT(description):
    '''
    Input: an app description string
    Description: asks the model to score the app's U.S.-military relevance
    Output: a decimal between 0.0 and 1.0 (higher = more military-related)
    '''

    # Create the OpenAI client (falls back to OPENAI_API_KEY env var if unset)
    client = OpenAI(
        api_key=OPENAI_API_KEY,
    )

    # System prompt: defines the scoring rubric and constrains output to a decimal 0-1
    sys_prompt = '''You are a classifier - you will be given an instruction
    on how to classify an app description. Does it represent an app that
    someone in the USA military (any branch e.g., Army, Marine Corps,
    Navy, Air Force, Space Force and Coast Guard) or veteran can use? Please
    return a decimal score between 0 to 1, with 1 representing a stronger
    likelihood of the app being related to USA Military. If the app is for
    the military of another country (e.g., Canada) the likelihood should be closer to 0.
    If the app is about any military fitness, the likelihood should be closer to 0.
    If an app has use cases for the military but is most commonly used by the general
    population (e.g., a recruiting app that is not targeted towards only the military,
    like Indeed, LinkedIn, etc.), the likelihood should be closer to 0. If the app
    description is about a game that relates to the military, the likelihood should be
    closer to 0. If the description mentions military ranks, military dating, connecting
    military units and associations, assisting military personnel with language learning,
    personal use for service members, military transition support, veterans, National Guard,
    or if the app is an official U.S. military app developed by e.g., the Department of Veterans
    Affairs (VA), it should be rated closer to 1. Your output should only be a decimal number
    between 0 or 1 (up to two decimal points), nothing else.
    '''

    prompt = description

    # Build the chat messages: system instruction + the app description
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": prompt}
    ]

    response = client.chat.completions.create(
        model=             'gpt-4-turbo',  # Specify the model
        messages=messages,  # Your input messages
        max_tokens=1024,  # Max number of tokens in the output
        temperature=0.9,  # Controls the randomness of the output
        top_p=0.9,  # Controls diversity via nucleus sampling
        n=1,  # Number of completions to generate
        stop=None  # Sequence where the API will stop generating further tokens
    )

    return float(response.choices[0].message.content.strip())


# Load the dataset
file_path = '../input/YOUR_INPUT_FILE.xlsx'  # replace with your input spreadsheet
data = pd.read_excel(file_path)

# Score every app description with the model
data['predicted'] = data['description'].apply(generate_decision_GPT)
print(data['predicted'].unique())

# Map the human "Accurate" labels (Yes/No) to integers for reference
column_name_corrected = 'Accurate [No, Yes, ?] '
data['accurate_converted'] = data[column_name_corrected].map({'Yes': 1, 'No': 0})
print(data['accurate_converted'].unique())

# Drop rows with no human label (NaN)
data_cleaned = data.dropna(subset=['accurate_converted'])

data_cleaned.to_excel('../updated_results/YOUR_OUTPUT_FILE.xlsx', index=False)  # replace with your output filename
