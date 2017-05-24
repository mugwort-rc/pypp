#!/usr/bin/env python3

from __future__ import absolute_import

import argparse
import os
import sys

from jinja2 import Environment, PackageLoader


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("class_name")
    parser.add_argument("--template", default="defvisitor.hpp")
    parser.add_argument("--append-cwd", default=False, action="store_true")

    args = parser.parse_args()

    if args.append_cwd:
        sys.path.append(os.getcwd())
    env = Environment(
        loader=PackageLoader("pypp", "templates"),
    )

    template = env.get_template(args.template)
    print(template.render({
        "class_name": args.class_name,
    }))

    return 0


if __name__ == "__main__":
    sys.exit(main())
