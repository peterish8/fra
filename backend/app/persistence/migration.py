"""Typed, non-executing inspection of the forward database migration.

This module deliberately stops at filesystem and SQL-text checks.  A later
schema-check layer can consume :class:`ForwardMigrationDocument` without
coupling domain code to a database driver or a particular provider.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from enum import StrEnum
from pathlib import Path

FORWARD_MIGRATION_PATH = Path("supabase") / "migrations" / "0001_truth_ledger.sql"


class MigrationErrorCode(StrEnum):
    """Stable categories for migration discovery, reading, and validation errors."""

    ROOT_NOT_FOUND = "ROOT_NOT_FOUND"
    INVALID_RELATIVE_PATH = "INVALID_RELATIVE_PATH"
    MIGRATION_NOT_FOUND = "MIGRATION_NOT_FOUND"
    MIGRATION_NOT_FILE = "MIGRATION_NOT_FILE"
    MIGRATION_OUTSIDE_ROOT = "MIGRATION_OUTSIDE_ROOT"
    MIGRATION_READ_FAILED = "MIGRATION_READ_FAILED"
    MIGRATION_INVALID_ENCODING = "MIGRATION_INVALID_ENCODING"
    EMPTY_MIGRATION = "EMPTY_MIGRATION"
    DESTRUCTIVE_STATEMENT = "DESTRUCTIVE_STATEMENT"
    ROLLBACK_STATEMENT = "ROLLBACK_STATEMENT"


@dataclass(frozen=True, slots=True)
class MigrationError:
    """A safe, structured problem suitable for logs or future schema checks."""

    code: MigrationErrorCode
    message: str
    path: Path | None = None
    line: int | None = None
    token: str | None = None


@dataclass(frozen=True, slots=True)
class ForwardMigrationDocument:
    """The exact migration text and its resolved filesystem identity."""

    path: Path
    relative_path: Path
    sql: str


@dataclass(frozen=True, slots=True)
class MigrationLocationResult:
    """Result of locating one expected forward migration file."""

    path: Path | None
    errors: tuple[MigrationError, ...] = ()

    @property
    def ok(self) -> bool:
        """Whether a usable migration path was located."""

        return self.path is not None and not self.errors


@dataclass(frozen=True, slots=True)
class MigrationReadResult:
    """Result of reading the located migration as UTF-8 text."""

    document: ForwardMigrationDocument | None
    errors: tuple[MigrationError, ...] = ()

    @property
    def ok(self) -> bool:
        """Whether a migration document was read successfully."""

        return self.document is not None and not self.errors


@dataclass(frozen=True, slots=True)
class MigrationValidationResult:
    """Non-executing forward-only validation output."""

    document: ForwardMigrationDocument | None
    statement_count: int
    errors: tuple[MigrationError, ...] = ()

    @property
    def valid(self) -> bool:
        """Whether the migration is non-empty and has no unsafe findings."""

        return self.document is not None and self.statement_count > 0 and not self.errors

    @property
    def ok(self) -> bool:
        """Alias for callers that use result objects uniformly."""

        return self.valid


_DESTRUCTIVE_PATTERNS: tuple[tuple[str, str], ...] = (
    (
        "drop object",
        r"\bdrop\s+(?:table|type|schema|index|view|function|procedure|sequence|extension|policy)\b",
    ),
    ("truncate", r"\btruncate(?:\s+table)?\b"),
    ("delete from", r"\bdelete\s+from\b"),
    ("alter table drop", r"\balter\s+table\b[^;]*?\bdrop\s+(?:column|constraint)\b"),
)

_ROLLBACK_PATTERN = re.compile(
    r"\b(?:rollback(?:\s+(?:to|work)\b|\s*;)|downgrade\b)",
    re.IGNORECASE,
)


def _default_repository_root() -> Path:
    """Return the repository root implied by this package's location."""

    return Path(__file__).resolve().parents[3]


def _error(
    code: MigrationErrorCode,
    message: str,
    *,
    path: Path | None = None,
    line: int | None = None,
    token: str | None = None,
) -> MigrationError:
    return MigrationError(code=code, message=message, path=path, line=line, token=token)


def locate_forward_migration(
    repository_root: Path | str | None = None,
    *,
    relative_path: Path | str = FORWARD_MIGRATION_PATH,
) -> MigrationLocationResult:
    """Locate the expected migration without accepting paths outside the root.

    The default root is derived from this module, so callers do not need to
    depend on the process working directory.  A custom relative path is useful
    for deterministic fixtures but cannot escape the supplied repository root.
    """

    root = Path(repository_root) if repository_root is not None else _default_repository_root()
    migration_relative_path = Path(relative_path)
    if migration_relative_path.is_absolute() or ".." in migration_relative_path.parts:
        return MigrationLocationResult(
            path=None,
            errors=(
                _error(
                    MigrationErrorCode.INVALID_RELATIVE_PATH,
                    "forward migration path must be relative and remain inside the repository root",
                    path=migration_relative_path,
                ),
            ),
        )

    try:
        resolved_root = root.expanduser().resolve()
    except (OSError, RuntimeError) as error:
        return MigrationLocationResult(
            path=None,
            errors=(
                _error(
                    MigrationErrorCode.ROOT_NOT_FOUND,
                    f"repository root could not be resolved: {error}",
                    path=root,
                ),
            ),
        )

    if not resolved_root.is_dir():
        return MigrationLocationResult(
            path=None,
            errors=(
                _error(
                    MigrationErrorCode.ROOT_NOT_FOUND,
                    "repository root does not exist or is not a directory",
                    path=resolved_root,
                ),
            ),
        )

    candidate = resolved_root / migration_relative_path
    try:
        resolved_candidate = candidate.resolve()
    except (OSError, RuntimeError) as error:
        return MigrationLocationResult(
            path=None,
            errors=(
                _error(
                    MigrationErrorCode.MIGRATION_OUTSIDE_ROOT,
                    f"forward migration could not be resolved safely: {error}",
                    path=candidate,
                ),
            ),
        )

    try:
        resolved_candidate.relative_to(resolved_root)
    except ValueError:
        return MigrationLocationResult(
            path=None,
            errors=(
                _error(
                    MigrationErrorCode.MIGRATION_OUTSIDE_ROOT,
                    "forward migration resolves outside the repository root",
                    path=resolved_candidate,
                ),
            ),
        )

    if not resolved_candidate.exists():
        return MigrationLocationResult(
            path=resolved_candidate,
            errors=(
                _error(
                    MigrationErrorCode.MIGRATION_NOT_FOUND,
                    "forward migration file was not found",
                    path=resolved_candidate,
                ),
            ),
        )
    if not resolved_candidate.is_file():
        return MigrationLocationResult(
            path=resolved_candidate,
            errors=(
                _error(
                    MigrationErrorCode.MIGRATION_NOT_FILE,
                    "forward migration path is not a regular file",
                    path=resolved_candidate,
                ),
            ),
        )
    return MigrationLocationResult(path=resolved_candidate)


def read_forward_migration(
    repository_root: Path | str | None = None,
    *,
    relative_path: Path | str = FORWARD_MIGRATION_PATH,
) -> MigrationReadResult:
    """Locate and read the forward migration as UTF-8 without executing it."""

    location = locate_forward_migration(repository_root, relative_path=relative_path)
    if not location.ok or location.path is None:
        return MigrationReadResult(document=None, errors=location.errors)

    try:
        sql = location.path.read_text(encoding="utf-8")
    except UnicodeDecodeError as error:
        return MigrationReadResult(
            document=None,
            errors=(
                _error(
                    MigrationErrorCode.MIGRATION_INVALID_ENCODING,
                    f"forward migration is not valid UTF-8: {error}",
                    path=location.path,
                ),
            ),
        )
    except OSError as error:
        return MigrationReadResult(
            document=None,
            errors=(
                _error(
                    MigrationErrorCode.MIGRATION_READ_FAILED,
                    f"forward migration could not be read: {error}",
                    path=location.path,
                ),
            ),
        )

    if not _mask_sql(sql).strip():
        return MigrationReadResult(
            document=None,
            errors=(
                _error(
                    MigrationErrorCode.EMPTY_MIGRATION,
                    "forward migration contains no executable SQL",
                    path=location.path,
                ),
            ),
        )

    relative = Path(relative_path)
    return MigrationReadResult(
        document=ForwardMigrationDocument(
            path=location.path,
            relative_path=relative,
            sql=sql,
        )
    )


def _mask_sql(sql: str, *, mask_dollar_quoted: bool = True) -> str:
    """Mask comments and literal bodies while preserving code and line offsets.

    This is intentionally a small lexical safety pass, not a SQL parser.  It
    prevents comments, quoted values, and (by default) PL/pgSQL dollar bodies
    from producing false statement counts in a text contract.  Validation uses
    the optional unmasked dollar-body mode so executable procedural SQL is not
    skipped when checking destructive operations.
    """

    output = list(sql)
    length = len(sql)
    index = 0

    def blank(start: int, end: int) -> None:
        for position in range(start, end):
            if output[position] != "\n":
                output[position] = " "

    while index < length:
        if sql.startswith("--", index):
            end = sql.find("\n", index)
            end = length if end == -1 else end
            blank(index, end)
            index = end
            continue
        if sql.startswith("/*", index):
            end = sql.find("*/", index + 2)
            end = length if end == -1 else end + 2
            blank(index, end)
            index = end
            continue
        if sql[index] in {"'", '"'}:
            quote = sql[index]
            end = index + 1
            while end < length:
                if sql[end] == quote:
                    if end + 1 < length and sql[end + 1] == quote:
                        end += 2
                        continue
                    end += 1
                    break
                end += 1
            blank(index, end)
            index = end
            continue
        if mask_dollar_quoted and sql[index] == "$":
            match = re.match(r"\$[A-Za-z_][A-Za-z0-9_]*\$|\$\$", sql[index:])
            if match:
                delimiter = match.group(0)
                body_start = index + len(delimiter)
                body_end = sql.find(delimiter, body_start)
                end = length if body_end == -1 else body_end + len(delimiter)
                blank(index, end)
                index = end
                continue
        index += 1
    return "".join(output)


def _statement_count(masked_sql: str) -> int:
    return sum(1 for statement in masked_sql.split(";") if statement.strip())


def _line_for_offset(masked_sql: str, offset: int) -> int:
    return masked_sql.count("\n", 0, offset) + 1


def validate_forward_migration(
    migration: ForwardMigrationDocument | str | Path | None = None,
    *,
    repository_root: Path | str | None = None,
) -> MigrationValidationResult:
    """Validate forward-only safety characteristics without touching a database.

    With no argument, the canonical repository migration is located and read.
    A string is treated as SQL text; a path is read directly only when it is
    already inside the supplied repository root (or its parent is used as the
    root when no root is supplied).
    """

    if migration is None:
        read_result = read_forward_migration(repository_root)
        if not read_result.ok or read_result.document is None:
            return MigrationValidationResult(
                document=None,
                statement_count=0,
                errors=read_result.errors,
            )
        document = read_result.document
    elif isinstance(migration, ForwardMigrationDocument):
        document = migration
    elif isinstance(migration, Path):
        path = migration.expanduser()
        root = Path(repository_root).expanduser() if repository_root is not None else path.parent
        try:
            relative_path = path.resolve().relative_to(root.resolve())
        except (OSError, RuntimeError, ValueError):
            return MigrationValidationResult(
                document=None,
                statement_count=0,
                errors=(
                    _error(
                        MigrationErrorCode.MIGRATION_OUTSIDE_ROOT,
                        "migration path is outside the repository root",
                        path=path,
                    ),
                ),
            )
        read_result = read_forward_migration(root, relative_path=relative_path)
        if not read_result.ok or read_result.document is None:
            return MigrationValidationResult(
                document=None, statement_count=0, errors=read_result.errors
            )
        document = read_result.document
    else:
        document = ForwardMigrationDocument(
            path=Path("<provided-sql>"),
            relative_path=Path("<provided-sql>"),
            sql=migration,
        )

    statement_count_sql = _mask_sql(document.sql)
    masked_sql = _mask_sql(document.sql, mask_dollar_quoted=False)
    statement_count = _statement_count(statement_count_sql)
    errors: list[MigrationError] = []
    if not statement_count_sql.strip():
        errors.append(
            _error(
                MigrationErrorCode.EMPTY_MIGRATION,
                "forward migration contains no executable SQL",
                path=document.path,
            )
        )
        return MigrationValidationResult(document=document, statement_count=0, errors=tuple(errors))

    for label, pattern in _DESTRUCTIVE_PATTERNS:
        for match in re.finditer(pattern, masked_sql, re.IGNORECASE):
            token = " ".join(match.group(0).split())
            errors.append(
                _error(
                    MigrationErrorCode.DESTRUCTIVE_STATEMENT,
                    f"forward migration contains a destructive {label} operation",
                    path=document.path,
                    line=_line_for_offset(masked_sql, match.start()),
                    token=token,
                )
            )

    for match in _ROLLBACK_PATTERN.finditer(masked_sql):
        token = match.group(0).upper()
        errors.append(
            _error(
                MigrationErrorCode.ROLLBACK_STATEMENT,
                "forward migration contains rollback/downgrade control text",
                path=document.path,
                line=_line_for_offset(masked_sql, match.start()),
                token=token,
            )
        )

    return MigrationValidationResult(
        document=document,
        statement_count=statement_count,
        errors=tuple(errors),
    )


__all__ = [
    "FORWARD_MIGRATION_PATH",
    "ForwardMigrationDocument",
    "MigrationError",
    "MigrationErrorCode",
    "MigrationLocationResult",
    "MigrationReadResult",
    "MigrationValidationResult",
    "locate_forward_migration",
    "read_forward_migration",
    "validate_forward_migration",
]
