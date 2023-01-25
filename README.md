# tabGPT

_Use GPT to classify a bunch of your open tabs!_

## Usage

### Initial Setup

1. Install [Poetry](https://python-poetry.org/docs/)
1. Install project dependencies in new virtualenv:

    ```poetry install```

### bookmark_utils

Parse bookmarks file to BookmarkFolder class and serialize to JSON.

1. Export bookmarks to an HTML file. Instructions:
    * [Firefox](https://support.mozilla.org/en-US/kb/export-firefox-bookmarks-to-backup-or-transfer)
1. Run bookmark_utils

    ```poetry run python bookmark_utils.py path/to/bookmarks.html```


### clasify_tabs

TODO: description

#### Default input

1. Run classify_tabs

    ```poetry run python classify_tabs.py gen```

#### Custom input

1. Write some sample text to a file `temp.txt` in the project directory

1. Run classify_tabs:

   ```poetry run python classify_tabs.py gen_file```
