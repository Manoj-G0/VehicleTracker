"""Normalization helpers for identifiers and Excel cells."""

MISSING_TOKENS = frozenset(
    {
        "",
        "-",
        "--",
        "n/a",
        "na",
        "null",
        "none",
        "blank",
    }
)

ID_FIELDS = (
    "rlf_id",
    "rm_id",
    "ip_id",
    "evap_id",
    "pr_id",
    "df_id",
    "ob_id",
    "er_id",
    "pems_id",
)


def normalize_identifier(value: object | None) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None
    if text.lower() in MISSING_TOKENS:
        return None
    return text


def normalize_header(value: object | None) -> str:
    if value is None:
        return ""
    return " ".join(str(value).strip().split()).upper()


def escape_ilike(value: str) -> str:
    return value.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
