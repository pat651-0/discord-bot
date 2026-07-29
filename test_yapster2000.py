"""Regression tests for yapster2000.

Runs under pytest, or standalone with `python test_yapster2000.py` so the bot
host does not need pytest installed.

The module is imported the same way the bot's own self-update validator imports
candidates (yapster2000.self_update_fixed_validation): TOKEN blanked and the
data directory redirected at a throwaway folder, so importing never touches the
real Railway volume, never logs in, and never runs main().
"""

from __future__ import annotations

import asyncio
import os
import sys
import tempfile
import time
from pathlib import Path

_DATA_DIR = tempfile.mkdtemp(prefix="xsi-test-data-")
os.environ["RAILWAY_VOLUME_MOUNT_PATH"] = _DATA_DIR
os.environ["TOKEN"] = ""

sys.path.insert(0, str(Path(__file__).resolve().parent))

import yapster2000 as xsi  # noqa: E402


class _StubGuild:
    """Minimal stand-in: build_sentinel_lookup_embed only calls get_member."""

    def __init__(self, members: dict[int, object] | None = None) -> None:
        self._members = members or {}

    def get_member(self, user_id: int):
        return self._members.get(user_id)


def _seed(guild_id: int, kind: str, value: str, user_id: int, last_seen: int, verified: int = 0) -> None:
    connection = xsi._sentinel_connect()
    try:
        connection.execute(
            """
            INSERT OR REPLACE INTO sentinel_identifiers
                (guild_id,kind,value,user_id,first_seen,last_seen,verified,source_channel_id,source_message_id)
            VALUES (?,?,?,?,?,?,?,NULL,NULL)
            """,
            (guild_id, kind, value, user_id, last_seen - 500, last_seen, verified),
        )
        connection.commit()
    finally:
        connection.close()


# ---------------- identifier normalisation ----------------
# The lookup reads rows written by sentinel_record_identifier. If the read path
# normalises differently from the write path, lookups silently return nothing.
def test_psn_normalisation_matches_write_path() -> None:
    assert xsi.sentinel_normalize_identifier("psn", "  xX_Trader_Xx ") == "xx_trader_xx"
    assert xsi.sentinel_normalize_identifier("psn", "xX Trader Xx") == "xxtraderxx"
    assert xsi.sentinel_normalize_identifier("psn", "") == ""
    assert xsi.sentinel_normalize_identifier("psn", "   ") == ""
    assert xsi.sentinel_normalize_identifier("psn", None) == ""
    assert xsi.sentinel_normalize_identifier("psn", "a" * 60) == "a" * 32


def test_normalisation_is_idempotent() -> None:
    # sentinel_run_lookup normalises, then sentinel_identifier_accounts
    # normalises again. A non-idempotent normaliser would break the query.
    for kind, raw in (
        ("psn", "  xX_Trader_Xx "),
        ("psn", "a" * 60),
        ("discord_invite", "discord.gg/Example"),
        ("discord_invite", "example"),
    ):
        once = xsi.sentinel_normalize_identifier(kind, raw)
        assert xsi.sentinel_normalize_identifier(kind, once) == once, (kind, raw)


def test_unicode_lookalikes_fold_together() -> None:
    # NFKC folds fullwidth characters, so an alt cannot dodge the lookup with them.
    assert xsi.sentinel_normalize_identifier("psn", "ｘX_Trader") == \
        xsi.sentinel_normalize_identifier("psn", "xX_Trader")


# ---------------- query parsing ----------------
def test_parse_lookup_query() -> None:
    assert xsi.sentinel_parse_lookup_query("xX_Trader_Xx") == ("psn", "xX_Trader_Xx")
    assert xsi.sentinel_parse_lookup_query("psn xX_Trader_Xx") == ("psn", "xX_Trader_Xx")
    assert xsi.sentinel_parse_lookup_query("discord_invite discord.gg/abc") == (
        "discord_invite",
        "discord.gg/abc",
    )
    assert xsi.sentinel_parse_lookup_query("") == ("psn", "")
    assert xsi.sentinel_parse_lookup_query("   ") == ("psn", "")
    # A bare kind word with no value is treated as the value, not a kind.
    assert xsi.sentinel_parse_lookup_query("psn") == ("psn", "psn")
    # Multi-word values keep their spaces; PSN normalisation strips them later.
    assert xsi.sentinel_parse_lookup_query("some trader name") == ("psn", "some trader name")


# ---------------- reverse lookup query ----------------
def test_reverse_lookup_finds_every_account_sharing_a_value() -> None:
    xsi._sentinel_init_sync()
    now = int(time.time())
    _seed(1001, "psn", "sharedpsn", user_id=11, last_seen=now - 100, verified=1)
    _seed(1001, "psn", "sharedpsn", user_id=22, last_seen=now)
    _seed(1001, "psn", "otherpsn", user_id=33, last_seen=now)

    rows = xsi._sentinel_identifier_accounts_sync(1001, "psn", "sharedpsn", 15)
    assert [int(row["user_id"]) for row in rows] == [22, 11], "must be newest last_seen first"
    assert int(rows[1]["verified"]) == 1

    assert len(xsi._sentinel_identifier_accounts_sync(1001, "psn", "otherpsn", 15)) == 1
    assert xsi._sentinel_identifier_accounts_sync(1001, "psn", "neverseen", 15) == []


def test_reverse_lookup_is_isolated_per_guild() -> None:
    xsi._sentinel_init_sync()
    now = int(time.time())
    _seed(2001, "psn", "tenantpsn", user_id=44, last_seen=now)
    _seed(2002, "psn", "tenantpsn", user_id=55, last_seen=now)

    rows = xsi._sentinel_identifier_accounts_sync(2001, "psn", "tenantpsn", 15)
    assert [int(row["user_id"]) for row in rows] == [44], "must not leak across guilds"


def test_reverse_lookup_respects_limit() -> None:
    xsi._sentinel_init_sync()
    now = int(time.time())
    for offset in range(20):
        _seed(3001, "psn", "busypsn", user_id=100 + offset, last_seen=now - offset)
    assert len(xsi._sentinel_identifier_accounts_sync(3001, "psn", "busypsn", 15)) == 15


def test_async_wrapper_normalises_and_rejects_empty() -> None:
    xsi._sentinel_init_sync()
    now = int(time.time())
    _seed(4001, "psn", "asyncpsn", user_id=66, last_seen=now)

    # Caller passes raw, unnormalised input; the wrapper must still match.
    rows = asyncio.run(xsi.sentinel_identifier_accounts(4001, "psn", "  AsyncPsn  "))
    assert [int(row["user_id"]) for row in rows] == [66]

    # Empty input must never reach the database.
    assert asyncio.run(xsi.sentinel_identifier_accounts(4001, "psn", "   ")) == []


def test_run_lookup_falls_back_to_psn_for_unknown_kind() -> None:
    xsi._sentinel_init_sync()
    now = int(time.time())
    _seed(5001, "psn", "kindpsn", user_id=77, last_seen=now)
    guild = _StubGuild()
    guild.id = 5001  # type: ignore[attr-defined]

    embed = asyncio.run(xsi.sentinel_run_lookup(guild, "not_a_kind", "kindpsn"))
    assert embed is not None
    assert "PSN" in embed.title
    assert asyncio.run(xsi.sentinel_run_lookup(guild, "psn", "")) is None


# ---------------- embed rendering ----------------
def test_lookup_embed_states() -> None:
    import discord

    guild = _StubGuild()
    now = int(time.time())

    empty = xsi.build_sentinel_lookup_embed(guild, "psn", "nothing", [])
    assert empty.color == discord.Color.greyple()

    single = xsi.build_sentinel_lookup_embed(
        guild, "psn", "solo", [{"user_id": 1, "verified": 1, "first_seen": now, "last_seen": now}]
    )
    assert single.color == discord.Color.green()
    assert not any("Shared identifier" in (field.name or "") for field in single.fields)

    shared = xsi.build_sentinel_lookup_embed(
        guild,
        "psn",
        "shared",
        [
            {"user_id": 1, "verified": 1, "first_seen": now, "last_seen": now},
            {"user_id": 2, "verified": 0, "first_seen": now, "last_seen": now},
        ],
    )
    assert shared.color == discord.Color.red()
    assert any("Shared identifier" in (field.name or "") for field in shared.fields)


def test_lookup_embed_cannot_break_out_of_its_code_span() -> None:
    guild = _StubGuild()
    embed = xsi.build_sentinel_lookup_embed(guild, "psn", "evil`](http://x)", [])
    assert "`" not in str(embed.description).strip("`")


def test_lookup_embed_field_stays_within_discord_limit() -> None:
    guild = _StubGuild()
    now = int(time.time())
    rows = [
        {"user_id": 900000000000000000 + i, "verified": 0, "first_seen": now, "last_seen": now}
        for i in range(xsi.SENTINEL_LOOKUP_LIMIT)
    ]
    embed = xsi.build_sentinel_lookup_embed(guild, "psn", "busy", rows)
    for field in embed.fields:
        assert len(field.value or "") <= 1024, field.name
    assert "Showing newest" in (embed.footer.text or "")


def test_lookup_embed_renders_departed_members() -> None:
    guild = _StubGuild()  # nobody resolves
    now = int(time.time())
    embed = xsi.build_sentinel_lookup_embed(
        guild, "psn", "gone", [{"user_id": 12345, "verified": 0, "first_seen": now, "last_seen": now}]
    )
    accounts = next(field for field in embed.fields if field.name == "Accounts")
    assert "Unknown user" in (accounts.value or "")


# ---------------- command registration ----------------
def test_slotinfo_is_gone() -> None:
    assert xsi.bot.get_command("slotinfo") is None
    assert "slotinfo" not in {command.name for command in xsi.bot.tree.get_commands()}


def test_sentinel_lookup_is_registered_on_both_surfaces() -> None:
    prefix_group = xsi.bot.get_command("sentinel")
    assert prefix_group is not None
    assert prefix_group.get_command("lookup") is not None
    assert xsi.bot.get_command("sentinel psn") is not None, "alias must resolve"

    sentinel_group = next(
        command for command in xsi.bot.tree.get_commands() if command.name == "sentinel"
    )
    assert "lookup" in {child.name for child in sentinel_group.commands}


def test_lookup_requires_manage_messages_not_public() -> None:
    # A read tool that exposes other members' identifiers must stay staff-only.
    prefix_lookup = xsi.bot.get_command("sentinel").get_command("lookup")
    assert prefix_lookup.checks, "prefix lookup must carry a permission check"

    sentinel_group = next(
        command for command in xsi.bot.tree.get_commands() if command.name == "sentinel"
    )
    slash_lookup = next(child for child in sentinel_group.commands if child.name == "lookup")
    assert slash_lookup.checks, "slash lookup must carry a permission check"


def test_application_command_count_within_discord_limit() -> None:
    # yapster2000 sits close to the cap; the bot's own validator rejects >100.
    count = len(xsi.bot.tree.get_commands())
    assert count <= 100, f"{count} top-level application commands exceeds Discord's limit"


if __name__ == "__main__":
    failures = 0
    for name, func in sorted(globals().items()):
        if not name.startswith("test_") or not callable(func):
            continue
        try:
            func()
        except Exception as exc:  # noqa: BLE001 - standalone runner reports and continues
            failures += 1
            print(f"FAIL {name}: {type(exc).__name__}: {exc}")
        else:
            print(f"ok   {name}")
    print(f"\n{'FAILED' if failures else 'PASSED'} — {failures} failure(s)")
    sys.exit(1 if failures else 0)
