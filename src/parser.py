from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


VALID_ZONE_TYPES = {"normal", "blocked", "restricted", "priority"}
ZONE_METADATA_KEYS = {"zone", "color", "max_drones"}
CONNECTION_METADATA_KEYS = {"max_link_capacity"}


class ParseError(Exception):
    """Exception raised when a map file cannot be parsed.

    Attributes:
        line_number: The 1-based line number where the error occurred.
        message: A human-readable description of the error.
    """

    def __init__(self, line_number: int, message: str) -> None:
        self.line_number = line_number
        self.message = message
        super().__init__(f"line {line_number}: {message}")


@dataclass(frozen=True)
class Zone:
    """Represents a zone in the drone network.

    Attributes:
        name: Unique zone name.
        x: Horizontal coordinate.
        y: Vertical coordinate.
        zone_type: One of 'normal', 'blocked', 'restricted', 'priority'.
        color: Optional color string for visualization.
        max_drones: Maximum simultaneous drones allowed in this zone.
    """

    name: str
    x: int
    y: int
    zone_type: str = "normal"
    color: str | None = None
    max_drones: int = 1


@dataclass(frozen=True)
class Connection:
    """Represents a bidirectional connection between two zones.

    Attributes:
        from_zone: Name of the first zone.
        to_zone: Name of the second zone.
        max_capacity: Max drones traversing this connection per turn.
    """

    from_zone: str
    to_zone: str
    max_capacity: int = 1


@dataclass(frozen=True)
class Map:
    """Represents a fully parsed map.

    Attributes:
        drone_nb: Number of drones to route.
        zones: Dictionary mapping zone names to Zone objects.
        connections: List of all connections in the map.
        start_name: Name of the start zone.
        end_name: Name of the end zone.
    """

    drone_nb: int
    zones: dict[str, Zone]
    connections: list[Connection]
    start_name: str
    end_name: str


@dataclass(frozen=True)
class ParsedLine:
    """A non-empty, non-comment line from the map file.

    Attributes:
        number: The original 1-based line number in the file.
        content: The stripped line content.
    """

    number: int
    content: str


def parse_file(path: str | Path) -> Map:
    """Parse a map file and return a Map object.

    Args:
        path: Path to the map file.

    Returns:
        The parsed Map.

    Raises:
        ParseError: If the file content is invalid.
        OSError: If the file cannot be read.
    """
    with Path(path).open("r", encoding="utf-8") as file:
        return parse_lines(file.readlines())


def parse_lines(raw_lines: list[str]) -> Map:
    """Parse a list of raw text lines into a Map.

    Args:
        raw_lines: Lines from the map file.

    Returns:
        The parsed Map.

    Raises:
        ParseError: If the content is invalid.
    """
    lines = _clean_lines(raw_lines)
    if not lines:
        raise ParseError(1, "empty map file")

    drone_nb = _parse_drone_count(lines[0])
    zones: dict[str, Zone] = {}
    connections: list[Connection] = []
    seen_connections: set[frozenset[str]] = set()
    start_name: str | None = None
    end_name: str | None = None
    parsing_connections = False

    for line in lines[1:]:
        if line.content.startswith("connection:"):
            parsing_connections = True
            connection = _parse_connection(line, zones, seen_connections)
            connections.append(connection)
            continue

        if parsing_connections:
            raise ParseError(
                line.number,
                "zone declared after connections started",
            )

        if line.content.startswith("start_hub:"):
            if start_name is not None:
                raise ParseError(line.number, "duplicate start_hub")
            zone = _parse_zone(
                line,
                "start_hub:",
                ignore_capacity=True,
                default_capacity=drone_nb,
            )
            start_name = zone.name
            _add_zone(line, zones, zone)
            continue

        if line.content.startswith("end_hub:"):
            if end_name is not None:
                raise ParseError(line.number, "duplicate end_hub")
            zone = _parse_zone(
                line,
                "end_hub:",
                ignore_capacity=True,
                default_capacity=drone_nb,
            )
            end_name = zone.name
            _add_zone(line, zones, zone)
            continue

        if line.content.startswith("hub:"):
            zone = _parse_zone(line, "hub:", ignore_capacity=False)
            _add_zone(line, zones, zone)
            continue

        if line.content.startswith("nb_drones:"):
            raise ParseError(
                line.number,
                "nb_drones must appear only once as first directive",
            )

        raise ParseError(line.number, "unknown directive")

    if start_name is None:
        raise ParseError(lines[0].number, "missing start_hub")
    if end_name is None:
        raise ParseError(lines[0].number, "missing end_hub")

    return Map(
        drone_nb=drone_nb,
        zones=zones,
        connections=connections,
        start_name=start_name,
        end_name=end_name,
    )


def _clean_lines(raw_lines: list[str]) -> list[ParsedLine]:
    """Filter out blank lines and comments, returning ParsedLine objects."""
    lines: list[ParsedLine] = []
    for index, raw_line in enumerate(raw_lines, start=1):
        content = raw_line.strip()
        if not content or content.startswith("#"):
            continue
        lines.append(ParsedLine(index, content))
    return lines


def _parse_drone_count(line: ParsedLine) -> int:
    """Parse the first directive and return the number of drones."""
    parts = line.content.split()
    if len(parts) != 2 or parts[0] != "nb_drones:":
        raise ParseError(
            line.number,
            "first directive must be 'nb_drones: <positive_integer>'",
        )
    return _parse_positive_int(line.number, parts[1], "nb_drones")


def _parse_zone(
    line: ParsedLine,
    prefix: str,
    ignore_capacity: bool,
    default_capacity: int = 1,
) -> Zone:
    """Parse a zone directive and return a Zone object.

    Args:
        line: The parsed line to read from.
        prefix: The directive prefix ('start_hub:', 'end_hub:', or 'hub:').
        ignore_capacity: If True, ignore max_drones metadata.
        default_capacity: Default capacity when ignored (used for start/end).

    Returns:
        The parsed Zone.
    """
    body = line.content.removeprefix(prefix).strip()
    main_part, metadata = _split_metadata(line, body, ZONE_METADATA_KEYS)
    parts = main_part.split()
    if len(parts) != 3:
        raise ParseError(line.number, f"invalid {prefix[:-1]} syntax")

    name = parts[0]
    _validate_zone_name(line.number, name)
    x = _parse_int(line.number, parts[1], "x coordinate")
    y = _parse_int(line.number, parts[2], "y coordinate")

    zone_type = metadata.get("zone", "normal")
    if zone_type not in VALID_ZONE_TYPES:
        raise ParseError(line.number, f"invalid zone type '{zone_type}'")

    color = metadata.get("color")
    if color is not None and not _is_single_word(color):
        raise ParseError(line.number, "color must be a single-word value")

    max_drones = default_capacity
    if not ignore_capacity and "max_drones" in metadata:
        max_drones = _parse_positive_int(
            line.number,
            metadata["max_drones"],
            "max_drones",
        )

    return Zone(
        name=name,
        x=x,
        y=y,
        zone_type=zone_type,
        color=color,
        max_drones=max_drones,
    )


def _parse_connection(
    line: ParsedLine,
    zones: dict[str, Zone],
    seen_connections: set[frozenset[str]],
) -> Connection:
    """Parse a connection directive and return a Connection object.

    Args:
        line: The parsed line to read from.
        zones: Previously defined zones for validation.
        seen_connections: Set of already-seen connection pairs.

    Returns:
        The parsed Connection.
    """
    body = line.content.removeprefix("connection:").strip()
    main_part, metadata = _split_metadata(line, body, CONNECTION_METADATA_KEYS)
    parts = main_part.split()
    if len(parts) != 1:
        raise ParseError(line.number, "invalid connection syntax")

    zone_names = parts[0].split("-")
    if len(zone_names) != 2 or not zone_names[0] or not zone_names[1]:
        raise ParseError(
            line.number,
            "connection must use '<zone1>-<zone2>' syntax",
        )

    from_zone, to_zone = zone_names
    if from_zone == to_zone:
        raise ParseError(
            line.number,
            "connection cannot link a zone to itself",
        )
    if from_zone not in zones:
        raise ParseError(
            line.number,
            f"unknown zone '{from_zone}' in connection",
        )
    if to_zone not in zones:
        raise ParseError(
            line.number,
            f"unknown zone '{to_zone}' in connection",
        )

    connection_key = frozenset({from_zone, to_zone})
    if connection_key in seen_connections:
        raise ParseError(line.number, "duplicate connection")
    seen_connections.add(connection_key)

    max_capacity = 1
    if "max_link_capacity" in metadata:
        max_capacity = _parse_positive_int(
            line.number,
            metadata["max_link_capacity"],
            "max_link_capacity",
        )

    return Connection(
        from_zone=from_zone,
        to_zone=to_zone,
        max_capacity=max_capacity,
    )


def _split_metadata(
    line: ParsedLine,
    body: str,
    allowed_keys: set[str],
) -> tuple[str, dict[str, str]]:
    """Split a directive body into its main part and metadata dictionary."""
    if "[" not in body and "]" not in body:
        return body.strip(), {}
    if body.count("[") != 1 or body.count("]") != 1:
        raise ParseError(
            line.number,
            "metadata block must use one matching '[' and ']' pair",
        )

    before, after_open = body.split("[", 1)
    metadata_content, after = after_open.split("]", 1)
    if after.strip():
        raise ParseError(
            line.number,
            "unexpected content after metadata block",
        )

    metadata = _parse_metadata(line, metadata_content.strip(), allowed_keys)
    return before.strip(), metadata


def _parse_metadata(
    line: ParsedLine,
    metadata_content: str,
    allowed_keys: set[str],
) -> dict[str, str]:
    """Parse the content inside a metadata block into a key-value dict."""
    if not metadata_content:
        raise ParseError(line.number, "metadata block cannot be empty")

    metadata: dict[str, str] = {}
    for token in metadata_content.split():
        if token.count("=") != 1:
            raise ParseError(line.number, f"invalid metadata token '{token}'")
        key, value = token.split("=", 1)
        if not key or not value:
            raise ParseError(line.number, f"invalid metadata token '{token}'")
        if key not in allowed_keys:
            raise ParseError(line.number, f"unexpected metadata key '{key}'")
        if key in metadata:
            raise ParseError(line.number, f"duplicate metadata key '{key}'")
        if not _is_single_word(value):
            raise ParseError(
                line.number,
                f"metadata value for '{key}' must be single-word",
            )
        metadata[key] = value
    return metadata


def _add_zone(line: ParsedLine, zones: dict[str, Zone], zone: Zone) -> None:
    """Add a zone to the zones dict, raising on duplicate names."""
    if zone.name in zones:
        raise ParseError(line.number, f"duplicate zone name '{zone.name}'")
    zones[zone.name] = zone


def _validate_zone_name(line_number: int, name: str) -> None:
    """Validate that a zone name is non-empty and contains no dash or space."""
    if not name:
        raise ParseError(line_number, "zone name cannot be empty")
    if "-" in name:
        raise ParseError(line_number, "zone names cannot contain dashes")
    if not _is_single_word(name):
        raise ParseError(line_number, "zone names cannot contain spaces")


def _parse_int(line_number: int, value: str, field_name: str) -> int:
    """Parse a string as an integer, raising ParseError on failure."""
    try:
        return int(value)
    except ValueError as error:
        raise ParseError(
            line_number,
            f"{field_name} must be an integer",
        ) from error


def _parse_positive_int(line_number: int, value: str, field_name: str) -> int:
    """Parse a string as a positive integer, raising ParseError if <= 0."""
    number = _parse_int(line_number, value, field_name)
    if number <= 0:
        raise ParseError(
            line_number,
            f"{field_name} must be a positive integer",
        )
    return number


def _is_single_word(value: str) -> bool:
    """Return True if the value is non-empty and contains no spaces."""
    return bool(value) and not any(character.isspace() for character in value)
