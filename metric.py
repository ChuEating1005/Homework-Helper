import openai
import os
import pandas as pd
from dotenv import load_dotenv
import numpy as np
from scipy.spatial.distance import cosine
from sentence_transformers import SentenceTransformer

# Set your OpenAI API key
load_dotenv()
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
model_list = ["text-embedding-3-small", "all-MiniLM-L6-v2"]
model = model_list[int(input("Choose a model:\n1. text-embedding-3-small\n2. all-MiniLM-L6-v2\n"))-1]
openai.api_key = OPENAI_API_KEY

df = pd.read_csv("test_branch.csv")
questions = df['Question'].tolist()
correct_answer = df['Correct Answer'].tolist()
baseline_answer = df['Baseline'].tolist()
dataset_answer = df['Dataset'].tolist()
num_test = len(correct_answer)


def get_embedding(text, model="text-embedding-3-small"):
    if model == "text-embedding-3-small":
        response = openai.Embedding.create(
            input=text,
            model=model
        )
        return response['data'][0]['embedding']
    else:
        return model.encode(text)

def cosine_similarity(vec1, vec2):
    return 1 - cosine(vec1, vec2)


for i in range(num_test):
    correct_embedding = get_embedding(correct_answer[i], model)
    baseline_embedding = get_embedding(baseline_answer[i], model)
    dataset_embedding = get_embedding(dataset_answer[i], model)

    similarity_baseline = round(cosine_similarity(correct_embedding, baseline_embedding), 5)
    similarity_dataset = round(cosine_similarity(correct_embedding, dataset_embedding), 5)

    print(f"{questions[i]}")
    print(f"Answer with Baseline, Metric: {similarity_baseline}")
    print(f"Answer with Dataset, Metric: {similarity_dataset}")
    print()
