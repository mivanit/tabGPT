import json
import requests
import re
import typing

from bs4 import BeautifulSoup
import yaml
from tqdm import tqdm
import dateparser

# OPENAI_KEY: str = open('OPENAI_KEY.txt').read().strip()

PROMPT_FORMAT: str = """# classification of urls according to category. can include multiple tags, and nested tags. 
# for example, `` or ``
tags:
 - research/interpretability
 - research/ethics
 - research/capabilities
 - philosophy
 - fiction
 - 
 - misc 
"""


def bs_find_text(soup: BeautifulSoup, *args, **kwargs) -> str:
    """find text in a BeautifulSoup object. kwargs are passed to `bs_find_text(soup, )`"""
    temp = soup.find(*args, **kwargs)
    if temp is None:
        return None
    else:
        return temp.get_text().strip()


def preprocess_url(url: str) -> str:
    """preprocess URL according to certain rules

    - `*arxiv.org/pdf/NNNN.pdf` -> `*arxiv.org/abs/NNNN`
    - `twitter.com` -> `nitter.net`
    """
    # remove http prefix (provides no info, wastes tokens)
    url = url.removeprefix("http://").removeprefix("https://")

    # match group of digits and decimal point
    m_arxiv = re.search(r"arxiv\.org/pdf/(\d+\.\d+)\.pdf", url)
    # math any text after `twitter.com/`
    m_twitter = re.search(r"twitter\.com/(.+)", url)
    if m_arxiv:
        return f"arxiv.org/abs/{m_arxiv.group(1)}"
    elif m_twitter:
        return f"nitter.net/{m_twitter.group(1)}"
    else:
        return url


def get_arxiv_meta(
    soup: BeautifulSoup,
    # filter_keys: typing.Callable[[str], bool] = lambda k : True,
    filter_keys: typing.Callable[[str], bool] = lambda k: k
    in ("title", "url", "subjects"),
) -> dict:
    """get metadata from an arxiv URL. returns a dict"""
    output: dict = dict(
        authors=list(),
    )

    # use the meta tags for basic citation info
    meta_tags: list[BeautifulSoup] = soup.find_all("meta")
    for tag in meta_tags:
        match tag.get("name"):
            case "citation_title":
                output["title"] = tag.get("content")
            case "citation_author":
                output["authors"].append(tag.get("content"))
            case "citation_date":
                output["submitted"] = tag.get("content").replace("/", "-")
            case "citation_online_date":
                output["revised"] = tag.get("content").replace("/", "-")
            case "citation_abstract":
                output["abstract"] = tag.get("content").replace("\n", " ")

    # subjects need to be extracted from the table
    subjects = bs_find_text(soup, "td", class_="tablecell subjects")
    output["subjects"] = [x.strip() for x in subjects.split(";")]

    return {k: v for k, v in output.items() if filter_keys(k)}


def get_url_meta(url: str) -> dict:
    url: str = preprocess_url(url)
    response: requests.Response = requests.get(f"http://{url}")
    soup: BeautifulSoup | None = BeautifulSoup(response.text, "html.parser")

    title_obj = bs_find_text(soup, "title")
    title: str | None = None
    if title_obj is not None:
        title = title_obj

    output: dict = dict(
        url=url,
        title=title,
        headings=[heading.get_text().strip() for heading in soup.find_all(["h1"])],
    )

    if "arxiv.org/abs/" in url:
        # remove the "headings" key
        del output["headings"]

        output.update(get_arxiv_meta(soup))

    elif len(output["headings"]) == 0:
        del output["headings"]

    return output


# def gpt_classify_meta(meta: dict) -> list[str]:
# 	"""classify URL meta using GPT-3. returns a list of tags"""

def process_urls(file: str, format: typing.Literal["json", "yaml", "yml"]) -> str:
    """process a file of URLs and print to stdout a yaml file with the meta data
    Parameters:
      file (str): a file with 1 URL on each line
      output_format: format to use when writing the output
    """
    with open(file) as f:
        urls: list[str] = [line.strip() for line in f.readlines()]

    # get meta data and print as yaml
    meta: list[dict] = list()
    # each item is a url
    for url in tqdm(urls, unit="url"):
        meta.append(get_url_meta(url))

    # enforce this key order: url, title, headings
    if format == "json":
        print(json.dumps(meta, indent="  "))
    elif format in ["yaml", "yml"]:
        print(yaml.dump(meta, sort_keys=False))

if __name__ == "__main__":
    import fire

    fire.Fire(process_urls)
