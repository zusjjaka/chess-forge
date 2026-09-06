from pathlib import Path


ROOT_DIR = Path(r'backend/repertoires/tests/api')
OUTPUT_FILE = Path('source.txt')

EXCLUDED_DIRS = {
    '.git',
    '.venv',
    '__pycache__',
    '.pytest_cache',
    '.mypy_cache',
    '.ruff_cache',
    'uv.lock',
    # 'tests',
}

EXCLUDED_FILES = {
    '.env',
    '.env.local',
}


def main() -> None:
    with OUTPUT_FILE.open(
        'w',
        encoding='utf-8',
    ) as output:
        for path in sorted(ROOT_DIR.rglob('*')):
            if not path.is_file():
                continue

            if any(
                part in EXCLUDED_DIRS
                for part in path.parts
            ):
                continue

            if path.name in EXCLUDED_FILES:
                continue

            if not path.name.endswith('.py') or path.name.startswith('__init__'):
                continue

            relative_path = path.relative_to(ROOT_DIR)

            try:
                content = path.read_text(
                    encoding='utf-8',
                )
            except UnicodeDecodeError:
                continue

            output.write(
                f'\n{"=" * 80}\n'
                f'FILE: {relative_path}\n'
                f'{"=" * 80}\n\n'
            )
            output.write(content)
            output.write('\n')

    print(f'Done: {OUTPUT_FILE}')


if __name__ == '__main__':
    main()
