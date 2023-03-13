from node2vec import Node2Vec
import networkx as nx
from uuid import uuid4

from iawmr.domain.project import Project

def fit_node2vec(project: Project):
  graph = nx.Graph()
  
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
  

  # Embed the nodes using node2vec
  node2vec = Node2Vec(graph, dimensions=64, walk_length=30, num_walks=200)
  model = node2vec.fit(window=10, min_count=1)

  # Get the embeddings for each node
  # TODO: field_name_nodes
  # embeddings = {}
  # for node in nodes:
  #   embedding = model.wv[node.fully_qualified_name]
  #   embeddings[node.uuid] = list(embedding)

  # return embeddings