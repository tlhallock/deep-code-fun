
from typing import Optional
from iawmr.domain.project import Project
import click


@click.command()
@click.option("--root-path", type=click.Path(exists=True))
def main(root_path: Optional[str] = "."):
  # ?
  root_path = "."
  Project.parse_from_root_path(root_path=root_path)

