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


def document_workflow_arg(
    *, name, type=None, default=None, required=None, description=None
):
    """
    Documents a workflow argument in Markdown format.
    >>> print(document_workflow_arg(name="foo"))
    - `foo`
    >>> print(document_workflow_arg(name="foo", default=True))
    - `foo` (default `true`)
    >>> print(document_workflow_arg(name="foo", required=True))
    - `foo` (**required**)
    >>> print(document_workflow_arg(name="foo", description="hello"))
    - `foo` - hello
    >>> print(document_workflow_arg(name="foo", type="string", default="bar", required=True, description="hello"))
    - `foo` (string, default `"bar"`, **required**) - hello
    """
    props = []
    if type:
        props.append(type)
    if default is not None:
        props.append(f"default `{json.dumps(default)}`")
    if required:
        props.append("**required**")

    s = f"- `{name}`"
    if props:
        s += " ("
        s += ", ".join(props)
        s += ")"

    if description:
        s += " - "
        s += description

    return s


def create_documentation(workflow_def):
    """
    Generates a Markdown formatted usage documentation for the given workflow dict.
    >>> print(create_documentation({}))
    ### Inputs
    There are no inputs for this workflow.

    >>> src = yaml.load('''
    ... on:
    ...   workflow_call:
    ...     inputs:
    ...       foo:
    ...         type: string
    ...     secrets:
    ...       foo:
    ...         required: true
    ... ''', Loader=yaml.CLoader)
    >>> res = create_documentation(src).split('\\n\\n') # must split these to make doctest work
    >>> print(res[0])
    ### Inputs
    - `foo` (string)

    >>> print(res[1])
    ### Secrets
    - `foo` (**required**)
    """
    spec = workflow_def.get(True, {}).get("workflow_call", {})
    inputs = spec.get("inputs", {})
    secrets = spec.get("secrets", {})

    docstring = "### Inputs\n"
    if inputs:
        docstring += "\n".join(
            [document_workflow_arg(name=k, **v) for k, v in inputs.items()]
        )
    else:
        docstring += "There are no inputs for this workflow."

    if secrets:
        docstring += "\n\n### Secrets\n"
        docstring += "\n".join(
            [document_workflow_arg(name=k, **v) for k, v in secrets.items()]
        )

    return docstring


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
        r"(<!-- autodoc start -->).+(<!-- autodoc end -->)",
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
    docstring = create_documentation(workflow)
    readme = replace_docstring(readme, docstring)

    args.doc_file.seek(0)
    args.doc_file.truncate(0)
    args.doc_file.write(readme)
