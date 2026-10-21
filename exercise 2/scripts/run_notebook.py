"""Execute and save all notebook outputs using this Python environment."""

import json
import sys
import tempfile
from pathlib import Path

import nbformat
from jupyter_client import KernelManager
from nbclient import NotebookClient

from fed.settings import NOTEBOOK_PATH


def run_notebook() -> None:
    """Execute the project notebook with this interpreter, then save its outputs.

    Paths come from the installed package, so any working folder is supported.
    Cell failures propagate and leave the saved notebook untouched. A temporary
    kernel specification avoids changing the user's Jupyter installation.
    """
    notebook = NOTEBOOK_PATH
    nb = nbformat.read(notebook, as_version=4)
    # A temporary kernel specification avoids changing the user's Jupyter setup.
    with tempfile.TemporaryDirectory() as temp:
        kernel_dir = Path(temp) / "gdp-analysis"
        kernel_dir.mkdir()
        (kernel_dir / "kernel.json").write_text(
            json.dumps(
                {
                    "argv": [sys.executable, "-m", "ipykernel_launcher", "-f", "{connection_file}"],
                    "display_name": "Python (gdp-analysis)",
                    "language": "python",
                }
            ),
            encoding="utf-8",
        )
        manager = KernelManager(kernel_name="gdp-analysis")
        manager.kernel_spec_manager.kernel_dirs.insert(0, temp)
        client = NotebookClient(
            nb, km=manager, timeout=180, resources={"metadata": {"path": str(notebook.parent)}}
        )
        try:
            client.execute()
        finally:
            if manager.has_kernel:
                manager.shutdown_kernel(now=True)
    nbformat.write(nb, notebook)
    print(f"Executed and saved {notebook.name}")


if __name__ == "__main__":
    run_notebook()
