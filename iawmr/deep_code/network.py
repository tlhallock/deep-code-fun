
from typing import List, Set
from node2vec import Node2Vec
import networkx as nx
from uuid import uuid4
import matplotlib
import matplotlib.pyplot as plt
from networkx.readwrite import json_graph
import iawmr.deep_code.model as model
import json


from iawmr.deep_code.project import Project


def create_nodes(project: Project, graph: nx.Graph, node_uuids: Set[str]) -> None:
  for module in project.modules():
    for node, _ in module.all_nodes():
      id = node.project_unique_path
      if id in node_uuids:
        raise Exception("Duplicate node")
      node_uuids.add(id)
      attrs = node.node_attributes()
      graph.add_node(id, **attrs)


def add_nodes_references(graph: nx.Graph, node_uuids: Set[str], node: model.AstNode, reference: model.CodeReference) -> None:
  if reference.target:
    graph.add_edge(
      node.project_unique_path,
      reference.target.project_unique_path,
      edge_type=reference.reference_type,
      resolution="resolved",
    )
    return

  key = f"unresolved::{reference.fully_qualified_name}"
  if key not in node_uuids:
    # TODO: use the Project's unresolved_references, then we can assume it is here, right?
    node_uuids.add(key)
    graph.add_node(key)
          
  graph.add_edge(
    node.project_unique_path,
    key,
    edge_type=reference.reference_type,
    resolution="unresolved",
  )


def add_references(project: Project, graph: nx.Graph, node_uuids: Set[str]) -> None:
  for module in project.modules():
    for node, _ in module.all_nodes():
      for reference in node.references:
        add_nodes_references(graph=graph, node_uuids=node_uuids, node=node, reference=reference)


def add_child_list(graph: nx.Graph, parent: str, values: List[model.AstNode]) -> None:
  # Add beginning sentinal?
  prev_child = None
  for child in values:
    graph.add_edge(parent, child.project_unique_path, edge_type="is_child")
    if prev_child is not None:
      graph.add_edge(prev_child.project_unique_path, child.project_unique_path, edge_type="child_follows")
    prev_child = child


def add_value_fields(graph: nx.Graph, node_uuids: Set[str], node: model.AstNode) -> None:
  prev_group_node = None
  for index, mapping in enumerate(node.children.value_fields.items()):
    field_name, values = mapping
    
    group_node = f"{node.project_unique_path}::{field_name}::{index}"
    node_uuids.add(group_node)
    graph.add_node(group_node, field_name=field_name)
    graph.add_edge(node.project_unique_path, group_node, edge_type="field")
    if prev_group_node is not None:
      graph.add_edge(prev_group_node, group_node, edge_type="group_follows")
    # Check if the node already exists
  
    add_child_list(graph=graph, parent=group_node, values=values)  
  
    prev_group_node = group_node
  

def add_list_fields(graph: nx.Graph, node_uuids: Set[str], node: model.AstNode) -> None:
  prev_outer_group_node = None
  for outer_index, outer_mapping in enumerate(node.children.list_fields.items()):
    field_name, outer_values = outer_mapping
    
    outer_group_node = f"{node.project_unique_path}::{field_name}::{outer_index}"
    node_uuids.add(outer_group_node)
    graph.add_node(outer_group_node, field_name=field_name)
    graph.add_edge(node.project_unique_path, outer_group_node, edge_type="outer-field")
    if prev_outer_group_node is not None:
      graph.add_edge(prev_outer_group_node, outer_group_node, edge_type="group_follows")
    
    prev_inner_group_node = None
    for inner_index, inner_values in enumerate(outer_values):
      group_node = f"{outer_group_node}::{inner_index}"
      node_uuids.add(group_node)
      graph.add_node(group_node, field_name=field_name)
      graph.add_edge(outer_group_node, group_node, edge_type="inner-field")
      if prev_inner_group_node is not None:
        graph.add_edge(prev_inner_group_node, group_node, edge_type="group_follows")
        
      add_child_list(graph=graph, parent=group_node, values=inner_values)
      prev_inner_group_node = group_node
    prev_outer_group_node = outer_group_node
  

def add_nodes_children(graph: nx.Graph, node_uuids: Set[str], node: model.AstNode) -> None:
  # TODO: Should I add sentinal nodes? (Or just a begin?)
  add_value_fields(graph=graph, node_uuids=node_uuids, node=node)
  add_list_fields(graph=graph, node_uuids=node_uuids, node=node)


def add_children(project: Project, graph: nx.Graph, node_uuids: Set[str]) -> None:
  for module in project.modules():
    for node, _ in module.all_nodes():
      add_nodes_children(graph=graph, node_uuids=node_uuids, node=node)

def fit_node2vec(project: Project):
  graph = nx.Graph()
  node_uuids: Set[str] = set()
  
  create_nodes(project=project, graph=graph, node_uuids=node_uuids)
  add_references(project=project, graph=graph, node_uuids=node_uuids)
  add_children(project=project, graph=graph, node_uuids=node_uuids)
  
  # Now add children
  
  if True:
    data = json_graph.node_link_data(graph)
    # Save the data to a JSON file
    with open("output.dir/graph.json", "w") as f:
      json.dump(data, f, indent=2)
    print("wrote graph")
    print_stats()
  
  if False:
    # This takes too long.
    pos = nx.spring_layout(graph)
    nx.draw(graph, pos, with_labels=True)
    plt.savefig("output.dir/graph.png")
    print("wrote image")
  

  # Small so we can run quickly until it works
  node2vec = Node2Vec(graph, dimensions=3, walk_length=5, num_walks=5)
  n2v_model = node2vec.fit(window=5, min_count=1)

  embeddings = {}
  for node in node_uuids:
    embedding = n2v_model.wv[node]
    embeddings[node] = list(embedding)
  return embeddings
  
def print_stats():
  with open("output.dir/graph.json", "r") as f:
    data = json.load(f)
  print("number of nodes", len(data["nodes"]))
  print("number of edges", len(data["links"]))
  print("number of unresolved references", len([n for n in data["nodes"] if n["id"].startswith("unresolved::")]))