from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
MAP_SOURCE = ROOT / "vnext" / "src" / "components" / "VisitorNeshanMap.tsx"


def test_vnext_neshan_map_stability_contract():
    source = MAP_SOURCE.read_text(encoding="utf-8")

    assert "if(!key||!host.current||map.current)return" in source
    assert "},[key,initNonce])" in source
    assert "},[key,plan,trustedPos])" not in source
    assert "focusTokenRef" in source
    assert "window.addEventListener('online',recover)" in source
    assert "document.addEventListener('visibilitychange',onVisible)" in source
    assert "current.getCenter?.()" in source
    assert "current.getZoom?.()" in source
    assert "current.setStyle?.(style)" in source
    assert "loadProxiedStyle" in source
    assert "/neshan-basemap/" in source
