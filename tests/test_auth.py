"""Tests for outgoing authentication (Task 3.3)."""

from __future__ import annotations

import asyncio
import time
from unittest.mock import AsyncMock

import pytest

from mcp_sentinel.bridge.auth.provider import (
    OAuth2Provider,
    StaticTokenProvider,
    _redact,
    create_auth_provider,
)
from mcp_sentinel.bridge.auth.token_cache import TokenCache

# ── TokenCache tests ────────────────────────────────────────────────────


class TestTokenCache:
    def test_empty_cache_returns_none(self) -> None:
        cache = TokenCache()
        assert cache.get() is None
        assert not cache.valid

    def test_set_and_get(self) -> None:
        cache = TokenCache(expiry_buffer=0.0)
        cache.set("tok123", expires_in=60.0)
        assert cache.valid
        assert cache.get() == "tok123"

    def test_expired_token_returns_none(self) -> None:
        cache = TokenCache(expiry_buffer=0.0)
        cache.set("tok", expires_in=0.01)
        time.sleep(0.02)
        assert cache.get() is None
        assert not cache.valid

    def test_expiry_buffer(self) -> None:
        cache = TokenCache(expiry_buffer=100.0)
        # Token expires in 50s, but buffer is 100s → immediately expired
        cache.set("tok", expires_in=50.0)
        assert cache.get() is None

    def test_invalidate(self) -> None:
        cache = TokenCache(expiry_buffer=0.0)
        cache.set("tok", expires_in=3600.0)
        assert cache.valid
        cache.invalidate()
        assert cache.get() is None
        assert not cache.valid


# ── StaticTokenProvider tests ────────────────────────────────────────


class TestStaticTokenProvider:
    def test_returns_headers(self) -> None:
        provider = StaticTokenProvider({"Authorization": "Bearer abc123"})
        headers = asyncio.get_event_loop().run_until_complete(provider.get_headers())
        assert headers == {"Authorization": "Bearer abc123"}

    def test_returns_copy(self) -> None:
        original = {"X-Key": "val"}
        provider = StaticTokenProvider(original)
        h1 = asyncio.get_event_loop().run_until_complete(provider.get_headers())
        h2 = asyncio.get_event_loop().run_until_complete(provider.get_headers())
        assert h1 is not h2
        assert h1 == h2

    def test_redacted_repr_masks_auth_headers(self) -> None:
        provider = StaticTokenProvider({
            "Authorization": "Bearer ghp_1234567890abcdef",
            "X-Custom": "visible",
        })
        r = provider.redacted_repr()
        assert "ghp_1234567890abcdef" not in r
        assert "visible" in r
        assert "StaticTokenProvider" in r


# ── OAuth2Provider tests ─────────────────────────────────────────────


class TestOAuth2Provider:
    def test_redacted_repr(self) -> None:
        provider = OAuth2Provider(
            token_url="https://auth.example.com/token",
            client_id="my-client",
            client_secret="super-secret-value",
        )
        r = provider.redacted_repr()
        assert "super-secret-value" not in r
        assert "my-client" in r
        assert "OAuth2Provider" in r

    def test_get_headers_calls_fetch(self) -> None:
        provider = OAuth2Provider(
            token_url="https://auth.example.com/token",
            client_id="cid",
            client_secret="csec",
        )
        provider._fetch_token = AsyncMock(return_value="access_tok_xyz")  # type: ignore[method-assign]
        headers = asyncio.get_event_loop().run_until_complete(provider.get_headers())
        assert headers == {"Authorization": "Bearer access_tok_xyz"}
        provider._fetch_token.assert_called_once()

    def test_get_headers_uses_cache(self) -> None:
        provider = OAuth2Provider(
            token_url="https://auth.example.com/token",
            client_id="cid",
            client_secret="csec",
            expiry_buffer=0.0,
        )
        # Pre-fill cache
        provider._cache.set("cached_tok", expires_in=3600.0)
        provider._fetch_token = AsyncMock()  # type: ignore[method-assign]
        headers = asyncio.get_event_loop().run_until_complete(provider.get_headers())
        assert headers == {"Authorization": "Bearer cached_tok"}
        provider._fetch_token.assert_not_called()


# ── Factory tests ────────────────────────────────────────────────────


class TestCreateAuthProvider:
    def test_static(self) -> None:
        p = create_auth_provider({"type": "static", "headers": {"X": "Y"}})
        assert isinstance(p, StaticTokenProvider)

    def test_oauth2(self) -> None:
        p = create_auth_provider({
            "type": "oauth2",
            "token_url": "https://ex.com/token",
            "client_id": "cid",
            "client_secret": "csec",
        })
        assert isinstance(p, OAuth2Provider)

    def test_unknown_type_raises(self) -> None:
        with pytest.raises(ValueError, match="Unknown auth type"):
            create_auth_provider({"type": "magic"})

    def test_static_missing_headers_raises(self) -> None:
        with pytest.raises(ValueError, match="headers"):
            create_auth_provider({"type": "static"})

    def test_oauth2_missing_field_raises(self) -> None:
        with pytest.raises(ValueError, match="token_url"):
            create_auth_provider({"type": "oauth2", "client_id": "x", "client_secret": "y"})


# ── Redact helper tests ─────────────────────────────────────────────


class TestRedact:
    def test_short_value(self) -> None:
        assert _redact("ab") == "****"

    def test_longer_value(self) -> None:
        result = _redact("1234567890", visible=4)
        assert result.endswith("7890")
        assert result.startswith("*")
        assert len(result) == 10


# ── Config schema tests ─────────────────────────────────────────────


class TestAuthConfigSchema:
    def test_static_auth_config(self) -> None:
        from mcp_sentinel.config.schema import SseBackendConfig

        cfg = SseBackendConfig(
            type="sse",
            url="https://example.com/sse",
            auth={"type": "static", "headers": {"Authorization": "Bearer tok"}},
        )
        assert cfg.auth is not None
        assert cfg.auth.type == "static"

    def test_oauth2_auth_config(self) -> None:
        from mcp_sentinel.config.schema import StreamableHttpBackendConfig

        cfg = StreamableHttpBackendConfig(
            type="streamable-http",
            url="https://example.com/mcp",
            auth={
                "type": "oauth2",
                "token_url": "https://auth.example.com/token",
                "client_id": "cid",
                "client_secret": "csec",
            },
        )
        assert cfg.auth is not None
        assert cfg.auth.type == "oauth2"

    def test_no_auth_config(self) -> None:
        from mcp_sentinel.config.schema import SseBackendConfig

        cfg = SseBackendConfig(type="sse", url="https://example.com/sse")
        assert cfg.auth is None

    def test_sse_headers_field(self) -> None:
        from mcp_sentinel.config.schema import SseBackendConfig

        cfg = SseBackendConfig(
            type="sse",
            url="https://example.com/sse",
            headers={"X-Api-Key": "test"},
        )
        assert cfg.headers == {"X-Api-Key": "test"}


# ── Merge headers test ──────────────────────────────────────────────


class TestMergeHeaders:
    def test_both_none(self) -> None:
        from mcp_sentinel.bridge.client_manager import _merge_headers
        assert _merge_headers(None, None) is None

    def test_only_static(self) -> None:
        from mcp_sentinel.bridge.client_manager import _merge_headers
        assert _merge_headers({"X": "1"}, None) == {"X": "1"}

    def test_only_auth(self) -> None:
        from mcp_sentinel.bridge.client_manager import _merge_headers
        assert _merge_headers(None, {"Authorization": "Bearer x"}) == {"Authorization": "Bearer x"}

    def test_auth_overrides_static(self) -> None:
        from mcp_sentinel.bridge.client_manager import _merge_headers
        result = _merge_headers(
            {"Authorization": "old", "X-Other": "keep"},
            {"Authorization": "new"},
        )
        assert result == {"Authorization": "new", "X-Other": "keep"}
