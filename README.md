# tabGPT

_Use GPT to classify a bunch of your browser tabs!_


# scripts

## bookmark_utils

Parse bookmarks file to BookmarkFolder class and serialize to JSON. Print result to STDOUT.

1. Export bookmarks to an HTML file. Instructions:
    * [Firefox](https://support.mozilla.org/en-US/kb/export-firefox-bookmarks-to-backup-or-transfer)
1. Run bookmark_utils

    ```python bookmark_utils.py path/to/bookmarks.html```

## preprocess_urls.py

Process a file of URLs and print to stdout a file with the metadata. Input file should contain one URL per line.

1. Export tabs to a file
    * Firefox: use [Export Tab URLs](https://addons.mozilla.org/en-GB/firefox/addon/export-tabs-urls-and-titles/) extension
1. Run preprocess_urls

    ```python preprocess_urls.py path/to/tabs_file.txt --output_format=[json|yaml|yml]```

## clasify_tabs

Currently this file does not classify tabs. It generates the next tokens in a sequence.

- generate continuation from command line:
    ```python classify_tabs.py gen "lorem ipsum"```

- generate continuation from a file `prompt.txt`:
    ```python classify_tabs.py gen_file ```
   


# Roadmap

- [ ] basic prompted prototype
    - [x] basic extraction of page metadata given a URL
    - [x] parsing of bookmark files
    - [ ] small set of manually classified data
    - [ ] generation of prompts from manual data + tag list
    - [ ] extraction of tags from a generated response
- [ ] finetuned model
    - [ ] larger dataset -- augment via manual review of automated classification?
    - [ ] finetune GPT-2
- [ ] exporting of classified tabs -- input needed from users, below are simply a few ideas
    - export to [Dendron](https://www.dendron.so/) vault
    - export to Notion
    - re-add bookmarks to browser
- [ ] long-term
    - [ ] better metadata extraction (keywords via `nltk_rake`, etc)
    - [ ] compatibility with openAI API -- finetune GPT-3?
    - [ ] browser extension (probably will use openAPI, might be a separate project)


# Development

## Setup

* Install [PyTorch](https://pytorch.org/get-started/locally/) to your global python
* Create venv and allow it to access global packages

    ```python -m venv venv_path --system-site-packages```
* Activate venv

    ```source venv_path/bin/activate```
* Install dependencies

    ```pip install -r requirements.txt```


## Testing & Static analysis

- formatter (black) via `make format`
- mypy via `make mypy`
- all of the above via `make check`