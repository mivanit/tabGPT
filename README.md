# tabGPT

_use GPT to classify a bunch of your open tabs!_

## General usage

1. Install [Poetry](https://python-poetry.org/docs/)
1. Install project dependencies in new virtualenv:

    ```poetry install```

## `bookmark_utils.py`

Parse bookmarks file to [BookmarkFolder] class and serialize to JSON.

### Usage

1. Export bookmarks to an HTML file. Instructions:
    * [Firefox](https://support.mozilla.org/en-US/kb/export-firefox-bookmarks-to-backup-or-transfer)
1. Run bookmark_utils

    ```poetry run python bookmark_utils.py path/to/bookmarks.html```
