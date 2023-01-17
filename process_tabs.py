import json
import requests
import re
import typing

from bs4 import BeautifulSoup
import openai
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
	"""preprocess URL according to certain rules (using regex)
	
	- `*arxiv.org/pdf/NNNN.pdf` -> `*arxiv.org/abs/NNNN`
	- `twitter.com` -> `nitter.net`
	"""
	# match group of digits and decimal point
	match_arxiv = re.search(r'arxiv\.org/pdf/(\d+\.\d+)\.pdf', url)
	# math any text after `twitter.com/`
	match_twitter = re.search(r'twitter\.com/(.+)', url)
	if match_arxiv:
		return f"https://arxiv.org/abs/{match_arxiv.group(1)}"
	elif match_twitter:
		return f"https://nitter.net/{match_twitter.group(1)}"
	else:
		return url


def get_arxiv_meta(soup: BeautifulSoup) -> dict:
	"""get meta data from an arxiv URL. returns a dict"""
	output: dict = dict()
	# get the submission date, author list, subjects, and author list
	# submission date
	submission_date_raw: str = bs_find_text(soup, 'div', class_="dateline")
	# process: "[Submitted on 24 May 2022 (<a href="https://arxiv.org/abs/2205.12411v1">v1</a>), last revised 9 Jul 2022 (this version, v4)]"
	# -> {"submitted": "24 May 2022", "revised": "9 Jul 2022"}
	submission_date_re = re.search(r'\[(.+)\]', submission_date_raw)
	if submission_date_re:
		try:
			submission_date_str: str = submission_date_re.group(1)
			output["submitted"] = dateparser.parse(
				re.search(r'Submitted on (.+?) \(', submission_date_str).group(1)
			).strftime("%Y-%m-%d")
		except AttributeError:
			# if the regex fails, just use the raw string
			output["dates"] = submission_date_raw
		
		try:
			output["revised"] = dateparser.parse(
				re.search(r'last revised (.+?) \(this', submission_date_str).group(1)
			).strftime("%Y-%m-%d")
		except AttributeError:
			pass
	
	# author list
	author_list = bs_find_text(soup, 'div', class_="authors")
	output["author_list"] = [
		name.strip() 
		for name in
		author_list.removeprefix("Authors:  ").split(",")
	]

	# subjects
	subjects = bs_find_text(soup, 'td', class_="tablecell subjects")
	output["subjects"] = [
		x.strip()
		for x in subjects.split(";")
	]

	# abstract
	abstract = bs_find_text(soup, 'blockquote', class_="abstract mathjax")
	output["abstract"] = abstract.removeprefix("Abstract:  ").strip().replace("\n", " ")

	return output
	


def get_url_meta(url: str) -> dict:
	url: str = preprocess_url(url)
	response: requests.Response = requests.get(url)
	soup: BeautifulSoup|None = BeautifulSoup(response.text, 'html.parser')

	title_obj = bs_find_text(soup, 'title')
	title: str|None = None
	if title_obj is not None:
		title = title_obj

	output: dict = dict(
		url = url,
		title = title,
		headings = [heading.get_text().strip() for heading in soup.find_all(['h1'])],
	)

	if "arxiv.org/abs/" in url:
		# remove the "headings" key
		del output["headings"]

		output.update(get_arxiv_meta(soup))
		

	return output

# def gpt_classify_meta(meta: dict) -> list[str]:
# 	"""classify URL meta using GPT-3. returns a list of tags"""

def process_urls(file: str, format: typing.Literal['json', 'yaml', 'yml']) -> str:
	"""process a file of URLs and print to stdout a yaml file with the meta data"""
	with open(file) as f:
		urls: list[str] = [line.strip() for line in f.readlines()]
	
	# get meta data and print as yaml
	meta: list[dict] = list()
	# each item is a url
	for url in tqdm(urls, unit="url"): 
		meta.append(get_url_meta(url))

	# enforce this key order: url, title, headings
	if format == 'json':
		print(json.dumps(meta, indent="  "))
	elif format in ['yaml', 'yml']:
		print(yaml.dump(meta, sort_keys=False))
	

if __name__ == "__main__":
	import fire
	fire.Fire(process_urls)

