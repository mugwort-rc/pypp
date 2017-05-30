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
    parser.add_argument("--with-example", default=False, action="store_true")

    args = parser.parse_args()

    env = Environment(
        loader=PackageLoader("pypp", "templates"),
    )

    template = env.get_template(args.template)
    print(template.render({
        "class_name": args.class_name,
        "with_example": args.with_example,
    }))

    return 0


if __name__ == "__main__":
    sys.exit(main())
