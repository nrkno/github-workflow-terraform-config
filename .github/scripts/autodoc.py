"""
Parses a GitHub Actions reusable workflow file and creates usage notes in
Markdown format. Replaces the all content between `<!-- autodoc start -->` and
`<!-- autodoc end -->` within the `doc_file` with the generated documentation.

1. Install dependencies with `python -m pip install pyyaml`
2. Run tests with `python -m doctest`
3. Get help with `python autodoc -h`
"""
import argparse
import json
import re

import yaml


def create_doc(d):
    """
    Generates a Markdown formatted usage documentation for the given workflow dict.
    >>> src = '''
    ... on:
    ...   workflow_call:
    ...     inputs:
    ...       a:
    ...         type: boolean
    ...         default: true
    ...       b:
    ...         type: string
    ...         description: something to say
    ...       c:
    ...         type: string
    ... '''
    >>> res = create_doc(yaml.load(src, Loader=yaml.CLoader))
    >>> print(res)
    - `a` (boolean, default `true`)
    - `b` (string): something to say
    - `c` (string)
    """
    inputs = (
        d.get(True, {}).get("workflow_call", {}).get("inputs", {})
    )  # The first level "on" is interpreted as a boolean true by the loader

    lines = []
    for k, v in inputs.items():
        type = v.get("type", "<unkown>")
        default = v.get("default")
        required = v.get("required", False)
        desc = v.get("description")

        doc = f"- `{k}` ({type}"
        if required:
            doc += ", **required**"
        if default:
            doc += f", default `{json.dumps(default)}`"
        doc += ")"
        if desc:
            doc += f": {desc}"

        lines.append(doc)
    return "\n".join(lines)


def replace_docstring(src, docstring):
    """
    Replaces all text between a start and end token inside `src` with `docstring`.
    >>> src = '''one
    ... two
    ... <!-- autodoc start -->
    ... three
    ... <!-- autodoc end -->
    ... four
    ... five'''
    >>> res = replace_docstring(src, "this\\nwas\\nreplaced")
    >>> print(res)
    one
    two
    <!-- autodoc start -->
    this
    was
    replaced
    <!-- autodoc end -->
    four
    five
    """
    return re.sub(
        r"(<!--\s+autodoc start\s+-->).+(<!--\s+autodoc end\s+-->)",
        r"\1\n" + docstring + r"\n\2",
        src,
        flags=re.IGNORECASE | re.DOTALL,
    )


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "workflow_file",
        type=argparse.FileType("r"),
    )
    parser.add_argument(
        "doc_file",
        type=argparse.FileType("r+"),
    )
    args = parser.parse_args()

    workflow = yaml.load(args.workflow_file, Loader=yaml.CLoader)
    readme = args.doc_file.read()
    docstring = create_doc(workflow)
    newreadme = replace_docstring(readme, docstring)

    args.doc_file.seek(0)
    args.doc_file.truncate(0)
    args.doc_file.write(newreadme)
