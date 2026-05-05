"""
# Using this Example:

Show top-level help
  $ python3 examples/example.py --help

Show help via subcommand (if enabled)
  $ python3 examples/example.py help

Show subcommand help
  $ python3 examples/example.py sub --help
  $ python3 examples/example.py sub help

Basic subcommand usage
  $ python3 examples/example.py sub -o "value" -f "John" 30 home work

Alternate command
  $ python3 examples/example.py alternate -a "something"

Show version
  $ python3 examples/example.py --version

- Global flags can appear before or after the subcommand.

- Positional arguments must follow declared order:
    NAME AGE LOCATION LOCATION

- Enum values are validated:
    LOCATION must be one of: home, work

- File validation:
    --input-file must exist and end with ".txt"

- Cranberry will error (panic) if:
    - required arguments are missing
    - unknown flags are used
    - enum values are invalid
    - file/directory constraints are not met
"""

import cranberry as cb


# ---------------------------------------------------------------------------
# Shared / reusable components
# ---------------------------------------------------------------------------
class FlattenedNested:
    """Fields mixed directly into parent commands."""

    nested_option: str = cb.option(
        "-n", "--nested-option", help="A nested option (flattened into parent)"
    )


@cb.enum(strict=True)
class Location:
    """Allowed location values."""

    HOME = "home"
    WORK = "work"


# ---------------------------------------------------------------------------
# Commands
# ---------------------------------------------------------------------------
@cb.command("nested")
@cb.description("A nested subcommand (not flattened).")
class NestedCommand:
    nested_flag: bool = cb.flag("-nf", "--nested-flag", help="A nested flag")


@cb.command("sub")
@cb.description("Primary subcommand demonstrating most features.")
@cb.subcommand(NestedCommand)
class SubCommand(FlattenedNested):
    # Options / flags
    option: str = cb.option("-o", "--option", help="A simple option")
    flag: bool = cb.flag("-f", "--flag", help="A boolean flag", stackable=True)
    flag2: bool = cb.flag("-F", "--flag2", help="Another boolean flag", stackable=True)

    # File / directory inputs
    file: str = cb.file(
        "-i",
        "--input-file",
        help="Input file (must be .txt)",
        validate=(lambda x: x.endswith(".txt"), "Must end with .txt"),
        exists=True,
    )
    directory: str = cb.dir("-d", "--input-directory", help="Input directory")

    # Positional arguments
    name: str = cb.arg(help="User name")
    age: int = cb.arg(help="User age", type=int)

    locations: list[Location] = cb.arg(
        help="Exactly two locations",
        count=2,
        enforce_count=True,
        type=Location,
    )


@cb.command("alternate")
@cb.description("Simpler alternative command.")
class AlternateCommand:
    alternate_option: str = cb.option(
        "-a", "--alternate-option", help="An alternate option"
    )


# ---------------------------------------------------------------------------
# Global options
# ---------------------------------------------------------------------------
@cb.globals()
class Globals:
    global_flag: bool = cb.flag(
        "-g", "--global-flag", help="Enable global flag", default=False
    )


# ---------------------------------------------------------------------------
# App entrypoint
# ---------------------------------------------------------------------------
@cb.app("cranberry_cli_example")  # This can be replaced with __file__ for the filename.
@cb.description("Example app showcasing Cranberry CLI features.")
@cb.version("0.0.1", subcommand=True)
@cb.help(subcommand=True)
@cb.subcommand(SubCommand, AlternateCommand)
@cb.style("colorful")
@cb.footer("Thanks for trying Cranberry!")
def main():
    ctx = cb.parse_args()

    # ---------------------------------------------------------------------
    # Dispatch
    # ---------------------------------------------------------------------
    match ctx.command:
        case SubCommand() as cmd:
            # TODO: This is a bit messy, therefore we need a better way to detect/display nested subcommands.
            print("-> SubCommand")
            try:
                if cmd.subcommand:  # pyrefly: ignore[missing-attribute]
                    if cmd.subcommand:
                        print("  -> NestedCommand")
                        print(f"    nested_flag   = {cmd.subcommand.nested_flag}")  # pyrefly: ignore[missing-attribute]
            except Exception:
                print(f"    option        = {cmd.option}")
                print(f"    flag          = {cmd.flag}")
                print(f"    file          = {cmd.file}")
                print(f"    directory     = {cmd.directory}")
                print(f"    name          = {cmd.name}")
                print(f"    age           = {cmd.age}")
                print(f"    locations     = {cmd.locations}")
                print(f"    nested_option = {cmd.nested_option}")

        case AlternateCommand() as cmd:
            print("-> AlternateCommand")
            print(f"    alternate_option = {cmd.alternate_option}")

        case None:
            print(ctx.help())

    # TODO: This is a bit messy as it is dynamically added to the context.
    print(f"\nglobal_flag = {ctx.global_flag}")  # pyrefly: ignore[missing-attribute]


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
