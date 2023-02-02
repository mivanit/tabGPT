format:
	python -m black .
	python -m isort format .

mypy:
	python -m mypy .

test:
	echo "NOTE: these tests do not check for correctness, only that some of the code runs."

	rm test_data/transient/*

	python bookmark_utils.py test_data/bookmarks.html > test_data/transient/bookmarks.json
	
	python bookmark_utils.py test_data/bookmarks.html --flatten > test_data/transient/bookmarks_flat.json
	
	python bookmark_utils.py test_data/bookmarks.html --tree > test_data/transient/bookmarks_tree.json
	
	python bookmark_utils.py test_data/bookmarks.html --select="Favorites bar/social" > test_data/transient/bookmarks_selected_social.json

	python bookmark_utils.py test_data/bookmarks.html > test_data/transient/bookmarks.json

	python preprocess_urls.py test_data/bookmarks.html --output_format=json --do_except=True > test_data/transient/bookmarks_preprocessed.json

check: mypy test
