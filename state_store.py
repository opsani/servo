import yaml

DFLT_FILE="_state.yaml"


def get_state(file=DFLT_FILE):
    """
    Get state, returns an object
    """
    try:
        f = open(file)
        state = yaml.load(f)
    except:
        state = {}

    return state


def set_state(state, file=DFLT_FILE):
    """
    Set state, may raise an exception
    """

    with open(file, 'w') as f:
        yaml.dump(state, f, default_flow_style=False)
