import json
import re
import sys
import typing
from dataclasses import dataclass, field

import dateparser
import rake_nltk
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


@dataclass(kw_only=True)
class UrlPreprocessor:
    """class for preprocessing URLs, such as twitter.com -> nitter.net"""

    check: typing.Callable[[str], bool]
    process: typing.Callable[[str], str]
    name: str | None = None


# TODO: precompiling regexes would be faster
URL_PREPROCESSORS: list[UrlPreprocessor] = [
    UrlPreprocessor(
        check=lambda url: re.search(r"arxiv\.org/pdf/(\d+\.\d+)\.pdf", url) is not None,
        process=lambda url: re.sub(
            r"arxiv\.org/pdf/(\d+\.\d+)\.pdf", r"arxiv.org/abs/\1", url
        ),
        name="arxiv",
    ),
    UrlPreprocessor(
        check=lambda url: re.search(r"twitter\.com/(.+)", url) is not None,
        process=lambda url: re.sub(r"twitter\.com/(.+)", r"nitter.net/\1", url),
        name="twitter",
    ),
]


def preprocess_url(url: str) -> str:
    """preprocess URL according to certain rules

    - `*arxiv.org/pdf/NNNN.pdf` -> `*arxiv.org/abs/NNNN`
    - `twitter.com` -> `nitter.net`
    """
    # remove http prefix (provides no info, wastes tokens)
    url = url.removeprefix("http://").removeprefix("https://")

    for preprocessor in URL_PREPROCESSORS:
        if preprocessor.check(url):
            url = preprocessor.process(url)
            break

    return url


@dataclass(kw_only=True)
class MetaExtractor:
    """extract metadata from a url/soup, like getting citation info from arxiv.org"""

    check: typing.Callable[[str, BeautifulSoup], bool]
    extract: typing.Callable[[str, BeautifulSoup], dict]
    name: str | None = None


def get_meta_arxiv(
    url: str,
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


def get_meta_fallback(
    url: str,
    soup: BeautifulSoup,
    kw_thresh: float = 1.0,
    kw_max_count: int = 10,
    kw_total_len_max: int = 500,
) -> dict:
    """fallback for getting metadata from a URL. returns a dict

    dict contains:
    - headings: list of h1 headings, if nonempty
    - keywords: list of keywords from text
    """
    # extract headings
    headings: list[str] = [
        heading.get_text().strip() for heading in soup.find_all(["h1"])
    ]

    # get keywords from the main text
    alltext: str = soup.get_text()
    r: rake_nltk.Rake = rake_nltk.Rake()
    r.extract_keywords_from_text(alltext)
    keywords_scored: list[tuple[float, str]] = r.get_ranked_phrases_with_scores()

    # filter keywords to shorten length
    keywords: list[str] = [
        keyword for score, keyword in keywords_scored if score >= kw_thresh
    ][:kw_max_count]

    while sum(len(k) for k in keywords) > kw_total_len_max:
        keywords.pop()

    # assemble output and return
    output: dict = dict(
        headings=headings,
        keywords=keywords,
    )

    if len(headings) == 0:
        del output["headings"]

    return output


META_EXTRACTORS: list[MetaExtractor] = [
    MetaExtractor(
        check=lambda url, soup: re.search(r"arxiv\.org/abs/(\d+\.\d+)", url)
        is not None,
        extract=get_meta_arxiv,
        name="arxiv",
    ),
    MetaExtractor(
        check=lambda url, soup: True,
        extract=get_meta_fallback,
        name="fallback",
    ),
]


def get_url_meta(url: str, do_except: bool = False) -> dict:
    """given a url, processes it and then gets metadata"""

    # preprocess
    url = preprocess_url(url)
    url_fmt: str = f"http://{url}"

    # get html
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

    # parse basics
    soup: BeautifulSoup = BeautifulSoup(response.text, "html.parser")

    title_obj = bs_find_text(soup, "title")
    title: str | None = None
    if title_obj is not None:
        title = title_obj

    output: dict = dict(
        url=url,
        title=title,
    )

    # run individual extractors
    for extractor in META_EXTRACTORS:
        if extractor.check(url, soup):
            output.update(extractor.extract(url, soup))
            break

    return output


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
