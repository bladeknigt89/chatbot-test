from importlib.metadata import PackageNotFoundError, version

try:
    __version__ = version("local-ai-chatbot")
except PackageNotFoundError:
    __version__ = "1.0.0"
