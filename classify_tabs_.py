import json
from pathlib import Path
import typing

import yaml
from muutils.json_serialize import json_serialize  # type: ignore[import]

from generate_continuation import generate_continuation
from preprocess_urls import get_url_meta
from bookmark_utils import Bookmark, BookmarkFolder, load_bookmarks, load_urls

def classify_single(
    base_prompt_file: Path | str = Path("data/prompt.yaml"),
    url: str = "https://arxiv.org/pdf/2212.07677.pdf",
    max_length: int = 30,
) -> list[str]:

    if not isinstance(base_prompt_file, Path):
        base_prompt_file = Path(base_prompt_file)

    if not base_prompt_file.exists():
        raise ValueError(
            f"Base prompt file {base_prompt_file.absolute} does not exist."
        )

    prompt: str = generate_prompt(url, base_prompt_file.read_text())
    # print(prompt)
    continuation: str = generate_continuation(
        prompt, max_length=max_length, stop_token="]"
    )

    tags: list[str] = extract_tags(continuation)

    return tags

def classify_from_file(
    urls_file: str,
    base_prompt_file: Path = Path("data/prompt.yaml"),
    max_length: int = 30,
    output_format: typing.Literal["json", "yaml", "yml"] = "yml",
    input_format: typing.Literal["txt", "json", "html", None] = None,
    sparse_output: bool = True,
) -> None:
    """prints output to console"""

    # deal with prompt
    if not isinstance(base_prompt_file, Path):
        base_prompt_file = Path(base_prompt_file)

    if not base_prompt_file.exists():
        raise ValueError(
            f"Base prompt file {base_prompt_file.absolute} does not exist."
        )

    base_prompt: str = base_prompt_file.read_text(encoding="utf-8")
    
    # load data to classify
    bkmks: BookmarkFolder = load_bookmarks(
        fname=urls_file,
        input_format=input_format,
    )


    # classify
    classified: list[Bookmark] = list()
    for bk in bkmks.iter_bookmarks():
        
        # get the tags
        prompt: str = generate_prompt(url=bk.href, base_prompt=base_prompt)
        continuation: str = generate_continuation(
            prompt, max_length=max_length, stop_token="]"
        )
        tags: list[str] = extract_tags(continuation)

        # store
        bk.tags = tags
        classified.append(bk)

    # output
    output_temp: list[dict] = json_serialize(classified)
    output: list[dict] = list()
    bkd: dict
    if sparse_output:
        for bkd in output_temp:
            output.append(dict(
                title=bkd["title"],
                href=bkd["href"],
                tags=bkd["tags"],
            ))
    else:
        output = output_temp

    if output_format == "json":
        print(json.dumps(output, indent=2))
    elif output_format in ["yaml", "yml"]:
        print(yaml.dump(output, sort_keys=False))


def generate_prompt(url: str, base_prompt: str):
    # have to wrap in a list to make sure it's the same format as the base_prompt
    # TODO tidy this up
    metadata: list[dict] = [get_url_meta(url)]
    url_prompt: str = yaml.dump(metadata, sort_keys=False)
    return base_prompt.strip() + "\n" + url_prompt + "  tags: ["


def extract_tags(continuation: str) -> list[str]:
    return continuation.split(", ")


if __name__ == "__main__":
    import fire # type: ignore[import]

    fire.Fire(dict(
        single=classify_single,
        file=classify_from_file,
    ))
