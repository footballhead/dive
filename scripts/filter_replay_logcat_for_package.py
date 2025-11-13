import argparse
import pathlib
import typing


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("file")
    parser.add_argument("capture_file_filter")
    return parser.parse_args()


def print_until_replay_end(text_io: typing.TextIO):
    for line in text_io:
        if "====== Exiting android_main" in line:
            return
        print(line, end="")


def main(args: argparse.Namespace):
    with pathlib.Path(args.file).open("r") as text_io:
        for line in text_io:
            if args.capture_file_filter in line:
                print_until_replay_end(text_io)
                return


if __name__ == "__main__":
    main(parse_args())
