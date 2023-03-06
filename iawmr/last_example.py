import networkx as nx

# create an empty graph
G = nx.Graph()

# add nodes for the project and all its modules
project_node = 'project'
module_nodes = ['module1', 'module2', 'module3']
G.add_node(project_node)
G.add_nodes_from(module_nodes)

# add edges between the project node and the module nodes
for module in module_nodes:
    G.add_edge(project_node, module)

# add edges between modules and their children classes, methods, and global variables
for module in module_nodes:
    # connect modules to their classes
    class_nodes = ['class1', 'class2', 'class3']
    G.add_nodes_from(class_nodes)
    for class_node in class_nodes:
        G.add_edge(module, class_node)
        
        # connect classes to their methods
        method_nodes = ['method1', 'method2', 'method3']
        G.add_nodes_from(method_nodes)
        for method_node in method_nodes:
            G.add_edge(class_node, method_node)
            
            # connect methods to their references (statements, variables, etc.)
            reference_nodes = ['reference1', 'reference2', 'reference3']
            G.add_nodes_from(reference_nodes)
            for reference_node in reference_nodes:
                G.add_edge(method_node, reference_node)
