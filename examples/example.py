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
  $ python3 examples/example.py sub -o "value" -f \
      --input-file input.txt \
      --input-directory ./data \
      "John" 30 home work

Using nested subcommand
  $ python3 examples/example.py sub nested -nf \
      -o "value" \
      --input-file input.txt \
      --input-directory ./data \
      "John" 30 home work

Using global flags
  $ python3 examples/example.py -g sub -o "value" \
      --input-file input.txt \
      --input-directory ./data \
      "John" 30 home work

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
    flag: bool = cb.flag("-f", "--flag", help="A boolean flag")

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
@cb.version("0.1.0", subcommand=True)
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
            print("-> SubCommand\n")
            print(f"option        = {cmd.option}")
            print(f"flag          = {cmd.flag}")
            print(f"file          = {cmd.file}")
            print(f"directory     = {cmd.directory}")
            print(f"name          = {cmd.name}")
            print(f"age           = {cmd.age}")
            print(f"locations     = {cmd.locations}")
            print(f"nested_option = {cmd.nested_option}")

            if cmd.subcommand:
                print("\n→ NestedCommand")
                print(f"nested_flag   = {cmd.subcommand.nested_flag}")

        case AlternateCommand() as cmd:
            print("-> AlternateCommand\n")
            print(f"alternate_option = {cmd.alternate_option}")

        case None:
            print("-> No subcommand provided")

    print(f"\nglobal_flag = {ctx.global_flag}")


# ---------------------------------------------------------------------------
# Entry point
# ---------------------------------------------------------------------------
if __name__ == "__main__":
    main()
