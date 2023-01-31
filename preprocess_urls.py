import json
import re
import sys
import typing

import dateparser
import requests
import yaml
from bs4 import BeautifulSoup  # type: ignore[import]
from tqdm import tqdm

from bookmark_utils import Bookmark, BookmarkFolder

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
        return ""
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


def get_url_meta(url: str, do_except: bool = False) -> dict:
    url = preprocess_url(url)
    url_fmt: str = f"http://{url}"

    try:
        response: requests.Response = requests.get(url_fmt)
    except (
        requests.exceptions.ConnectionError,
        requests.exceptions.InvalidURL,
        ValueError,
    ) as e:
        print(f"with url:\n{url_fmt}\nerror: {e}", file=sys.stderr)
        if do_except:
            raise e

        return dict(url=url, error=True)

    soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")

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


def process_urls(
    fname: str,
    output_format: typing.Literal["json", "yaml", "yml"] = "yml",
    input_format: typing.Literal["txt", "json", None] = None,
    do_except: bool = False,
):
    """process a file of URLs and print to stdout a yaml file with the meta data
    Parameters:
      file (str): json or txt file
      output_format: format to use when writing the output
    """

    urls: list[str]
    if input_format is None:
        # guess input format
        if fname.endswith(".json"):
            input_format = "json"
        elif fname.endswith(".txt"):
            input_format = "txt"
        else:
            raise ValueError(f"can't infer format of file {fname}")

    with open(fname) as f:
        if input_format == "txt":
            urls = [line.strip() for line in f.readlines()]
        elif input_format == "json":
            bkmks: BookmarkFolder = BookmarkFolder.load(json.load(f))
            urls = [b.href for b in bkmks.iter_bookmarks()]
        else:
            raise ValueError(f"Unknown input format: {input_format}")

    # get meta data and print as yaml
    meta: list[dict] = list()
    # each item is a url
    for url in tqdm(urls, unit="url"):
        meta.append(get_url_meta(url, do_except=do_except))

    # enforce this key order: url, title, headings
    if output_format == "json":
        print(json.dumps(meta, indent="  "))
    elif output_format in ["yaml", "yml"]:
        print(yaml.dump(meta, sort_keys=False))


if __name__ == "__main__":
    import fire  # type: ignore[import]

    fire.Fire(process_urls)
