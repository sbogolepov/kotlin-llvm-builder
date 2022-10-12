#!/usr/bin/python3
#
# Copyright 2010-2022 JetBrains s.r.o. Use of this source code is governed by the Apache 2.0 license

import argparse
import json
import utils
import os
import sys
import pathlib
from typing import List


def user_dist_components():
    components = ["clang", "libclang", "lld", "llvm-cov", "llvm-profdata", "llvm-ar", "clang-resource-headers"]
    if utils.host_is_linux():
        components.append("compiler_rt")
    return components


def bootstrap_flags():
    if utils.host_is_darwin():
        # Don't waste time by doing unnecessary work for throwaway toolchain.
        return [
            '-DCOMPILER_RT_BUILD_CRT=OFF',
            '-DCOMPILER_RT_BUILD_LIBFUZZER=OFF',
            '-DCOMPILER_RT_BUILD_SANITIZERS=OFF',
            '-DCOMPILER_RT_BUILD_XRAY=OFF',
            '-DCOMPILER_RT_ENABLE_IOS=OFF',
            '-DCOMPILER_RT_ENABLE_WATCHOS=OFF',
            '-DCOMPILER_RT_ENABLE_TVOS=OFF',
        ]
    else:
        return []


def dist_flags():
    final_distribution_symlinks = [
        # These links are actually copies on windows, so they're wasting precious disk space.
        "-DCLANG_LINKS_TO_CREATE=clang++",
        "-DLLD_SYMLINKS_TO_CREATE=ld.lld;wasm-ld"
    ]
    # Make distribution much smaller by linking to dynamic library
    # instead of static linkage.
    # Not working for Windows yet.
    #
    # Also not working for Linux and macOS because of signal chaining.
    # TODO: Enable after LLVM distribution patching.
    # if not utils.host_is_windows():
    #    cmake_args.append("-DLLVM_BUILD_LLVM_DYLIB=OFF")
    #    cmake_args.append("-DLLVM_LINK_LLVM_DYLIB=OFF")

    if utils.host_is_darwin():
        platform_flags = ['-DLIBCXX_USE_COMPILER_RT=ON']
    else:
        platform_flags = []

    return final_distribution_symlinks + platform_flags


def platform_common_flags():
    if utils.host_is_windows():
        return [
            # Use MT to make distribution self-contained
            # TODO: Consider -DCMAKE_INSTALL_UCRT_LIBRARIES=ON as an alternative
            '-DLLVM_USE_CRT_RELEASE=MT',
            '-DCMAKE_MSVC_RUNTIME_LIBRARY=MultiThreaded',
            # We don't support PDB, so no need fir DIA.
            '-DLLVM_ENABLE_DIA_SDK=OFF',
        ]
    elif utils.host_is_darwin():
        return ['-DLLVM_ENABLE_LIBCXX=ON']
    elif utils.host_is_linux():
        return []
    else:
        return []


def default_projects():
    return ["clang", "lld", "libcxx", "libcxxabi", "compiler-rt"]


bootstrap_build_config = {
    "target_backends": ["Native"],
    "distribution_components": None,
    "build_targets": ["install"],
    "projects": default_projects(),
    "runtimes": None,
    "build_type": "Release",
    "cmake_flags": bootstrap_flags(),
    "use_default_cmake_flags": True,
}

dev_build_config = {
    "target_backends": None,
    "distribution_components": None,
    "build_targets": ["install-distribution"],
    "projects": default_projects(),
    "runtimes": None,
    "build_type": "Release",
    "cmake_flags": dist_flags(),
    "use_default_cmake_flags": True,
}

user_build_config = {
    "target_backends": None,
    "distribution_components": user_dist_components(),
    "build_targets": ["install-distribution"],
    "projects": default_projects(),
    "runtimes": None,
    "build_type": "Release",
    "cmake_flags": dist_flags(),
    "use_default_cmake_flags": True,
}

common_cmake_args = [
    '-DLLVM_ENABLE_ASSERTIONS=OFF',
    '-DLLVM_ENABLE_TERMINFO=OFF',
    '-DLLVM_INCLUDE_GO_TESTS=OFF',
    '-DLLVM_ENABLE_Z3_SOLVER=OFF',
    '-DCOMPILER_RT_BUILD_BUILTINS=ON',
    '-DLLVM_ENABLE_THREADS=ON',
    '-DLLVM_OPTIMIZED_TABLEGEN=ON',
    '-DLLVM_ENABLE_IDE=OFF',
    '-DLLVM_BUILD_UTILS=ON',
    '-DLLVM_INSTALL_UTILS=ON'
]


class LlvmBuildConfig:
    def __init__(self, config):
        self.build_targets = config["build_targets"]
        self.projects = config["projects"]
        self.runtimes = config["runtimes"]
        self.distribution_components = config["distribution_components"]
        self.target_backends = config["target_backends"]
        self.build_type = config["build_type"]
        self.cmake_flags = config["cmake_flags"]
        self.use_default_cmake_flags = config["use_default_cmake_flags"]


def construct_cmake_flags(
        bootstrap_llvm_path: str = None,
        install_path: str = None,
        config: LlvmBuildConfig = None,
) -> List[str]:
    c_compiler, cxx_compiler, linker, ar = None, None, None, None
    c_flags, cxx_flags, linker_flags = None, None, None

    cmake_args = ['-DCMAKE_BUILD_TYPE=' + config.build_type]
    if config.use_default_cmake_flags:
        cmake_args.extend(platform_common_flags())
    if config.cmake_flags:
        cmake_args.extend(config.cmake_flags)

    if bootstrap_llvm_path is not None:
        if utils.host_is_windows():
            # CMake is not tolerant to backslashes
            c_compiler = f'{bootstrap_llvm_path}/bin/clang-cl.exe'.replace('\\', '/')
            cxx_compiler = f'{bootstrap_llvm_path}/bin/clang-cl.exe'.replace('\\', '/')
            linker = f'{bootstrap_llvm_path}/bin/lld-link.exe'.replace('\\', '/')
            ar = f'{bootstrap_llvm_path}/bin/llvm-lib.exe'.replace('\\', '/')
        elif utils.host_is_linux():
            c_compiler = f'{bootstrap_llvm_path}/bin/clang'
            cxx_compiler = f'{bootstrap_llvm_path}/bin/clang++'
            linker = f'{bootstrap_llvm_path}/bin/ld.lld'
            ar = f'{bootstrap_llvm_path}/bin/llvm-ar'
        elif utils.host_is_darwin():
            c_compiler = f'{bootstrap_llvm_path}/bin/clang'
            cxx_compiler = f'{bootstrap_llvm_path}/bin/clang++'
            # ld64.lld is not that good yet.
            linker = None
            ar = f'{bootstrap_llvm_path}/bin/llvm-ar'
            c_flags = ['-isysroot', utils.isysroot]
            cxx_flags = ['-isysroot', utils.isysroot, '-stdlib=libc++']
            linker_flags = ['-stdlib=libc++']

    if config.target_backends is not None:
        cmake_args.append('-DLLVM_TARGETS_TO_BUILD=' + ";".join(config.target_backends))
    if config.projects is not None:
        cmake_args.append('-DLLVM_ENABLE_PROJECTS=' + ";".join(config.projects))
    if config.runtimes is not None:
        cmake_args.append('-DLLVM_ENABLE_RUNTIMES=' + ";".join(config.runtimes))
    if config.distribution_components:
        cmake_args.append('-DLLVM_DISTRIBUTION_COMPONENTS=' + ';'.join(config.distribution_components))
    if install_path is not None:
        cmake_args.append('-DCMAKE_INSTALL_PREFIX=' + install_path)
    if c_compiler is not None:
        cmake_args.append('-DCMAKE_C_COMPILER=' + c_compiler)
    if cxx_compiler is not None:
        cmake_args.append('-DCMAKE_CXX_COMPILER=' + cxx_compiler)
    if linker is not None:
        cmake_args.append('-DCMAKE_LINKER=' + linker)
    if ar is not None:
        cmake_args.append('-DCMAKE_AR=' + ar)
    if c_flags is not None:
        cmake_args.append("-DCMAKE_C_FLAGS=" + ' '.join(c_flags))
    if cxx_flags is not None:
        cmake_args.append("-DCMAKE_CXX_FLAGS=" + ' '.join(cxx_flags))
    if linker_flags is not None:
        cmake_args.append('-DCMAKE_EXE_LINKER_FLAGS=' + ' '.join(linker_flags))
        cmake_args.append('-DCMAKE_MODULE_LINKER_FLAGS=' + ' '.join(linker_flags))
        cmake_args.append('-DCMAKE_SHARED_LINKER_FLAGS=' + ' '.join(linker_flags))
    return cmake_args


def llvm_build_commands(
        install_path: str,
        bootstrap_path: str,
        llvm_src: str,
        config: LlvmBuildConfig,
) -> List[List[str]]:
    cmake_flags = construct_cmake_flags(bootstrap_path, install_path, config)
    cmake_command = [utils.cmake, "-G", "Ninja"] + cmake_flags + [os.path.join(llvm_src, "llvm")]
    ninja_command = [utils.ninja] + config.build_targets
    return [cmake_command, ninja_command]


def build(
        config: LlvmBuildConfig,
        llvm_src: str,
        build_path: str,
        bootstrap_path: str,
        output_path: str,
        dry_run: bool
):
    commands = llvm_build_commands(
        install_path=utils.absolute_path(output_path),
        bootstrap_path=utils.absolute_path(bootstrap_path),
        llvm_src=utils.absolute_path(llvm_src),
        config=config,
    )
    pathlib.Path(build_path).mkdir(parents=True, exist_ok=True)
    os.chdir(utils.absolute_path(build_path))
    print("Changed working dir to " + build_path)
    for command in commands:
        utils.run_command(command, dry_run=dry_run)


def prepare_config(config_param):
    if config_param == 'predefined/bootstrap':
        config = bootstrap_build_config
    elif config_param == 'predefined/dev':
        config = dev_build_config
    elif config_param == 'predefined/user':
        config = user_build_config
    elif config_param is None:
        sys.exit('Error: build config is not selected')
    else:
        print("Using build config from " + config_param)
        with open(config_param) as f:
            json_string = f.read()
            config = json.loads(json_string)
    return config


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(description="Build LLVM from sources for Kotlin/Native toolchain")
    utils.add_common_args(parser)
    parser.add_argument("--sources", dest="llvm_src", type=str, default=None,
                        help="Location of LLVM sources")
    parser.add_argument("--bootstrap-path", type=str, default=None,
                        help="Path to LLVM distribution that should be used as a bootstrap")
    parser.add_argument("--config", type=str, default=None,
                        help="Configure LLVM build parameters. Either `predefined/(bootstrap, user, dev)`, or path to json config")
    parser.add_argument("--output", default="llvm-dist",
                        help="Output path")
    parser.add_argument("--build-path", type=str, default="build",
                        help="Path to directory that should store intermediate build files")
    return parser


def main():
    parser = build_parser()
    args = parser.parse_args()
    utils.setup_environment(args)
    config_dict = prepare_config(args.config)
    print("Building LLVM with the following configuration:")
    print(json.dumps(config_dict, indent=2))
    llvm_config = LlvmBuildConfig(config_dict)
    build(
        config=llvm_config,
        llvm_src=args.llvm_src,
        bootstrap_path=args.bootstrap_path,
        build_path=args.build_path,
        output_path=args.output,
        dry_run=args.dry_run,
    )


if __name__ == "__main__":
    main()
