
from iawmr.main import main

"""
TODO:
    remove the uuid field from the ast nodes
      This should be a string that uniquely identifies the node
    sequence2vec to embed the names
      
    Make expressions optional
    Implement constants
    Add variable names
    finish pruning
    implement import levels (level==3 for "from ...parent import some_func")
    
    implement function calls as references
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
