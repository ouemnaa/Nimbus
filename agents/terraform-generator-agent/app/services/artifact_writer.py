from app.utils.file_utils import write_artifacts


class ArtifactWriter:
    def __init__(self, output_dir: str) -> None:
        self.output_dir = output_dir

    def write(self, files: list[dict[str, str]]) -> None:
        write_artifacts(files, self.output_dir)
