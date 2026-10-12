"""Write the throwaway galaxy files. Fake numbers only. No game server."""
import json
from pathlib import Path

HERE = Path(__file__).resolve().parent


def build(n: int, seed: int) -> dict:
    rng = seed
    def rnd() -> float:
        nonlocal rng
        rng = (rng * 1103515245 + 12345) & 0x7FFFFFFF
        return rng / 0x7FFFFFFF
    nodes = []
    for i in range(1, n + 1):
        if i == 1:
            x = y = 0.0
        else:
            turn = i * 0.42
            radius = 18 + (i ** 0.5) * 14
            x = radius * __import__("math").cos(turn) + (rnd() - 0.5) * 8
            y = radius * __import__("math").sin(turn) + (rnd() - 0.5) * 8
        z = ((i * 17) % 11 - 5) * 0.6
        port = None
        if i != 1 and rnd() < 0.35:
            port = "".join("BS"[int(rnd() * 2)] for _ in range(3))
        nodes.append({"id": i, "x": round(x, 2), "y": round(y, 2), "z": z, "port": port})
    edges = []
    seen = set()
    def add(a: int, b: int) -> None:
        key = (a, b) if a < b else (b, a)
        if a == b or key in seen:
            return
        seen.add(key)
        oneway = rnd() < 0.15
        if oneway and rnd() < 0.5:
            a, b = b, a
        edges.append({"a": a, "b": b, "oneway": oneway})
    for i in range(2, n + 1):
        add(i, 1 + int(rnd() * (i - 1)))
    while len(edges) < int(n * 2.7) and len(edges) < n * (n - 1) // 2:
        add(1 + int(rnd() * n), 1 + int(rnd() * n))
    markers = []
    colors = ["#ff5a5a", "#5ad1ff", "#ffe14a", "#7dff7a", "#d07dff", "#ff9a3c", "#ffffff"]
    used = {1}
    markers.append({"seat": "P1", "sector": 1, "color": colors[0]})
    for k in range(1, 7):
        sector = 1 + int(rnd() * (n - 1))
        while sector in used:
            sector = 1 + int(rnd() * (n - 1))
        used.add(sector)
        markers.append({"seat": f"P{k + 1}", "sector": sector, "color": colors[k]})
    return {"nodes": nodes, "edges": edges, "markers": markers}


def main() -> None:
    small = build(40, 40)
    large = build(1000, 1000)
    (HERE / "galaxy-40.json").write_text(json.dumps(small), encoding="utf-8")
    (HERE / "galaxy-1000.json").write_text(json.dumps(large), encoding="utf-8")
    html = (HERE / "map.template.html").read_text(encoding="utf-8")
    html = html.replace("/*__SMALL__*/null", json.dumps(small))
    html = html.replace("/*__LARGE__*/null", json.dumps(large))
    (HERE / "map.html").write_text(html, encoding="utf-8")
    print(f"40 nodes, {len(small['edges'])} edges")
    print(f"1000 nodes, {len(large['edges'])} edges")


if __name__ == "__main__":
    main()
