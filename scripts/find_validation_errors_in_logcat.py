import argparse
import dataclasses
import enum
import re
import sys
import typing

# Output from `adb logcat` (default format is threadtime)
#
# example: `11-12 16:43:05.716 11044 11085 E gfxrecon: `
#          `%m-%d %H:%M:%S.%3N <PID> <TID> * <TAG>: `
_GFXRECON_LOGCAT_THREADTIME_REGEX = (
    r"\d{2}-\d{2} +\d{2}:\d{2}:\d{2}.\d{3} +\d+ +\d+ +[IEVWDF] +gfxrecon: "
)
_DEBUG_MESSENGER_PREFIX = "DEBUG MESSENGER: "
_FILE_READ_FROM_STDIN = "-"
_OUTPUT_TO_STDOUT = "-"
_MESSAGE_LIMIT_INDICATOR = "duplicate_message_limit"
_COLON_SPLIT_SEPARATOR = ": "


@dataclasses.dataclass
class ErrorStats:
    """Aggregated validation error statistics"""

    count: int
    messages: set[str]


@dataclasses.dataclass
class Error:
    """Singular error in logcat. Could encompass multiple lines of output."""

    vuid: str
    detailed_message: str
    summary_message: str


@dataclasses.dataclass
class ErrorHeader:
    """Parsed results of the first line of a validation error in logcat"""

    vuid: str
    message_limit_reached: bool
    message: str


class _ReportFormat(enum.StrEnum):
    """Types of reports that this program can generate"""

    TEXT = enum.auto()
    HTML = enum.auto()


class _TextReportGenerator:
    """Generates a report with little formatting"""

    def __init__(self, file_object: typing.TextIO):
        """file_object is where the report will be written to"""
        self._file_object = file_object

    def report_validation_error(self, message: str) -> None:
        self._write(message)

    def report_statistics(self, error_stats: dict[str, ErrorStats]) -> None:
        """Write aggregated statistics to the report"""
        self._write("Summary:")
        for vuid in error_stats:
            self._write(f" {vuid}: {error_stats[vuid].count}")
        self._write("")

        self._write("Unique errors:")
        for vuid in error_stats:
            for error in error_stats[vuid].messages:
                self._write(f"  {error}")

    def _write(self, txt: str) -> None:
        self._file_object.write(f"{txt}\n")


class _HtmlReportGenerator:
    """Generates a report with basic HTML formatting.

    The implementation forces a strict function call sequence:
    report_statistics() must be called last and the object must not be used afterwards.

    Example:
        reporter = HtmlReportGenerator(sys.stdout)
        reporter.report_validation_error('a')
        reporter.report_validation_error('b')
        reporter.report_validation_error('c')
        ...
        reporter.report_statistics(aggregated_stats)
    """

    def __init__(self, file_object: typing.TextIO):
        """file_object is where the report will be written to"""
        self._file_object = file_object

        self._write("<!DOCTYPE html>")
        self._write("<html>")
        self._write(
            "<head><style>td, th { border: 1px solid black; } table { border-collapse: collapse; }</style></head>"
        )
        self._write("<body>")
        self._write("<h1>Errors</h1>")
        # Start raw errors section (assuming report_validation_error called next)
        self._write("<table><tbody>")

    def report_validation_error(self, message: str):
        """Must not be called after report_statistics."""
        self._write("<tr><td>")
        self._write(message)
        self._write("</td></tr>")

    def report_statistics(self, error_stats: dict[str, ErrorStats]):
        """Must be called last. The object must not be used after calling."""
        # End previous section (assumed called last)
        self._write("</tbody></table>")

        self._write("<h1>Summary</h1>")
        self._write("<table><thead><tr><th>VUID</th><th>Count</th></tr></thead><tbody>")
        for vuid in error_stats:
            self._write(f"<tr><td>{vuid}</td><td>{error_stats[vuid].count}</td></tr>")
        self._write("</tbody></table>")

        self._write("<h1>Unique errors</h1>")
        self._write("<table><thead><tr><th>VUID</th><th>Error</th></tr></thead><tbody>")
        for vuid in error_stats:
            for error in error_stats[vuid].messages:
                self._write(f"<tr><td>{vuid}</td><td>{error}</td></tr>")
        self._write("</tbody></table>")

        # Finalize HTML file (assumed called last)
        self._write("</body></html>")

    def _write(self, txt: str) -> None:
        self._file_object.write(f"{txt}\n")


def _next_gfxrecon_line(f: typing.TextIO) -> str | None:
    """Parses the log message from the next gfxrecon tagged logcat line in a
    text file object. Returns None if the end of file is reached."""
    while True:
        line = f.readline()
        if not line:
            break

        result = re.match(_GFXRECON_LOGCAT_THREADTIME_REGEX, line)
        if not result:
            continue

        # Strip the logcat gubbins; we only care about the log message from the app
        return line[len(result.group(0)) :]

    return None


def _is_start_of_validation_error(line: str) -> bool:
    return _DEBUG_MESSENGER_PREFIX in line


def _is_message_limit_reached(line: str) -> bool:
    return _MESSAGE_LIMIT_INDICATOR in line


class NotAHeaderError(Exception):
    pass


def _parse_validation_header(line: str) -> ErrorHeader:
    """Extract relevant information from the first line of a validation error"""
    # DEBUG MESSENGER: Frame #X: VUID-FOO: <rest of message>
    fields = line.split(_COLON_SPLIT_SEPARATOR, maxsplit=3)
    if len(fields) != 4:
        # Check _is_start_of_validation_error first
        raise NotAHeaderError(fields)

    vuid = fields[2]
    message = fields[3]
    message_limit_reached = _is_message_limit_reached(message)

    return ErrorHeader(
        vuid=vuid, message_limit_reached=message_limit_reached, message=message
    )


def _next_validation_error(f: typing.TextIO) -> Error | None:
    """Parses relevant information about the gfxrecon validation error in the
    logcat from a text file object. Returns None if the end of file is
    reached."""
    while True:
        # The first line contains:
        #
        # 1. the start-of-error indicator
        # 2. the VUID
        # 3. either:
        #    a. info about whether the message limit was reached
        #    b. the beginning of the error message
        header_line = _next_gfxrecon_line(f)
        if header_line is None:
            break

        if not _is_start_of_validation_error(header_line):
            continue

        error_header = _parse_validation_header(header_line)

        detailed_message = header_line
        summary_message: str = (
            "" if error_header.message_limit_reached else error_header.message
        )

        # Second and (optional) third lines are pure error message
        additional_line = _next_gfxrecon_line(f)
        if additional_line is None:
            break
        detailed_message += additional_line
        summary_message += additional_line

        if error_header.message_limit_reached:
            additional_line = _next_gfxrecon_line(f)
            if additional_line is None:
                break
            detailed_message += additional_line
            summary_message += additional_line

        return Error(
            vuid=error_header.vuid,
            detailed_message=detailed_message,
            summary_message=summary_message,
        )

    return None


def _parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser()
    parser.add_argument("file", help="Use - for stdin")
    parser.add_argument(
        "-r",
        "--report",
        type=_ReportFormat,
        choices=[str(choice) for choice in _ReportFormat],
        default=_ReportFormat.TEXT,
    )
    parser.add_argument(
        "-o", "--output", default=_OUTPUT_TO_STDOUT, help="Use - for stdout"
    )
    return parser.parse_args()


def _main(args: argparse.Namespace):
    in_file = sys.stdin if args.file == _FILE_READ_FROM_STDIN else open(args.file, "r")
    out_file = (
        sys.stdout if args.output == _OUTPUT_TO_STDOUT else open(args.output, "w")
    )

    match args.report:
        case _ReportFormat.TEXT:
            reporter = _TextReportGenerator(out_file)
        case _ReportFormat.HTML:
            reporter = _HtmlReportGenerator(out_file)
        case _:
            raise NotImplementedError("Unimplemented --report")

    # Key is VUID
    error_stats: dict[str, ErrorStats] = {}

    while True:
        error = _next_validation_error(in_file)
        if error is None:
            break

        reporter.report_validation_error(error.detailed_message)

        vuid = error.vuid
        if vuid not in error_stats:
            error_stats[vuid] = ErrorStats(count=0, messages=set())
        error_stats[vuid].count += 1
        error_stats[vuid].messages.add(error.summary_message)

    reporter.report_statistics(error_stats)


if __name__ == "__main__":
    _main(_parse_args())
