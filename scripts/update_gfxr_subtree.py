# Testing instructions:
#
# Merge main
# Push main to fork
# Open GitHub actions
# Find GFXR subtree pull
# Run job

import argparse
import enum
import logging
import pathlib
import shutil
import subprocess
import sys

LOGGER = logging.getLogger()


class CmakeGenerator(enum.StrEnum):
    NINJA_MULTI_CONFIG = "Ninja Multi-Config"


class Cmake:
    def __init__(self, exe: pathlib.Path):
        self._exe = exe

    def configure(
        self,
        source_directory: pathlib.Path,
        build_directory: pathlib.Path,
        generator: CmakeGenerator,
    ):
        run(
            [
                str(self._exe),
                str(source_directory),
                "-B",
                str(build_directory),
                "-G",
                str(generator),
            ]
        )

    def build(self, build_directory: pathlib.Path):
        run([str(self._exe), "--build", str(build_directory)])


class ScriptExecutor:
    def __init__(self, exe: pathlib.Path):
        self._exe = exe

    def run(self, script: pathlib.Path, args: list[str] = []):
        command = [str(self._exe), str(script), *args]
        run(command)


class GitSubmodule:
    def __init__(self, exe: pathlib.Path):
        self._exe = exe

    def update(self, init: bool, recursive: bool):
        command = [str(self._exe), "submodule", "update"]
        if init:
            command.append("--init")
        if recursive:
            command.append("--recursive")
        run(command)


class GitSubtree:
    def __init__(self, exe: pathlib.Path):
        self._exe = exe

    def pull(self, prefix: str, remote: str, ref: str, squash: bool):
        command = [
            str(self._exe),
            "subtree",
            "pull",
            f"--prefix={prefix}",
            remote,
            ref,
        ]
        if squash:
            command.append("--squash")
        run(command)


class Git:
    def __init__(self, exe: pathlib.Path):
        self._subtree = GitSubtree(exe)
        self._submodule = GitSubmodule(exe)

    @property
    def subtree(self):
        return self._subtree

    @property
    def submodule(self):
        return self._submodule


def run(cmd: list[str]):
    LOGGER.debug(cmd)
    subprocess.check_call(cmd)


def parse_args() -> argparse.Namespace:
    def validate_program_path(path: str) -> pathlib.Path:
        which = shutil.which(path)
        if which is None:
            raise argparse.ArgumentTypeError(f"can't find program: {path}")

        return pathlib.Path(which)

    parser = argparse.ArgumentParser()
    parser.add_argument(
        "--git",
        type=validate_program_path,
        default="git",
    )
    parser.add_argument(
        "--cmake",
        type=validate_program_path,
        default="cmake",
    )
    parser.add_argument(
        "--ninja",
        type=validate_program_path,
        default="ninja",
    )
    parser.add_argument(
        "--shell",
        type=validate_program_path,
        default="bash",
    )
    default_dive_root = pathlib.Path(__file__).parent.parent
    parser.add_argument(
        "--dive_root",
        type=pathlib.Path,
        default=default_dive_root,
    )
    parser.add_argument(
        "--build_root",
        type=pathlib.Path,
        default=default_dive_root / "build" / "host",
    )
    return parser.parse_args()


def main(args: argparse.Namespace):
    logging.basicConfig(level=logging.DEBUG)

    git = Git(args.git)
    python = ScriptExecutor(pathlib.Path(sys.executable))
    cmake = Cmake(args.cmake)
    sh = ScriptExecutor(args.shell)

    git.subtree.pull(
        prefix="third_party/gfxreconstruct",
        remote="https://github.com/LunarG/gfxreconstruct.git",
        ref="dev",
        squash=True,
    )
    python.run(args.dive_root / "scripts" / "incorporate_gfxr_submodules.py")
    git.submodule.update(init=True, recursive=True)
    python.run(
        args.dive_root
        / "third_party"
        / "gfxreconstruct"
        / "framework"
        / "generated"
        / "generate_vulkan.py"
    )
    cmake.configure(
        source_directory=args.dive_root,
        build_directory=args.build_root,
        generator=CmakeGenerator.NINJA_MULTI_CONFIG,
    )
    cmake.build(args.build_root)
    sh.run(args.dive_root / "scripts" / "build_android.sh")
    print("Done!")


if __name__ == "__main__":
    main(parse_args())
