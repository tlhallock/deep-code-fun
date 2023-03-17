
from iawmr.main import main

"""
TODO:
  I have wanted to use the vscode language server protocol for a while now
      This project would have been a good excuse to do that
  
    handle references to class.__init__ properly
    ensure that project_unique_path is unique
      This should be a string that uniquely identifies the node
    sequence2vec to embed the names
      
    Implement constants
    Add variable names
    finish pruning
    implement import levels (level==3 for "from ...parent import some_func")
    
    implement variable declarations as references
    
Don't parse everything, just parse up to the current obj model...
# todo: add ignore directories

    TODO: an expr can also be a statement
    TODO: understand these:
      possible sources of references?
        assign
        augassign
        annassign
        import
        import from
        global
        nonlocal
        Call
        attribute
        Name
      important missing information?
        boolop
        binop
        unaryop
        Constant
"""


if __name__ == "__main__":
    main()
