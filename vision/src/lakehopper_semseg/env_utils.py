from pathlib import Path


def is_notebook() -> bool:
    """Check if we are running in a Jupyter notebook.
    Source: https://stackoverflow.com/a/39662359/7120579"""
    try:
        shell = get_ipython().__class__.__name__  # type: ignore
        if shell == "ZMQInteractiveShell":
            return True  # Jupyter notebook or qtconsole
        elif shell == "TerminalInteractiveShell":
            return False  # Terminal running IPython
        else:
            return False  # Other type (?)
    except NameError:
        return False  # Probably standard Python interpreter


def find_repo(path):
    """Find repository root from the path's parents.
    Source: https://stackoverflow.com/a/67516092"""
    for path in Path(path).parents:
        # Check whether "path/.git" exists and is a directory
        git_dir = path / ".git"
        if git_dir.is_dir():
            return path
