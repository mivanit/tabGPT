from pathlib import Path

import yaml

from generate_continuation import generate_continuation
from preprocess_urls import get_url_meta


def main():
    base_prompt_file = Path("data/prompt.yaml")
    url = "https://arxiv.org/pdf/2212.07677.pdf"

    if not base_prompt_file.exists:
        raise ValueError(
            f"Base prompt file {base_prompt_file.absolute} does not exist."
        )

    prompt = generate_prompt(url, base_prompt_file)
    print(prompt)
    continuation = generate_continuation(prompt, max_length=30, stop_token="]")

    tags = extract_tags(continuation)
    print(f"Tags for {url}: {tags}")


def generate_prompt(url: str, base_prompt_file: Path):
    # have to wrap in a list to make sure it's the same format as the base_prompt
    # TODO tidy this up
    metadata = [get_url_meta(url)]

    base_prompt = base_prompt_file.read_text()
    url_prompt = yaml.dump(metadata, sort_keys=False)

    return base_prompt.strip() + "\n" + url_prompt + "  tags: ["


def extract_tags(continuation: str):
    return continuation.split(", ")


if __name__ == "__main__":
    main()
