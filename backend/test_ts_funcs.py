import asyncio
from tree_sitter_languages import get_language, get_parser

PYTHON_CODE = b"""
def my_function(a, b):
    pass

class MyClass:
    def my_method(self):
        pass
"""

JS_CODE = b"""
function hello() {}
const arrow = () => {}
const expr = function anon() {}
class MyClass {
    method1() {}
}
"""

GO_CODE = b"""
package main

func hello() {}

type MyStruct struct {}

func (m *MyStruct) method1() {}
"""

# Queries
_PY_FUNCTION_QUERY = """
(class_definition name: (identifier) @function)
(function_definition name: (identifier) @function)
"""

_JS_FUNCTION_QUERY = """
(class_declaration name: (identifier) @function)
(function_declaration name: (identifier) @function)
(method_definition name: (property_identifier) @function)
(variable_declarator 
  name: (identifier) @function 
  value: [(arrow_function) (function)])
"""

_GO_FUNCTION_QUERY = """
(type_spec name: (type_identifier) @function)
(function_declaration name: (identifier) @function)
(method_declaration name: (field_identifier) @function)
"""

def _extract_functions(source: bytes, lang_name: str, query_src: str) -> list[str]:
    try:
        language = get_language(lang_name)
        parser = get_parser(lang_name)
        tree = parser.parse(source)

        query = language.query(query_src)
        captures = query.captures(tree.root_node)
        functions = []
        for node, _ in captures:
            raw = node.text.decode(errors="replace").strip()
            if raw:
                functions.append(raw)
        return functions
    except Exception as e:
        return [str(e)]

if __name__ == "__main__":
    print("Python:", _extract_functions(PYTHON_CODE, "python", _PY_FUNCTION_QUERY))
    print("JS:", _extract_functions(JS_CODE, "javascript", _JS_FUNCTION_QUERY))
    print("Go:", _extract_functions(GO_CODE, "go", _GO_FUNCTION_QUERY))
