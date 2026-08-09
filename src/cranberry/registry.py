"""
Cranberry field registry.

"""

from __future__ import annotations

from typing import Any, get_type_hints

from cranberry.errors import panic
from cranberry.fields import FieldSpec


def _is_cranberry_enum(tp: Any) -> bool:
    """Return *True* if *tp* is a class produced by ``@cb.enum``."""
    from cranberry.enum import CranberryEnum  # local import avoids cycle

    try:
        return isinstance(tp, type) and issubclass(tp, CranberryEnum)
    except TypeError:
        return False


def _unwrap_list(tp: Any) -> tuple[bool, Any]:
    """
    If *tp* is ``list[X]`` return ``(True, X)``; otherwise ``(False, tp)``.
    """
    origin = getattr(tp, "__origin__", None)
    if origin is list:
        args = getattr(tp, "__args__", ())
        inner = args[0] if args else str
        return True, inner
    return False, tp


def _resolve_field_type(spec: FieldSpec, annotation: Any) -> None:
    """
    Fill in *spec.type* from the class annotation when the factory function
    did not supply one.

    For ``list[X]`` annotations on ``"arg"`` fields we unwrap the inner type
    and rely on ``count`` / ``enforce_count`` to control plurality.
    """
    if spec.type is not None:
        # Explicit type supplied by the factory call - trust it.
        return

    is_list, inner = _unwrap_list(annotation)
    if is_list and spec.kind == "arg":
        spec.type = inner
    else:
        spec.type = annotation if annotation is not type(None) else str


def extract_fields(cls: type) -> dict[str, FieldSpec]:
    """
    Return the :class:`FieldSpec` objects declared directly on *cls*
    (not its bases), keyed by attribute name.

    The annotation is used to back-fill ``spec.type`` when needed.
    """
    try:
        hints = get_type_hints(cls)
    except Exception as _:  # noqa: BLE001
        hints = {}

    fields: dict[str, FieldSpec] = {}
    for name, annotation in hints.items():
        value = cls.__dict__.get(name)  # own attrs only, not inherited
        if not isinstance(value, FieldSpec):
            continue
        spec = value
        _resolve_field_type(spec, annotation)
        fields[name] = spec
    return fields


def collect_fields(
    cls: type,
    *,
    allow_clash: bool = False,
) -> dict[str, FieldSpec]:
    """
    Walk the MRO of *cls* (excluding ``object``) and collect all
    :class:`FieldSpec` attributes, merging flattened base-class fields.

    Parameters
    ----------
    cls:
        The command class to introspect.
    allow_clash:
        When *False* (the default) a :func:`~cranberry.errors.panic` is
        raised if the same attribute name (or the same short/long flag) is
        declared more than once across the MRO.

    Returns
    -------
    dict[str, FieldSpec]
        Ordered so that positional ``"arg"`` fields appear last, preserving
        declaration order within each group.
    """
    seen_names: dict[str, str] = {}  # attr_name -> source class name
    seen_flags: dict[str, str] = {}  # "-x" / "--foo" -> source class name
    fields: dict[str, FieldSpec] = {}

    # Reverse MRO so base classes are processed first, then overrides.
    for base in reversed(cls.__mro__):
        if base is object:
            continue
        for attr_name, spec in extract_fields(base).items():
            if not allow_clash and attr_name in seen_names:
                panic(
                    f"Field clash: attribute {attr_name!r} is defined in both "
                    f"{seen_names[attr_name]!r} and {base.__name__!r}."
                )
            seen_names[attr_name] = base.__name__
            for flag in (spec.short, spec.long):
                if flag is None:
                    continue
                if not allow_clash and flag in seen_flags:
                    panic(
                        f"Flag clash: {flag!r} is used in both "
                        f"{seen_flags[flag]!r} and {base.__name__!r}."
                    )
                seen_flags[flag] = base.__name__
            fields[attr_name] = spec

    # Stable ordering: non-arg fields first, arg fields last.
    ordered = {k: v for k, v in fields.items() if v.kind != "arg"}
    ordered.update({k: v for k, v in fields.items() if v.kind == "arg"})
    return ordered


def check_global_clashes(
    global_fields: dict[str, FieldSpec],
    command_fields: dict[str, FieldSpec],
    *,
    global_cls_name: str,
    command_cls_name: str,
) -> None:
    """
    Panic if any attribute name or flag string appears in both the global
    namespace and a command's field set.
    """
    global_flags: set[str] = set()
    for spec in global_fields.values():
        for f in (spec.short, spec.long):
            if f:
                global_flags.add(f)

    for attr, spec in command_fields.items():
        if attr in global_fields:
            panic(
                f"Global/command field clash: attribute {attr!r} is declared "
                f"in both {global_cls_name!r} and {command_cls_name!r}."
            )
        for f in (spec.short, spec.long):
            if f and f in global_flags:
                panic(
                    f"Global/command flag clash: flag {f!r} is used in both "
                    f"{global_cls_name!r} and {command_cls_name!r}."
                )
