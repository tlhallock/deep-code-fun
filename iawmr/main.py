
from typing import Optional
import iawmr.domain.parsing as parsing
from iawmr.domain.project import ProjectSpec
import click
import json


@click.command()
@click.option("--root-path", type=click.Path(exists=True))
def main(root_path: Optional[str] = "."):
  spec = ProjectSpec(
    name="my self",
    ignores=["venv"],
    venv=None,
    sources=["."]
  )
  write_jsons = True
  project = parsing.Parsing.parse_project(spec=spec, write_jsons=write_jsons)
  print(json.dumps(project.dict(), indent=2))

