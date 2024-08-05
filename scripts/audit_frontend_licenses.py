#!/usr/bin/env python
# Copyright (c) Streamlit Inc. (2018-2022) Snowflake Inc. (2022-2024)
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.

"""Audit the licenses of all our frontend dependencies (as defined by our
`pnpm.lock` file). If any dependency has an unacceptable license, print it
out and exit with an error code. If all dependencies have acceptable licenses,
exit normally.
"""

import json
import subprocess
import sys
from pathlib import Path
from typing import NoReturn, Set, Tuple, cast

from typing_extensions import TypeAlias

PackageInfo: TypeAlias = Tuple[str, str]

SCRIPT_DIR = Path(__file__).resolve().parent
FRONTEND_DIR = SCRIPT_DIR.parent / "frontend"

# Set of acceptable licenses. If a library uses one of these licenses,
# we can include it as a dependency.
ACCEPTABLE_LICENSES = {
    "MIT",  # https://opensource.org/licenses/MIT
    "Apache-2.0",  # https://opensource.org/licenses/Apache-2.0
    "Apache-2.0 WITH LLVM-exception",  # https://spdx.org/licenses/LLVM-exception.html
    "0BSD",  # https://opensource.org/licenses/0BSD
    "BlueOak-1.0.0",  # https://blueoakcouncil.org/license/1.0.0
    "BSD-2-Clause",  # https://opensource.org/licenses/BSD-2-Clause
    "BSD-3-Clause",  # https://opensource.org/licenses/BSD-3-Clause
    "ISC",  # https://opensource.org/licenses/ISC
    "CC0-1.0",  # https://creativecommons.org/publicdomain/zero/1.0/
    "CC-BY-3.0",  # https://creativecommons.org/licenses/by/3.0/
    "CC-BY-4.0",  # https://creativecommons.org/licenses/by/4.0/
    "Python-2.0",  # https://www.python.org/download/releases/2.0/license/
    "Zlib",  # https://opensource.org/licenses/Zlib
    "Unlicense",  # https://unlicense.org/
    "WTFPL",  # http://www.wtfpl.net/about/
    # Multi-licenses are acceptable if at least one of the licenses is acceptable.
    "(MIT OR Apache-2.0)",
    "(MPL-2.0 OR Apache-2.0)",
    "(MIT OR CC0-1.0)",
    "(Apache-2.0 OR MPL-1.1)",
    "(BSD-3-Clause OR GPL-2.0)",
    "(MIT AND BSD-3-Clause)",
    "(MIT AND Zlib)",
    "(WTFPL OR MIT)",
    "(AFL-2.1 OR BSD-3-Clause)",
    "(BSD-2-Clause OR MIT OR Apache-2.0)",
    "(MIT OR GPL-3.0-or-later)",
    "Apache-2.0 AND MIT",
    "Apache*",  # https://github.com/saikocat/colorbrewer/blob/master/LICENSE.txt
}

# Some of our dependencies have licenses that pnpm fails to parse, but that
# are still acceptable. This set contains all those exceptions. Each entry
# should include a comment about why it's an exception.
PACKAGE_EXCEPTIONS: Set[PackageInfo] = {
    (
        # Mapbox Web SDK license: https://github.com/plotly/mapbox-gl-js/blob/v1.13.4/LICENSE.txt
        "@plotly/mapbox-gl",
        "1.13.4",
    ),
    (
        # MIT License https://github.com/felixge/node-stack-trace/blob/v0.0.9/License
        "stack-trace",
        "0.0.9",
    ),
    (
        # Mapbox Web SDK license: https://github.com/mapbox/mapbox-gl-js/blob/v1.13.2/LICENSE.txt
        "mapbox-gl",
        "1.13.2",
    ),
    (
        # MIT License https://github.com/mapbox/jsonlint/blob/v2.0.2/README.md
        "@mapbox/jsonlint-lines-primitives",
        "2.0.2",
    ),
    (
        # Apache-2.0 license: https://github.com/saikocat/colorbrewer/blob/master/LICENSE.txt
        "colorbrewer",
        "1.5.6",
    ),
}


def check_licenses(licenses) -> NoReturn:
    # `pnpm licenses` outputs a bunch of lines.
    # The last line contains the JSON object we care about
    licenses_json = json.loads(licenses)
    # assert licenses_json["type"] == "table"

    # Pull out the list of package infos from the JSON.
    licenses = licenses_json.keys()

    # Discover packages that don't have an acceptable license, and that don't
    # have an explicit exception. If we have any, we print them out and exit
    # with an error.
    bad_licenses = [
        license for license in licenses if license not in ACCEPTABLE_LICENSES
    ]

    bad_packages = {}
    bad_package_check = set()

    for license in bad_licenses:
        bad_packages_for_license = []

        for package in licenses_json[license]:
            pkg_tuple = (package["name"], ", ".join(package["versions"]))
            bad_package_check.add(pkg_tuple)
            if (
                package["name"],
                ", ".join(package["versions"]),
            ) not in PACKAGE_EXCEPTIONS:
                bad_packages_for_license.append(package)

        if len(bad_packages_for_license) > 0:
            bad_packages[license] = bad_packages_for_license

    # Discover dependency exceptions that are no longer used and can be
    # jettisoned, and print them out with a warning.
    unused_exceptions = PACKAGE_EXCEPTIONS.difference(bad_package_check)
    if len(unused_exceptions) > 0:
        for exception in sorted(list(unused_exceptions)):
            print(f"Unused package exception, please remove: {exception}")

    if len(bad_packages) > 0:
        for license in bad_packages:
            for package in bad_packages[license]:
                print(
                    f"Unacceptable license: '{license}' (in {package['name']} version {', '.join(package['versions'])})"
                )
        sys.exit(1)

    print(f"No unacceptable licenses")
    sys.exit(0)


def main() -> NoReturn:
    # Run `pnpm licenses` for lib.
    licenses_output = subprocess.check_output(
        [
            "pnpm",
            "licenses",
            "list",
            "--json",
            "--prod",
        ],
        cwd=str(FRONTEND_DIR),
    ).decode()

    check_licenses(licenses_output)


if __name__ == "__main__":
    main()
