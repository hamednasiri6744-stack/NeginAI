import argparse
import json
import sys
import urllib.request
from pathlib import Path

METHODS = ("get", "post", "put", "patch", "delete", "options", "head", "trace")
CONTRACT_KEYS = ("parameters", "requestBody", "responses", "security")


def load(source: str) -> dict:
    if source.startswith(("http://", "https://")):
        with urllib.request.urlopen(source, timeout=15) as response:
            return json.loads(response.read().decode("utf-8"))
    with Path(source).open(encoding="utf-8") as file:
        return json.load(file)


def operations(document: dict) -> dict:
    result = {}
    for path, path_item in document.get("paths", {}).items():
        for method in METHODS:
            if method in path_item:
                result[(path, method)] = path_item[method]
    return result


def contract(operation: dict) -> dict:
    return {key: operation[key] for key in CONTRACT_KEYS if key in operation}


def main() -> int:
    parser = argparse.ArgumentParser()
    parser.add_argument("--production", required=True, help="OpenAPI URL or JSON file")
    parser.add_argument("--local", required=True, help="OpenAPI URL or JSON file")
    parser.add_argument("--json-out", help="Optional report path")
    parser.add_argument("--allow-extra", action="store_true", help="Do not fail for local-only operations")
    args = parser.parse_args()

    prod = load(args.production)
    local = load(args.local)
    po, lo = operations(prod), operations(local)
    missing = sorted(set(po) - set(lo))
    extra = sorted(set(lo) - set(po))
    shared = sorted(set(po) & set(lo))
    drift = [
        {"path": path, "method": method.upper(), "production": contract(po[(path, method)]), "local": contract(lo[(path, method)])}
        for path, method in shared
        if contract(po[(path, method)]) != contract(lo[(path, method)])
    ]
    report = {
        "production_paths": len(prod.get("paths", {})),
        "production_operations": len(po),
        "local_paths": len(local.get("paths", {})),
        "local_operations": len(lo),
        "missing_operations": [{"path": p, "method": m.upper()} for p, m in missing],
        "extra_operations": [{"path": p, "method": m.upper()} for p, m in extra],
        "contract_drift": drift,
    }
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report, ensure_ascii=False, indent=2), encoding="utf-8")

    print(f"Production: {report['production_paths']} paths / {report['production_operations']} operations")
    print(f"Local:       {report['local_paths']} paths / {report['local_operations']} operations")
    print(f"Missing:     {len(missing)}")
    print(f"Extra:       {len(extra)}")
    print(f"Contract drift: {len(drift)}")
    for path, method in missing:
        print(f"MISSING {method.upper()} {path}")
    for item in drift:
        print(f"DRIFT {item['method']} {item['path']}")

    fail = bool(missing or drift or (extra and not args.allow_extra))
    return 1 if fail else 0


if __name__ == "__main__":
    raise SystemExit(main())
