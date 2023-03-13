
from typing import Optional
import iawmr.deep_code.network as network
import iawmr.deep_code.parsing as parsing
from iawmr.deep_code.project import ProjectSpec
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
  project.resolve_references()
  network.fit_node2vec(project)
  
  # print(json.dumps(project.dict(), indent=2))

