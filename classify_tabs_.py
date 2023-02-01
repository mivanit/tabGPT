from pathlib import Path

import yaml

from generate_continuation import generate_continuation
from preprocess_urls import get_url_meta


def main(
    base_prompt_file: Path | str = Path("data/prompt.yaml"),
    url: str = "https://arxiv.org/pdf/2212.07677.pdf",
    max_length: int = 30,
):

    if not isinstance(base_prompt_file, Path):
        base_prompt_file = Path(base_prompt_file)

    if not base_prompt_file.exists:
        raise ValueError(
            f"Base prompt file {base_prompt_file.absolute} does not exist."
        )

    prompt: str = generate_prompt(url, base_prompt_file)
    # print(prompt)
    continuation: str = generate_continuation(
        prompt, max_length=max_length, stop_token="]"
    )

    tags: list[str] = extract_tags(continuation)

    return tags


def generate_prompt(url: str, base_prompt_file: Path):
    # have to wrap in a list to make sure it's the same format as the base_prompt
    # TODO tidy this up
    metadata: list[dict] = [get_url_meta(url)]

    base_prompt: str = base_prompt_file.read_text()
    url_prompt: str = yaml.dump(metadata, sort_keys=False)

    return base_prompt.strip() + "\n" + url_prompt + "  tags: ["


def extract_tags(continuation: str) -> list[str]:
    return continuation.split(", ")


if __name__ == "__main__":
    import fire

    fire.Fire(main)
