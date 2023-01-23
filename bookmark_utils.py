"""reads a bookmark html export in the `<!DOCTYPE NETSCAPE-Bookmark-file-1>` browser format

I've checked, and firefox, edge, and vivaldi all use this format
"""

from dataclasses import dataclass, field, asdict
import warnings
import json

from bs4 import BeautifulSoup, PageElement
from muutils.json_serialize import json_serialize

# pylint: disable=missing-class-docstring,pointless-string-statement

@dataclass(kw_only=True)
class Bookmark:
	title: str
	href: str
	add_date: int
	_parent: "BookmarkFolder|None" = field(default=None, repr=False, compare=False)
	tags: tuple[str]|None = None

	def serialize(self) -> dict:
		return dict(
			title = self.title,
			href = self.href,
			add_date = self.add_date,
			tags = self.tags,
		)

@dataclass
class BookmarkFolder:
	title: str
	add_date: int|None
	last_modified: int|None
	contents: list["Bookmark|BookmarkFolder"]
	_parent: "BookmarkFolder|None" = field(default=None, repr=False, compare=False)

	_being_serialized: bool = False

	def serialize(self) -> dict:
		if self._being_serialized:
			raise RuntimeError("recursive serialization")
		self._being_serialized = True
		return dict(
			title = self.title,
			add_date = self.add_date,
			last_modified = self.last_modified,
			contents = [x.serialize() for x in self.contents],
		)

	def get_child(self, title: str) -> "Bookmark|BookmarkFolder":
		for x in self.contents:
			if x.title == title:
				return x

		raise KeyError(f"no child with title {title}")

	def __iter__(self):
		for x in self.contents:
			if isinstance(x, Bookmark):
				yield x
			else:
				yield from x

	def count_bookmarks(self) -> int:
		return sum(
			1 if isinstance(x, Bookmark) else x.count_bookmarks()
			for x in self.contents
		)

def process_child(element: PageElement) -> Bookmark|BookmarkFolder:
	if element.name == "h3":

		bkfolder: BookmarkFolder = BookmarkFolder(
			title = element.string,
			add_date = element["add_date"] if "add_date" in element else None,
			last_modified = element["last_modified"] if "last_modified" in element else None,
			contents = list(),
		)

		child_elements = element.find_next_sibling("dl")

		# preserve order, and loop over both folders and bookmarks at once
		for child in child_elements.children:
			p: Bookmark|BookmarkFolder|None = process_child(child)
			if p is not None:
				p._parent = bkfolder
				bkfolder.contents.append(p)
		
		return bkfolder

	elif element.name == "dl":
		# we skip it, because the sibling dl element should be processed in `get_bookmark_folder`
		return None
	elif element.name == "a":
		return Bookmark(
			title = element.string,
			href = element["href"],
			add_date = element["add_date"],
		)
	else:
		warnings.warn(f"unexpected tag {element.name}")
		# raise ValueError(f"unexpected tag {element.name}")
		return None


def process_bookmark_file(data: str) -> BookmarkFolder:

	# this part is a hack: remove all <DT> and <p> tags, they are useless and complicate things
	data = data.replace("<DT>", "").replace("<dt>", "").replace("<p>", "").replace("<P>", "")
	
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
		title = title,
		add_date = None,
		last_modified = None,
		contents = list(),
	)

	# we want to iterate over all the children of the root folder
	for child in root_folder.children:
		p: Bookmark|BookmarkFolder|None = process_child(child)
		if p is not None:
			p._parent = output
			output.contents.append(p)

	return output


def flatten_bookmarks(folder: BookmarkFolder) -> list[Bookmark]:
	"""tag bookmark with position in the folder hierarchy"""
	
	output: list[Bookmark] = list()

	# use the iterator of the folder to get all contained bookmarks, not just direct children
	bk: Bookmark
	for bk in folder:
		tags_temp: list[str] = list()
		bk_temp: Bookmark = bk
		# loop until root
		while bk_temp._parent is not None:
			tags_temp.append(bk_temp._parent.title)
			bk_temp = bk_temp._parent
		
		bk.tags = tags_temp[::-1]
		output.append(bk)
	
	return output

def main(fname: str = "data/wip/bookmarks.html"):
	with open(fname, "r", encoding="utf-8") as f:
		data = f.read()

	bookmarks = process_bookmark_file(data)

	return bookmarks

if __name__ == "__main__":
	import sys
	bkmks = main(sys.argv[1])

	print(f"{bkmks.count_bookmarks()} bookmarks found", file=sys.stderr)

	if ("--flatten" in sys.argv) or ("-f" in sys.argv):
		bkmks = flatten_bookmarks(bkmks)

	print(json.dumps(json_serialize(bkmks), indent="\t"))
