# cranberry

**cranberry** is a Python library for building expressive, decorator-driven command-line interfaces. It provides a clean API for defining subcommands, typed arguments, global options, enums, and rich help output - all from plain Python classes and functions.

---

## Features

- Define subcommands as plain Python classes decorated with `@cb.command`.
- Declare typed arguments, options, flags, file and directory inputs with `cb.arg`, `cb.option`, `cb.flag`, `cb.file`, and `cb.dir`.
- First-class enum support via `@cb.enum` with strict or permissive validation.
- Global options that are parsed before subcommand dispatch and accessible directly on the context.
- Nested subcommand trees with automatic chain resolution.
- Built-in `--help` and `--version` flags (and optional `help` / `version` subcommands).
- Three built-in rendering styles - `plain`, `colorful`, and `fancy` - plus a `Style` base class for custom themes.
- Validation callbacks, file existence checks, and per-argument type coercion.
- Mixin-based field inheritance for sharing option groups across commands.

---

## Installation

```bash
pip install git+https://github.com/chriso345/cranberry
```

---

## Usage

The following example defines a small CLI with two subcommands and a global flag.

```python
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
```

Running `myapp --help` produces:

```
Usage: myapp [OPTIONS] <COMMAND>

Commands:
  export    Export data in a chosen format.
  validate  Validate an input file.
  help      Display this help message and exit.

Flags:
  -h, --help     Display this help message and exit.
  -V, --version  Display version information and exit.

Global Options:
  -v, --verbose  Enable verbose logging

Run 'myapp help' for usage details.
```

---

## Enums

`@cb.enum` turns a plain class into a validated string enum. In strict mode, only declared values are accepted; non-strict mode allows any unknown value through.

```python
@cb.enum(strict=True)
class Color:
    RED = "red"
    GREEN = "green"
    BLUE = "blue"


@cb.command("paint")
class PaintCommand:
    color: Color = cb.option("-c", "--color", type=Color, help="Color to apply")
```

Enum instances compare equal to their string values, so `cmd.color == "red"` works as expected.

---

## Global Options

Mark a class with `@cb.globals()` to declare options that are parsed before subcommand dispatch and attached directly to the `ParseContext`.

```python
@cb.globals()
class Globals:
    config: str = cb.option("-c", "--config", help="Path to config file")

# Accessible as ctx.config after parse_args()
```

---

## Field Inheritance

Share common fields across commands using plain Python inheritance or mixin classes.

```python
class PaginationMixin:
    page: int = cb.option("-p", "--page", type=int, default=1, help="Page number")
    limit: int = cb.option(
        "-l", "--limit", type=int, default=20, help="Results per page"
    )


@cb.command("list-users")
class ListUsersCommand(PaginationMixin):
    filter: str = cb.option("-f", "--filter", help="Filter string")
```

---

## Styles

Three built-in styles control the appearance of help output:

| Style      | Description                                    |
|------------|------------------------------------------------|
| `plain`    | No ANSI codes; safe for all terminals.         |
| `colorful` | Tasteful color accents using true-color ANSI.  |
| `fancy`    | Bolder palette with underlined headings.       |

A custom style can be created by subclassing `cb.Style` and overriding individual methods.

```python
from cranberry import Style


class MyStyle(Style):
    def heading(self, text: str) -> str:
        return f">>> {text}"


@cb.app("myapp")
@cb.style(MyStyle)
def main(): ...
```

---

## License

Licensed under the MIT License. See the [LICENSE](LICENSE) file for more details.
