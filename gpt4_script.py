import json
import requests
from collections import defaultdict
from bs4 import BeautifulSoup
import openai
import fire
import numpy as np
from typing import List, Dict

# Replace with your OpenAI API key
openai.api_key = 'your-api-key'

def get_text_from_url(url: str) -> str:
    response = requests.get(url)
    soup = BeautifulSoup(response.content, 'html.parser')
    return ' '.join(soup.stripped_strings)

def get_embedding(text: str) -> List[float]:
    embeddings = openai.Embedding.create(texts=[text], model = "text-embedding-ada-002").get('data')
    return embeddings[0]['embeddings']

def get_summary(text: str) -> str:
    response = openai.Completion.create(
        model='text-davinci-002',
        prompt=f'Summarize the content of the following text in one sentence: {text}',
        max_tokens=50,
        n=1,
        stop=None
    )
    return response.choices[0].text.strip()

def classify_url(embedding: List[float], tag_embeddings: Dict[str, List[float]]) -> str:
    best_match = None
    best_similarity = float('-inf')

    for tag, tag_embedding in tag_embeddings.items():
        similarity = np.dot(embedding, tag_embedding) / (np.linalg.norm(embedding) * np.linalg.norm(tag_embedding))
        if similarity > best_similarity:
            best_similarity = similarity
            best_match = tag

    return best_match

def process_urls(urls_filename: str, tag_embeddings_filename: str, output_filename: str) -> None:
    # Load the URLs received from the browser extension
    with open(urls_filename, 'r') as f:
        urls = json.load(f)

    # Load the existing embeddings for a set of tags
    with open(tag_embeddings_filename, 'r') as f:
        tag_embeddings = json.load(f)

    results = defaultdict(list)

    for url in urls:
        # Get the plain text from the URL
        text = get_text_from_url(url)

        # Get the GPT embedding for the text
        embedding = get_embedding(text)

        # Classify the text
        tag = classify_url(embedding, tag_embeddings)

        # Generate a summary for the text
        summary = get_summary(text)

        # Add the URL and summary under the appropriate tag
        results[tag].append({
            'url': url,
            'summary': summary
        })

    # Save the results to a JSON file
    with open(output_filename, 'w') as f:
        json.dump(results, f, indent=2)

def embed_tagged_urls(input_filename: str, output_filename: str) -> None:
    with open(input_filename, 'r') as f:
        tagged_urls = json.load(f)

    tag_embeddings = defaultdict(list)

    for item in tagged_urls:
        url = item['url']
        tag = item['tag']

        text = get_text_from_url(url)
        embedding = get_embedding(text)
        tag_embeddings[tag] = embedding

    with open(output_filename, 'w') as f:
        json.dump(tag_embeddings, f, indent=2)

def main():
    fire.Fire({
        'process_urls': process_urls,
        'embed_tagged_urls': embed_tagged_urls
    })

if __name__ == '__main__':
    main()