"""Local launcher for the EDAViz Streamlit app.

>>> import edaviz
>>> app = edaviz.show()  # returns once the server is ready; does not block
>>> app.url
>>> app.stop()
"""

from importlib.metadata import PackageNotFoundError, version

from edaviz.launcher import EDAVizServer, LaunchError, show

try:
    __version__ = version("edaviz")
except PackageNotFoundError:  # Imported from a checkout without installation.
    __version__ = "0+unknown"

__all__ = ["EDAVizServer", "LaunchError", "show", "__version__"]
