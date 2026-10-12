"""Tests for PyPI client using mocked HTTP responses."""

import httpx
import pytest

from libtrial.pypi_client import PyPIClient


def test_pypi_package_found():
    """Verify clean extraction of version, license, and dependencies from PyPI JSON."""
    mock_payload = {
        "info": {
            "name": "polars",
            "version": "1.0.0",
            "summary": "Fast multi-threaded DataFrame library",
            "requires_python": ">=3.9",
            "requires_dist": ["pyarrow>=14.0.0", "numpy>=1.24.0"],
            "license": "MIT",
            "project_urls": {"Homepage": "https://pola.rs"},
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_payload)

    with PyPIClient(client=httpx.Client(transport=httpx.MockTransport(handler))) as client:
        meta = client.get_package_metadata("polars", fetch_github=False)

    assert meta.is_found is True
    assert meta.name == "polars"
    assert meta.version == "1.0.0"
    assert meta.summary == "Fast multi-threaded DataFrame library"
    assert meta.requires_python == ">=3.9"
    assert "pyarrow>=14.0.0" in meta.requires_dist
    assert meta.license == "MIT"


def test_pypi_package_not_found_404():
    """Package returning 404 must be marked is_found=False without throwing exceptions."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(404)

    with PyPIClient(client=httpx.Client(transport=httpx.MockTransport(handler))) as client:
        meta = client.get_package_metadata("hallucinated-pkg-xyz", fetch_github=False)

    assert meta.is_found is False
    assert meta.name == "hallucinated-pkg-xyz"
    assert "not found on PyPI" in (meta.raw_error or "")


def test_pypi_timeout():
    """Network timeouts must be safely captured and flagged as not found with an error message."""
    def handler(request: httpx.Request) -> httpx.Response:
        raise httpx.TimeoutException("Read timed out")

    with PyPIClient(client=httpx.Client(transport=httpx.MockTransport(handler))) as client:
        meta = client.get_package_metadata("slow-pkg", fetch_github=False)

    assert meta.is_found is False
    assert "Network error" in (meta.raw_error or "")


def test_pypi_malformed_json():
    """Malformed or invalid JSON responses must be caught safely."""
    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, text="NOT_VALID_JSON{")

    with PyPIClient(client=httpx.Client(transport=httpx.MockTransport(handler))) as client:
        meta = client.get_package_metadata("broken-pkg", fetch_github=False)

    assert meta.is_found is False
    assert "Malformed data" in (meta.raw_error or "")


def test_pypi_incomplete_metadata():
    """Missing or empty license and requires_python fields must be marked 'unknown'."""
    mock_payload = {
        "info": {
            "name": "bare-pkg",
            "version": "0.1.0",
            "summary": None,
            "requires_python": None,
            "requires_dist": None,
            "license": "UNKNOWN",
            "classifiers": [],
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_payload)

    with PyPIClient(client=httpx.Client(transport=httpx.MockTransport(handler))) as client:
        meta = client.get_package_metadata("bare-pkg", fetch_github=False)

    assert meta.is_found is True
    assert meta.requires_python == "unknown"
    assert meta.license == "unknown"
    assert meta.summary == "unknown"
    assert meta.requires_dist == []


def test_license_extracted_from_classifiers():
    """When info.license is omitted, license classifier must be used without inventing."""
    mock_payload = {
        "info": {
            "name": "classifier-pkg",
            "version": "1.0",
            "license": "",
            "classifiers": [
                "Programming Language :: Python :: 3",
                "License :: OSI Approved :: Apache Software License",
            ],
        }
    }

    def handler(request: httpx.Request) -> httpx.Response:
        return httpx.Response(200, json=mock_payload)

    with PyPIClient(client=httpx.Client(transport=httpx.MockTransport(handler))) as client:
        meta = client.get_package_metadata("classifier-pkg", fetch_github=False)

    assert meta.license == "Apache Software License"
