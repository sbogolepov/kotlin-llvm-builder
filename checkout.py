#!/usr/bin/python3
#
# Copyright 2010-2022 JetBrains s.r.o. Use of this source code is governed by the Apache 2.0 license
import argparse
import os
import shutil
import sys

import utils


git = 'git'


def clone_llvm_repository(repo, branch, llvm_repo_destination, dry_run):
    """
    Downloads a single commit from the given repository.
    """
    # Temporary hack.
    if os.path.exists(llvm_repo_destination):
        return utils.absolute_path(llvm_repo_destination)
    if utils.host_is_darwin():
        default_repo, default_branch = "https://github.com/apple/llvm-project", "apple/stable/20200714"
    else:
        default_repo, default_branch = "https://github.com/llvm/llvm-project", "release/11.x"
    repo = default_repo if repo is None else repo
    branch = default_branch if branch is None else branch
    # Download only single commit because we don't need whole history just for building LLVM.
    utils.run_command([git, "clone", repo, "--branch", branch, "--depth", "1", "llvm-project"], dry_run)
    return utils.absolute_path(llvm_repo_destination)


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Checkout LLVM sources for Kotlin/Native toolchain")

    parser.add_argument("--repo", type=str, default=None)
    parser.add_argument("--branch", type=str, default=None)
    parser.add_argument("--output", type=str, default="llvm-project",
                        help="Where LLVM repository should be downloaded.")

    parser.add_argument("--dry-run", action='store_true',
                        help="Only print commands, do not run")
    parser.add_argument("--git", type=str, default=None,
                        help="Override path to git")

    return parser


def setup(args):
    global git
    if args.git:
        git = args.git
    elif shutil.which('git') is None:
        sys.exit("'git' is not found. Install or provide via --git argument.")


def main():
    parser = build_parser()
    args = parser.parse_args()
    setup(args)
    clone_llvm_repository(args.repo, args.branch, args.output, dry_run=args.dry_run)


if __name__ == "__main__":
    main()
