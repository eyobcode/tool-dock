import importlib
from django.conf import settings

def get_tool_runner(tool_name):
    path = settings.TOOL_RUNNERS.get(tool_name)
    if not path:
        raise ValueError(f"Tool '{tool_name}' not registered in settings.TOOL_RUNNERS")

    module_name, class_name = path.rsplit(".", 1)
    module = importlib.import_module(module_name)
    cls = getattr(module, class_name)
    return cls()
