format:
	python -m black .

mypy:
	python -m mypy .

check: format mypy
