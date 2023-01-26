# tabGPT

_Use GPT to classify a bunch of your browser tabs!_

## Setup

* Install [PyTorch](https://pytorch.org/get-started/locally/) to your global python
* Create venv and allow it to access global packages

    ```python -m venv venv --system-site-packages```
* Activate venv

    ```source venv/bin/activate```
* Install dependencies

    ```pip install -r requirements.txt```

### bookmark_utils

Parse bookmarks file to BookmarkFolder class and serialize to JSON. Print result to STDOUT.

1. Export bookmarks to an HTML file. Instructions:
    * [Firefox](https://support.mozilla.org/en-US/kb/export-firefox-bookmarks-to-backup-or-transfer)
1. Run bookmark_utils

    ```python bookmark_utils.py path/to/bookmarks.html```

### preprocess_urls.py

Process a file of URLs and print to stdout a file with the metadata. Input file should contain one URL per line.

1. Export tabs to a file
    * Firefox: use [Export Tab URLs](https://addons.mozilla.org/en-GB/firefox/addon/export-tabs-urls-and-titles/) extension
1. Run preprocess_urls

    ```python preprocess_urls.py path/to/tabs_file.txt --output_format=[json|yaml|yml]```

### clasify_tabs

Currently this file does not classify tabs. It generates the next tokens in a sequence.

#### Input from command line

1. Run classify_tabs

    ```python3 classify_tabs.py gen "lorem ipsum"```

#### Input from file

1. Write some sample text to a file `temp.txt` in the project directory

1. Run classify_tabs:

   ```poetry run python classify_tabs.py gen_file```

