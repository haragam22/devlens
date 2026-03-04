from app.services.parser import parse_repository
from pathlib import Path
import json

if __name__ == "__main__":
    # Test on the current repository's backend folder
    test_path = Path(".").resolve()
    print(f"Parsing: {test_path}")
    graph = parse_repository(test_path)
    
    # Check if nodes have extracted_names
    for node in graph.nodes:
        if node.id.endswith("parser.py"):
            print("Found parser.py!")
            print(f"Extracted names: {node.extracted_names}")
            break
