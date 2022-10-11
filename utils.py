import os
import sys
import shlex
import shutil
import subprocess
import urllib.request
from typing import List


vsdevcmd = None
isysroot = None
ninja = 'ninja'
cmake = 'cmake'
git = 'git'


def detect_vsdevcmd():
    """
    Use vswhere (and download it, if needed) utility to find path to vsdevcmd.bat.
    :return: path to vsdevcmd.bat
    """
    vswhere = shutil.which('vswhere')
    if vswhere is None:
        print("Downloading vswhere utility to detect path to vsdevcmd.bat automatically")
        vswhere_url = "https://github.com/microsoft/vswhere/releases/download/2.8.4/vswhere.exe"
        urllib.request.urlretrieve(vswhere_url, 'vswhere.exe')
        vswhere = shutil.which('vswhere')
        if vswhere is None:
            sys.exit("Failed to retrieve vswhere utility. Please provide path to vsdevcmd.bat with --vsdevcmd")
    vswhere_args = [vswhere, '-prerelease', '-latest', '-property', 'installationPath']
    path_to_visual_studio = subprocess.check_output(vswhere_args, universal_newlines=True).rstrip()
    vsdevcmd_path = os.path.join(path_to_visual_studio, "Common7", "Tools", "vsdevcmd.bat")
    if not os.path.isfile(vsdevcmd_path):
        sys.exit("vsdevcmd.bat is not found. Please provide path to vsdevcmd.bat with --vsdevcmd")
    else:
        print("Found vsdevcmd.bat: " + vsdevcmd_path)
    return vsdevcmd_path


def detect_xcode_sdk_path():
    """
    Get an absolute path to macOS SDK.
    """
    return subprocess.check_output(['xcrun', '--show-sdk-path'], universal_newlines=True).rstrip()


def absolute_path(path):
    if path is not None:
        # CMake is not tolerant to backslashes in path.
        return os.path.abspath(path).replace('\\', '/')
    else:
        return None


def host_is_windows():
    return sys.platform == "win32"


def host_is_linux():
    return sys.platform == "linux"


def host_is_darwin():
    return sys.platform == "darwin"


def run_command(command: List[str], dry_run):
    """
    Execute single command in terminal/cmd.

    Note that on Windows we prepare environment with vsdevcmd.bat.
    """
    if host_is_windows():
        if vsdevcmd is None:
            sys.exit("'VsDevCmd.bat' is not set!")
        command = [vsdevcmd, "-arch=amd64", "&&"] + command
        print("Running command: " + ' '.join(command))
    else:
        command = [shlex.quote(arg) for arg in command]
        command = ' '.join(command)
        print("Running command: " + command)

    if not dry_run:
        subprocess.run(command, shell=True, check=True)


def add_common_args(parser):
    # Environment setup.
    parser.add_argument("--vsdevcmd", type=str, default=None,
                        help="(Windows only) Path to VsDevCmd.bat")
    parser.add_argument("--ninja", type=str, default=None,
                        help="Override path to ninja")
    parser.add_argument("--cmake", type=str, default=None,
                        help="Override path to cmake")
    parser.add_argument("--git", type=str, default=None,
                        help="Override path to git")
    parser.add_argument("--isysroot", type=str, default=None,
                        help="(macOS only) Override path to macOS SDK")
    # Misc.
    parser.add_argument("--dry-run", action='store_true', help="Only print commands, do not run")


def setup_environment(args):
    """
    Setup globals that store information about script execution environment.
    """
    global vsdevcmd, ninja, cmake, git, isysroot
    # TODO: We probably can download some of these binaries ourselves.
    if args.ninja:
        ninja = args.ninja
    elif shutil.which('ninja') is None:
        sys.exit("'ninja' is not found. Install or provide via --ninja argument.")
    if args.cmake:
        cmake = args.cmake
    elif shutil.which('cmake') is None:
        sys.exit("'cmake' is not found. Install or provide via --cmake argument.")
    if args.git:
        git = args.git
    elif shutil.which('git') is None:
        sys.exit("'git' is not found. Install or provide via --git argument.")
    if host_is_windows():
        if args.vsdevcmd:
            vsdevcmd = args.vsdevcmd
        else:
            vsdevcmd = detect_vsdevcmd()
    elif host_is_darwin():
        if args.isysroot:
            isysroot = args.isysroot
        else:
            isysroot = detect_xcode_sdk_path()