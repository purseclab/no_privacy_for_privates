import praw
import pandas as pd
from openai import OpenAI


# --- Credentials (replace placeholders before running) ---
OPENAI_API_KEY = "YOUR_OPENAI_API_KEY"


def generate_decision_GPT(description):
    '''
    Input: concatenated Reddit text (title + body + comments)
    Description: asks the model whether the text mentions any apps
    Output: comma-separated app name(s), or "0" if none
    '''

    # Create the OpenAI client (falls back to OPENAI_API_KEY env var if unset)
    client = OpenAI(
        api_key=OPENAI_API_KEY,
    )

    # System prompt: instruct the model to extract app names or return 0
    sys_prompt = '''
      "" You are given a reddit post's title, text and comments
      concatenated. Please find if the given texts are talking about some apps.
      If the posts/comments talk about some particular app/apps, please return
      the name of those apps separated by comma, otherwise, return 0.""
    '''

    prompt = description

    # Build the chat messages: system instruction + user-supplied text
    messages = [
        {"role": "system", "content": sys_prompt},
        {"role": "user", "content": prompt}
    ]

    # Call the chat completion API
    response = client.chat.completions.create(
        model=             'gpt-4-turbo',  # Specify the model
        messages=messages,  # Your input messages
        max_tokens=1024,  # Max number of tokens in the output
        temperature=0.9,  # Controls the randomness of the output
        top_p=0.9,  # Controls diversity via nucleus sampling
        n=1,  # Number of completions to generate
        stop=None  # Sequence where the API will stop generating further tokens
    )

    return response.choices[0].message.content.strip()


# --- Load the input spreadsheet and select the slice of rows to process ---
file_path = '../input/YOUR_INPUT_FILE.xlsx'  # replace with your input spreadsheet
data = pd.read_excel(file_path)
print(data.columns, data.shape)
data = data[1000:2000]  # process rows 1000-1999 in this run
print(data.head(5), data.shape)

# --- Reddit API credentials (replace placeholders before running) ---
client_id = 'YOUR_REDDIT_CLIENT_ID'
client_secret = 'YOUR_REDDIT_CLIENT_SECRET'
user_agent = 'YOUR_REDDIT_USER_AGENT'

# Create a Reddit instance
reddit = praw.Reddit(client_id=client_id,
                     client_secret=client_secret,
                     user_agent=user_agent)


def process_value(val):
    # Skip image URLs — there is no text to analyze
    if('.jpeg' in val or '.png' in val or '.jpg' in val):
        return 'image url, couldn\'t process'

    # Skip anything that isn't a reddit.com link
    if('www.reddit.com' not in val):
        return 'url not valid'

    print('processing ', val)

    # Fetch the submission and pull out its title and body text
    submission = reddit.submission(url=val)
    title = ''
    if submission.title:
        title = submission.title

    text = ''
    if submission.selftext:
        text = submission.selftext
    comments = ""

    # Expand all comment trees and concatenate every comment body
    submission.comments.replace_more(limit=None)
    for comment in submission.comments.list():
        comments+=comment.body
        comments+="\n"

    # Combine title, text, and comments into a single string for the model
    res_str = title
    res_str += "\n"
    res_str += text
    res_str += "\n"
    res_str += comments

    # Ask the model whether this post mentions any apps
    resp = generate_decision_GPT(res_str)
    return resp

# Prepare the output frame with an extra column for the model's verdict
all_cols = list(data.columns)
all_cols.append('app_exists')

data_new = pd.DataFrame(columns=all_cols)

# Process each row, appending the result and checkpointing to disk each time
for _, row in data.iterrows():
    res_reddit = ''
    try:
        res_reddit = process_value(row['URL'])
    except Exception as e:
        res_reddit = "error when processing"
        print(f"error processing {row['URL']}: {e}")

    new_row = row.to_dict()  # Convert the original row to a dictionary
    new_row['app_exists'] = res_reddit  # Add the new column
    data_new = pd.concat([data_new, pd.DataFrame([new_row])], ignore_index=True)
    data_new.to_excel('YOUR_OUTPUT_FILE.xlsx', index=False)  # incremental save; replace with your output filename


print(data_new.head())
