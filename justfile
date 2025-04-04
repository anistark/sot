version := `python3 -c "from src.sot.__about__ import __version__; print(__version__)"`

default:
	@echo "\"just publish\"?"

publish: clean
	@if [ "$(git rev-parse --abbrev-ref HEAD)" != "main" ]; then exit 1; fi
	gh release create "v{{version}}"
	python3 -m build --sdist --wheel .
	twine upload dist/*

clean:
	@find . | grep -E "(__pycache__|\.pyc|\.pyo$)" | xargs rm -rf
	@rm -rf src/*.egg-info/ build/ dist/ .tox/

format:
	isort .
	black .
	blacken-docs README.md

lint:
	black --check .
	flake8 .

publish-test: clean
	python3 -m build --sdist --wheel .
	twine check dist/*
