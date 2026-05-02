import cranberry as cb


@cb.enum(strict=True)
class Format:
    JSON = "json"
    CSV = "csv"
    TEXT = "text"


@cb.command("export")
@cb.description("Export data in a chosen format.")
class ExportCommand:
    output: str = cb.option(
        "-o", "--output", help="Destination file path", required=True
    )
    fmt: Format = cb.option(
        "-f", "--format", help="Output format", type=Format, default="json"
    )
    quiet: bool = cb.flag("-q", "--quiet", help="Suppress progress output")


@cb.command("validate")
@cb.description("Validate an input file.")
class ValidateCommand:
    path: str = cb.file(
        "-p", "--path", help="File to validate", exists=True, required=True
    )


@cb.globals()
class GlobalOptions:
    verbose: bool = cb.flag("-v", "--verbose", help="Enable verbose logging")


@cb.app("myapp")
@cb.description("A sample CLI built with cranberry.")
@cb.version("1.0.0")
@cb.help(subcommand=True)
@cb.subcommand(ExportCommand, ValidateCommand)
@cb.style("colorful")
@cb.footer("Run 'myapp help' for usage details.")
def main():
    ctx = cb.parse_args()

    match ctx.command:
        case ExportCommand() as cmd:
            if not cmd.quiet:
                print(f"Exporting to {cmd.output} as {cmd.fmt}...")
        case ValidateCommand() as cmd:
            print(f"Validating {cmd.path}...")
        case None:
            print("No subcommand given. Try --help.")

    if ctx.verbose:  # pyrefly: ignore[missing-attribute]
        print("[verbose mode enabled]")


if __name__ == "__main__":
    main()
