"""reads a bookmark html export in the `<!DOCTYPE NETSCAPE-Bookmark-file-1>` browser format

I've checked, and firefox, edge, and vivaldi all use this format
"""

import json
import sys
import typing
import warnings
from dataclasses import asdict, dataclass, field
from typing import Iterator, List

from bs4 import BeautifulSoup, PageElement  # type: ignore[import]
from muutils.json_serialize import json_serialize  # type: ignore[import]

# pylint: disable=missing-class-docstring,pointless-string-statement,protected-access

_VERBOSE_WARN: bool = False


@dataclass(kw_only=True)
class Bookmark:
    title: str
    href: str
    add_date: int | None = None
    _parent: "BookmarkFolder|None" = field(default=None, repr=False, compare=False)
    tags: List[str] | None = None

    def serialize(self) -> dict:
        return dict(
            title=self.title,
            href=self.href,
            add_date=self.add_date,
            tags=self.tags,
        )

    @classmethod
    def load(cls, data: dict) -> "Bookmark":
        return cls(**data)


@dataclass
class BookmarkFolder:
    title: str
    add_date: int | None
    last_modified: int | None
    contents: list["Bookmark|BookmarkFolder"]
    _parent: "BookmarkFolder|None" = field(default=None, repr=False, compare=False)

    _being_serialized: bool = False

    def serialize(self) -> dict:
        if self._being_serialized:
            raise RuntimeError("recursive serialization")
        self._being_serialized = True
        return dict(
            title=self.title,
            add_date=self.add_date,
            last_modified=self.last_modified,
            contents=[x.serialize() for x in self.contents],
        )

    @classmethod
    def load(cls, data: dict | list) -> "BookmarkFolder":
        output: "BookmarkFolder"
        if isinstance(data, list):
            output = cls(
                title="_root",
                add_date=None,
                last_modified=None,
                contents=[
                    Bookmark.load(x) if "href" in x else BookmarkFolder.load(x)
                    for x in data
                ],
            )
        elif isinstance(data, dict):
            output = cls(
                title=data["title"],
                add_date=data["add_date"],
                last_modified=data["last_modified"],
                contents=[
                    Bookmark.load(x) if "href" in x else BookmarkFolder.load(x)
                    for x in data["contents"]
                ],
            )
        else:
            raise TypeError(f"invalid type {type(data)}")

        output.set_parents()
        return output

    def get_child(self, title: str) -> "Bookmark|BookmarkFolder":
        """get a child from `contents` by title"""
        for x in self.contents:
            if x.title == title:
                return x

        raise KeyError(f"no child with title {title}")

    def __getitem__(self, title: str) -> "Bookmark|BookmarkFolder":
        return self.get_child(title)

    def iter_bookmarks(self) -> Iterator[Bookmark]:
        for x in self.contents:
            if isinstance(x, Bookmark):
                yield x
            else:
                yield from x.iter_bookmarks()

    def count_bookmarks(self) -> int:
        """counts downstream bookmarks"""
        return sum(
            1 if isinstance(x, Bookmark) else x.count_bookmarks() for x in self.contents
        )

    def get_tree(self) -> dict:
        """gets only the downstream folder structure, not the bookmarks"""
        output: dict = dict()
        for x in self.contents:
            if isinstance(x, Bookmark):
                continue
            output[x.title] = x.get_tree()
        return output

    def set_parents(self) -> None:
        """sets the parent attribute of all children"""
        for x in self.contents:
            x._parent = self
            if isinstance(x, BookmarkFolder):
                x.set_parents()


def process_child(element: PageElement) -> Bookmark | BookmarkFolder | None:
    if element.name == "h3":

        bkfolder: BookmarkFolder = BookmarkFolder(
            title=element.string,
            add_date=element["add_date"] if "add_date" in element else None,
            last_modified=element["last_modified"]
            if "last_modified" in element
            else None,
            contents=list(),
        )

        child_elements = element.find_next_sibling("dl")

        # preserve order, and loop over both folders and bookmarks at once
        for child in child_elements.children:
            p: Bookmark | BookmarkFolder | None = process_child(child)
            if p is not None:
                p._parent = bkfolder
                bkfolder.contents.append(p)
            else:
                if _VERBOSE_WARN:
                    warnings.warn(f"skipping {child}")

        return bkfolder

    elif element.name == "dl":
        # we skip it, because the sibling dl element should be processed in `get_bookmark_folder`
        return None
    elif element.name == "a":
        return Bookmark(
            title=element.string,
            href=element["href"],
            add_date=element["add_date"],
        )
    else:
        if _VERBOSE_WARN:
            # print the name and raw html of the element
            warnings.warn(f"unexpected tag {element.name}\n{element[:1000]}")
            # raise ValueError(f"unexpected tag {element.name}")
            return None

    return None


def process_bookmark_file(data: str) -> BookmarkFolder:

    # this part is a hack: remove all <DT> and <p> tags, they are useless and complicate things
    data = (
        data.replace("<DT>", "")
        .replace("<dt>", "")
        .replace("<p>", "")
        .replace("<P>", "")
    )

    # parse the html
    soup: BeautifulSoup = BeautifulSoup(data, "html.parser")

    # the structure is now as follows:
    """<!DOCTYPE NETSCAPE-Bookmark-file-1>
    <META HTTP-EQUIV="Content-Type" CONTENT="text/html; charset=UTF-8">
    <TITLE>Bookmarks</TITLE>
    <H1>Bookmarks</H1>
    <DL>
        <H3 add_date="1624139022" last_modified="1674165683" PERSONAL_TOOLBAR_FOLDER="true">Bookmarks</H3>
        <DL>
            <DT><A HREF="https://calendar.google.com/calendar/r" add_date="1594058447">calendar</A>
            <DT><A HREF="https://github.com/" add_date="1657553942">github</A>
    ..............		
    """

    # find title
    title = soup.find("h1").string

    # the first dl element is the root folder, get the <p> inside it
    root_folder = soup.find("dl")

    output = BookmarkFolder(
        title=title,
        add_date=None,
        last_modified=None,
        contents=list(),
    )

    # we want to iterate over all the children of the root folder
    for child in root_folder.children:
        p: Bookmark | BookmarkFolder | None = process_child(child)
        if p is not None:
            p._parent = output
            output.contents.append(p)

    return output


def flatten_bookmarks(folder: BookmarkFolder) -> list[Bookmark]:
    """tag bookmark with position in the folder hierarchy"""

    output: list[Bookmark] = list()

    # use the iterator of the folder to get all contained bookmarks, not just direct children
    bk: Bookmark
    for bk in folder.iter_bookmarks():
        tags_temp: list[str] = list()
        bk_temp: Bookmark | BookmarkFolder = bk
        # loop until root
        while bk_temp._parent is not None:
            tags_temp.append(bk_temp._parent.title)
            bk_temp = bk_temp._parent

        bk.tags = tags_temp[::-1]
        output.append(bk)

    return output


def load_bookmarks(
    fname: str,
    input_format: typing.Literal["txt", "json", "html", None] = None,
) -> BookmarkFolder:
    """loads a list of urls from a file -- plain txt, json, or html bookmarks"""

    bkmks: BookmarkFolder
    with open(fname) as f:
        data: str = f.read()

        # guess input format
        if input_format is None:
            if fname.endswith(".json"):
                input_format = "json"
            elif fname.endswith(".txt"):
                input_format = "txt"
            elif any(
                [
                    fname.endswith(".html"),
                    fname.endswith(".htm"),
                    data.startswith("<!DOCTYPE NETSCAPE-Bookmark-file-1>"),
                ]
            ):
                input_format = "html"
            else:
                raise ValueError(f"can't infer format of file {fname}")

        # load data
        if input_format == "txt":
            # if plain file, store each in a bookmark
            urls = [line.strip() for line in f.readlines()]
            bkmks = BookmarkFolder(
                title="bookmarks",
                add_date=None,
                last_modified=None,
                contents=[Bookmark(title=url, href=url, add_date=None) for url in urls],
            )
        elif input_format == "json":
            bkmks = BookmarkFolder.load(json.loads(data))
        elif input_format == "html":
            bkmks = process_bookmark_file(data)
        else:
            raise ValueError(f"Unknown input format: {input_format}")

    return bkmks


def load_urls(
    fname: str,
    input_format: typing.Literal["txt", "json", "html", None] = None,
) -> list[str]:

    bkmks: BookmarkFolder = load_bookmarks(fname, input_format=input_format)
    urls: list[str] = list()
    for bk in bkmks.iter_bookmarks():
        urls.append(bk.href)

    return urls


def main(
    fname: str,
    flatten: bool = False,
    tree: bool = False,
    select: str | None = None,
):
    # read file
    bookmarks: BookmarkFolder = load_bookmarks(fname)

    print(f"{bookmarks.count_bookmarks()} bookmarks found", file=sys.stderr)

    if flatten:
        if tree:
            raise ValueError("cannot flatten and print tree at the same time")

        bookmarks = flatten_bookmarks(bookmarks)  # type: ignore

    if select is not None:
        # select by path
        path: list[str] = select.split("/")
        for p in path:
            bookmarks = bookmarks.get_child(p)  # type: ignore

    if tree:
        print(json.dumps(bookmarks.get_tree(), indent="\t"))

    else:
        print(json.dumps(json_serialize(bookmarks), indent="\t"))


if __name__ == "__main__":
    import fire  # type: ignore[import]

    fire.Fire(main)
