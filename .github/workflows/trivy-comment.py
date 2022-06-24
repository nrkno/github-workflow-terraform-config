#!/usr/bin/env python3

import json
import sys

result_filename = sys.argv[1]


def create_output(filename, error):
    severity = "warning"
    if error["Severity"] in ("HIGH", "CRITICAL"):
        severity = "error"
    message = f"{error['ID']}: {error['Title']}%0A{error['Description']}%0A{error['Message']}%0AResolution: {error['Resolution']}%0A"
    for reference in error["References"]:
        message += f"%0A{reference}"
    start_line = error["CauseMetadata"]["StartLine"]
    end_line = error["CauseMetadata"]["EndLine"]
    print(
        f"::{severity} file={filename},line={start_line},endLine={end_line}::{message}"
    )


with open(result_filename, "r") as result_file:
    output = json.load(result_file)
    results = output.get("Results", [])

    for result in results:
        for misconfiguration in result.get("Misconfigurations", []):
            create_output(result["Target"], misconfiguration)

    # Since severity filter is set at job level, we can exit non-zero for all
    # errors regardless of severity and let workflow consumers decide which
    # severity levels to care about.
    if results:
        sys.exit(1)
