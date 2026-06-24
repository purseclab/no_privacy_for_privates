import pandas as pd
from sklearn.metrics import precision_score, recall_score, f1_score, accuracy_score
from openai import OpenAI


# --- Credentials (replace placeholder before running) ---
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"


def generate_decision_GPT(description):
    '''
    Input: an app description string
    Description: asks the model to classify the app as military-relevant or not
    Output: 1.0 if relevant to a U.S. service member/veteran, else 0.0
    '''

    # Create the OpenAI client (falls back to OPENAI_API_KEY env var if unset)
    client = OpenAI(
        api_key=OPENAI_API_KEY,
    )

    # System prompt: defines the classification rules and constrains output to 0/1
    sys_prompt = '''"You are a classifier - you will be given an instruction
    how to classify an app description. Does it represent an app that someone
    in the USA military (any branch e.g., Army, Marine Corps, Navy, Air Force,
    Space Force, and Coast Guard) or veteran can use? If so, please return 1. 
    If not please return 0. If the app is for military of another country
    (e.g., canada) please return 0. If the app is about any military fitness,
    please return 0. If an app has use cases for military but is most commonly
    used by the general population (e.g., a recruiting app that is not targeted
    towards military) return 0. If the app description is about a game that
    relates to the military please return 0. Your output should only be the
    integers 0 or 1, nothing else
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

# Map the human "Accurate" labels (Yes/No) to integers for scoring
column_name_corrected = 'Accurate [No, Yes, ?] '
data['accurate_converted'] = data[column_name_corrected].map({'Yes': 1, 'No': 0})
print(data['accurate_converted'].unique())

# Apply the classifier to every app description to produce predictions
data['predicted'] = data['description'].apply(generate_decision_GPT)
print(data['predicted'].unique())

# Drop rows with no human label (NaN) so they don't skew the metrics
data_cleaned = data.dropna(subset=['accurate_converted'])

# Extract true and predicted values
true_values = data_cleaned['accurate_converted']
predicted_values = data_cleaned['predicted']

data_cleaned.to_excel('YOUR_OUTPUT_FILE.xlsx', index=False)  # replace with your output filename

# Calculate metrics
accuracy = accuracy_score(true_values, predicted_values)
precision = precision_score(true_values, predicted_values, zero_division=1)
recall = recall_score(true_values, predicted_values, zero_division=1)
f1 = f1_score(true_values, predicted_values, zero_division=1)

# Print metrics
print("ML Metrics for Classifier Performance:")
print(f"Accuracy: {accuracy:.4f}")
print(f"Precision: {precision:.4f}")
print(f"Recall: {recall:.4f}")
print(f"F1-Score: {f1:.4f}")

# Track 'link' column for later use
tracked_links = data_cleaned['link'].tolist()
