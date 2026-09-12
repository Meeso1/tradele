from pathlib import Path

from fastapi.testclient import TestClient

from app.container import container
from app.main import app

client = TestClient(app)


def test_unknown_api_path_returns_json_404():
    response = client.get("/api/does-not-exist")

    assert response.status_code == 404
    assert response.json() == {"detail": "Not Found"}

    # The catch-all covers all standard methods, not just the common ones.
    assert client.head("/api/does-not-exist").status_code == 404
    assert client.options("/api/does-not-exist").status_code == 404
    assert client.request("TRACE", "/api/does-not-exist").status_code == 404


def test_spa_returns_404_when_frontend_not_built():
    response = client.get("/")

    assert response.status_code == 404


def test_spa_serves_index_and_static_files():
    dist = Path(container.settings.frontend_dist_dir)
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html><body>tradele</body></html>")
    (dist / "favicon.ico").write_bytes(b"icon")
    (dist / "assets" / "app-123.js").write_text("console.log('tradele');")

    # The root and unknown client-side routes both serve index.html.
    assert client.get("/").text == "<html><body>tradele</body></html>"
    assert client.get("/some/client/route").text == "<html><body>tradele</body></html>"

    # Files directly in the dist root and under dist/assets/ are served as-is.
    assert client.get("/favicon.ico").content == b"icon"
    asset = client.get("/assets/app-123.js")
    assert asset.status_code == 200
    assert asset.text == "console.log('tradele');"


def test_spa_only_serves_allowlisted_locations():
    dist = Path(container.settings.frontend_dist_dir)
    (dist / "assets").mkdir(parents=True)
    (dist / "index.html").write_text("<html></html>")
    (dist / "sub").mkdir()
    (dist / "sub" / "secret.txt").write_text("secret")
    (dist.parent / "secret.txt").write_text("secret")

    # Files in nested directories other than assets/ are not served; the
    # request falls back to index.html.
    assert client.get("/sub/secret.txt").text == "<html></html>"

    # Traversal through /assets/ lands outside the allowlist, even when it
    # would resolve to an existing file.
    assert client.get("/assets/%2e%2e/%2e%2e/secret.txt").text == "<html></html>"


def test_spa_does_not_serve_files_outside_the_dist_directory():
    dist = Path(container.settings.frontend_dist_dir)
    dist.mkdir(parents=True)
    (dist / "index.html").write_text("<html></html>")

    # Percent-encoded traversal is decoded server-side; it must fall back
    # to index.html rather than serving tests/conftest.py.
    response = client.get("/%2e%2e/conftest.py")

    assert response.status_code == 200
    assert response.text == "<html></html>"
