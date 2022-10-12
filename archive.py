#!/usr/bin/python3
#
# Copyright 2010-2022 JetBrains s.r.o. Use of this source code is governed by the Apache 2.0 license

import argparse
import utils
import shutil
import hashlib
import os


def create_archive(input_directory, output_path, compression, dry_run=False) -> str:
    base_directory, archive_prefix = os.path.split(os.path.normpath(input_directory))
    return shutil.make_archive(output_path, compression, base_directory, archive_prefix, dry_run=dry_run)


def create_checksum_file(input_path, output_path):
    chunk_size = 4096
    checksum = hashlib.sha256()
    with open(input_path, "rb") as input_contents:
        for chunk in iter(lambda: input_contents.read(chunk_size), b""):
            checksum.update(chunk)
    print(checksum.hexdigest(), file=open(output_path, "w"))
    return True


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build LLVM from sources for Kotlin/Native toolchain")
    utils.add_common_args(parser)
    parser.add_argument("--input", type=str, default=None,
                        help="Location of LLVM distribution")
    parser.add_argument("--output", type=str, default=None,
                        help="Output path")
    parser.add_argument("--compression", type=str, default='zip',
                        help="Archive format: gztar|zip")
    parser.add_argument("--checksum", action='store_true',
                        help="Create SHA256 of archive")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    utils.setup_environment(args)
    archive = create_archive(args.input, args.output, compression=args.compression, dry_run=args.dry_run)
    print("Created " + archive + " from " + utils.absolute_path(args.input))
    if args.checksum:
        create_checksum_file(archive, f"{archive}.sha256")


if __name__ == "__main__":
    main()
