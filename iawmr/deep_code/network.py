
from node2vec import Node2Vec
import networkx as nx
from uuid import uuid4
import matplotlib
import matplotlib.pyplot as plt
from networkx.readwrite import json_graph
import json


from iawmr.deep_code.project import Project

def fit_node2vec(project: Project):
  graph = nx.Graph()
  
  # Could use fully qualified name, when it is available
  node_uuids = []
  unresolved_references = {}
  
  for module in project.modules():
    for _, ast_node, _ in module.all_nodes():
      node_uuids.append(ast_node.uuid)
      attrs = ast_node.node_attributes()
      graph.add_node(ast_node.uuid, **attrs)
  
  for module in project.modules():
    for _, node, _ in module.all_nodes():
      for reference in node.references:
        if reference.target:
          graph.add_edge(node.uuid, reference.target.uuid, edge_type="references")
          continue
        
        key = reference.fully_qualified_name
        if key not in unresolved_references:
          unresolved_target = str(uuid4())
          node_uuids.append(unresolved_target)
          graph.add_node(unresolved_target)
          unresolved_references[key] = unresolved_target
          
        graph.add_edge(node.uuid, unresolved_references[key], edge_type="unresolved")
  
  # Now add children
  for module in project.modules():
    for _, node, _ in module.all_nodes():
      # TODO: Should I add a begin sentinal?
      prev_group_node = None
      for field_name, group in node.children.items():
        prev_child = None
        group_node = str(uuid4())
        node_uuids.append(group_node)
        graph.add_node(group_node, field_name=field_name)
        graph.add_edge(node.uuid, group_node, edge_type="field")
        
        for child in group:
          graph.add_edge(group_node, child.uuid, edge_type="contains")
          if prev_child is not None:
            graph.add_edge(prev_child.uuid, child.uuid, edge_type="child_follows")
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
  model = node2vec.fit(window=5, min_count=1)

  embeddings = {}
  for node in node_uuids:
    embedding = model.wv[node]
    embeddings[node] = list(embedding)
  return embeddings
  
def print_stats():
  with open("output.dir/graph.json", "r") as f:
    data = json.load(f)
  print("number of nodes", len(data["nodes"]))
  print("number of edges", len(data["links"]))
  print("number of unresolved references", len([link for link in data["links"] if link["edge_type"] == "unresolved"]))