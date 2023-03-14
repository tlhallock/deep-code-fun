
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

def fit_node2vec(project: Project):
  graph = nx.Graph()
  node_uuids: Set[str] = set()
  
  for module in project.modules():
    for node, _ in module.all_nodes():
      node: model.AstNode = node
      id = node.project_unique_path
      if id in node_uuids:
        raise Exception("Duplicate node")
      node_uuids.add(id)
      attrs = node.node_attributes()
      graph.add_node(id, **attrs)
  
  for module in project.modules():
    for node, _ in module.all_nodes():
      node: model.AstNode = node
      for reference in node.references:
        if reference.target:
          graph.add_edge(
            node.project_unique_path,
            reference.target.project_unique_path,
            edge_type=reference.reference_type,
            resolution="resolved",
          )
          continue
        
        key = "unresolved::{reference.fully_qualified_name}"
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
  
  # Now add children
  for module in project.modules():
    for node, _ in module.all_nodes():
      # TODO: Should I add a begin sentinal?
      prev_group_node = None
      for field_name, group in node.children.items():
        prev_child = None
        group_node = f"{node.project_unique_path}::{field_name}"
        node_uuids.add(group_node)
        graph.add_node(group_node, field_name=field_name)
        graph.add_edge(node.project_unique_path, group_node, edge_type="field")
        # Check if the node already exists
        
        for child in group:
          graph.add_edge(group_node, child.project_unique_path, edge_type="contains")
          if prev_child is not None:
            graph.add_edge(prev_child.project_unique_path, child.project_unique_path, edge_type="child_follows")
          prev_child = child
        
        if prev_group_node is not None:
          graph.add_edge(prev_group_node, group_node, edge_type="group_follows")
        prev_group_node = group_node
  
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