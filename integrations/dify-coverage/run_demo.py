"""Run the fictional example through the actual Dify SDK, without network."""

import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parent / "plugin"))
from tools.props_coverage import PropsCoverageTool

for message in PropsCoverageTool.from_credentials({}).invoke({"mode": "demo"}):
    print(json.dumps(message.message.json_object, indent=2))
