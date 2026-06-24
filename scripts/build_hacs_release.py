from pathlib import Path
from zipfile import ZIP_DEFLATED, ZipFile


ROOT = Path(__file__).parents[1]
SOURCE = ROOT / "custom_components" / "goecharger"
TARGET = ROOT / "goecharger.zip"


def build_zip(target=TARGET, source=SOURCE):
    with ZipFile(target, "w", ZIP_DEFLATED) as archive:
        for path in sorted(source.rglob("*")):
            if path.is_file() and "__pycache__" not in path.parts and path.suffix != ".pyc":
                archive.write(path, path.relative_to(source))


if __name__ == "__main__":
    build_zip()
