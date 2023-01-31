format:
	python -m black .
	python -m isort format .

mypy:
	python -m mypy .

check: format mypy
