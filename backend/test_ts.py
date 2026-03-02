import asyncio
from tree_sitter_languages import get_language, get_parser

JS_CODE = b"""
function hello() {}
const arrow = () => {}
const expr = function() {}
class MyClass {
    method1() {}
}
"""

_JS_FUNCTION_QUERY = """
(function_declaration name: (identifier) @function)
(method_definition name: (property_identifier) @function)
(variable_declarator name: (identifier) @function value: [(arrow_function) (function)])
"""

def _extract_functions(source: bytes, lang_name: str, query_src):
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

print(_extract_functions(JS_CODE, "javascript", _JS_FUNCTION_QUERY))

