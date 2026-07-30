.PHONY: install run debug test clean lint lint-strict

MAP ?= maps/easy/01_linear_path.txt

install:
	uv sync --all-groups

run:
	uv run python main.py $(MAP)

debug:
	uv run python -m pdb main.py $(MAP)

make visual:
	uv run python arcade_test.py $(MAP)

test:
	uv run python -m unittest discover -s tests -v

clean:
	rm -rf __pycache__ .mypy_cache .pytest_cache
	find . -type d -name __pycache__ -prune -exec rm -rf {} +

lint:
	uv run flake8 .
	uv run mypy . --warn-return-any --warn-unused-ignores \
		--ignore-missing-imports --disallow-untyped-defs \
		--check-untyped-defs

lint-strict:
	uv run flake8 .
	uv run mypy . --strict
