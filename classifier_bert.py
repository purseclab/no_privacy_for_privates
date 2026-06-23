import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report
from transformers import AutoTokenizer, AutoModelForSequenceClassification, AdamW, get_scheduler
from torch.utils.data import Dataset, DataLoader
import torch
import os
from tqdm import tqdm



file_path = '../input/search-results-master-v2.xlsx'  # Update this path if needed
data = pd.read_excel(file_path)
# exit()

# Clean and preprocess the data
data = data.dropna(subset=['Accurate [No, Yes, ?] '])
data['accurate_converted'] = data['Accurate [No, Yes, ?] '].map({'Yes': 1, 'No': 0})
data = data.dropna(subset=['accurate_converted'])
# print(data['accurate_converted'].unique())
# print(data['accurate_converted'])
# print(str(data[data['accurate_converted'].isna()]['link']))
# data.to_csv('check_nan.csv', index=False)
# print(len(data))
# exit()
# Split into train/test
print("Splitting data into train and test")

train_data, test_data = train_test_split(
    data, test_size=0.2, stratify=data['accurate_converted'], random_state=42
)


# === Step 2: Define the Dataset Class ===
class TextDataset(Dataset):
    def __init__(self, texts, labels, tokenizer, max_length):
        self.texts = texts
        self.labels = labels
        self.tokenizer = tokenizer
        self.max_length = max_length

    def __len__(self):
        return len(self.texts)

    def __getitem__(self, idx):
        text = self.texts[idx]
        label = self.labels[idx]
        encoding = self.tokenizer(
            text,
            max_length=self.max_length,
            padding="max_length",
            truncation=True,
            return_tensors="pt",
        )
        return {
            "input_ids": encoding["input_ids"].squeeze(0),
            "attention_mask": encoding["attention_mask"].squeeze(0),
            "label": torch.tensor(label, dtype=torch.long),
        }

# Initialize tokenizer
tokenizer = AutoTokenizer.from_pretrained("bert-base-uncased")
max_length = 512

# Prepare datasets
train_dataset = TextDataset(
    train_data['description'].tolist(),
    train_data['accurate_converted'].astype(int).tolist(),
    tokenizer,
    max_length,
)
test_dataset = TextDataset(
    test_data['description'].tolist(),
    test_data['accurate_converted'].astype(int).tolist(),
    tokenizer,
    max_length,
)

# === Step 3: Initialize Model, Optimizer, and Scheduler ===
num_labels = 2
model = AutoModelForSequenceClassification.from_pretrained(
    "bert-base-uncased",
    num_labels=num_labels,
)

train_loader = DataLoader(train_dataset, batch_size=16, shuffle=True)
test_loader = DataLoader(test_dataset, batch_size=16)

optimizer = AdamW(model.parameters(), lr=5e-5)
num_training_steps = len(train_loader) * 3  # 3 epochs
lr_scheduler = get_scheduler(
    "linear", optimizer=optimizer, num_warmup_steps=0, num_training_steps=num_training_steps
)

# === Step 4: Training the Model ===
device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
model.to(device)

loss_fn = torch.nn.CrossEntropyLoss()
epochs = 3

for epoch in range(epochs):
    model.train()
    progress_bar = tqdm(train_loader, desc=f"Epoch {epoch + 1}")
    for batch in progress_bar:
        optimizer.zero_grad()

        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["label"].to(device)

        outputs = model(input_ids, attention_mask=attention_mask, labels=labels)
        loss = outputs.loss
        loss.backward()
        optimizer.step()
        lr_scheduler.step()

        progress_bar.set_postfix(loss=loss.item())

# === Step 5: Evaluate the Model ===
model.eval()
predictions, true_labels = [], []

with torch.no_grad():
    for batch in test_loader:
        input_ids = batch["input_ids"].to(device)
        attention_mask = batch["attention_mask"].to(device)
        labels = batch["label"].to(device)

        outputs = model(input_ids, attention_mask=attention_mask)
        logits = outputs.logits
        preds = torch.argmax(logits, dim=-1)

        predictions.extend(preds.cpu().numpy())
        true_labels.extend(labels.cpu().numpy())

print(classification_report(true_labels, predictions, target_names=["No", "Yes"]))

# === Step 6: Save the Model ===
save_directory = "./bert_model"
os.makedirs(save_directory, exist_ok=True)

model.save_pretrained(save_directory)
tokenizer.save_pretrained(save_directory)

print(f"Model and tokenizer saved to {save_directory}")

# === Step 7: Load and Use the Model for Inference ===
loaded_model = AutoModelForSequenceClassification.from_pretrained(save_directory)
loaded_tokenizer = AutoTokenizer.from_pretrained(save_directory)
loaded_model.to(device)

new_text = ["This is an example sentence for testing the model."]
inputs = loaded_tokenizer(
    new_text, max_length=512, padding="max_length", truncation=True, return_tensors="pt"
)
inputs = {key: val.to(device) for key, val in inputs.items()}

loaded_model.eval()
with torch.no_grad():
    outputs = loaded_model(**inputs)
    logits = outputs.logits
    predicted_class = torch.argmax(logits, dim=-1)

print(f"Predicted class: {predicted_class.item()}")