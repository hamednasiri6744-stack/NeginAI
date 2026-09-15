import argparse
import json
import urllib.request
from pathlib import Path

METHODS = ("get", "post", "put", "patch", "delete", "options", "head", "trace")
DOC_KEYS = {"title", "description", "summary", "examples", "example", "externalDocs"}

def load(source):
    if source.startswith(("http://","https://")):
        with urllib.request.urlopen(source, timeout=15) as r:
            return json.loads(r.read().decode("utf-8"))
    with Path(source).open(encoding="utf-8") as f:
        return json.load(f)

def operations(doc):
    return {(p,m): item[m] for p,item in doc.get("paths",{}).items() for m in METHODS if m in item}

def normalize(v):
    if isinstance(v, dict):
        return {k: normalize(x) for k,x in v.items() if k not in DOC_KEYS}
    if isinstance(v, list):
        return [normalize(x) for x in v]
    return v

def schema_accepts(p,l):
    p,l=normalize(p or {}),normalize(l or {})
    if p==l: return True
    if "anyOf" in l: return any(schema_accepts(p,b) for b in l["anyOf"])
    if "oneOf" in l: return any(schema_accepts(p,b) for b in l["oneOf"])
    if "anyOf" in p: return all(schema_accepts(b,l) for b in p["anyOf"])
    if "oneOf" in p: return all(schema_accepts(b,l) for b in p["oneOf"])
    return False

def pmap(op):
    return {(str(x.get("in","")),str(x.get("name",""))):x for x in op.get("parameters",[])}

def params_ok(p,l):
    pp,ll=pmap(p),pmap(l); reasons=[]
    for key,x in pp.items():
        y=ll.get(key)
        if y is None: reasons.append(f"missing parameter {key[0]}:{key[1]}"); continue
        if not x.get("required",False) and y.get("required",False):
            reasons.append(f"optional production parameter became required {key[0]}:{key[1]}")
        if not schema_accepts(x.get("schema",{}),y.get("schema",{})):
            reasons.append(f"parameter schema narrowed {key[0]}:{key[1]}")
    for key,y in ll.items():
        if key not in pp and y.get("required",False):
            reasons.append(f"new required parameter {key[0]}:{key[1]}")
    return reasons

def body_ok(p,l):
    a,b=p.get("requestBody"),l.get("requestBody")
    if a is None:
        return ["new required request body"] if b is not None and b.get("required",False) else []
    if b is None: return ["production request body missing locally"]
    reasons=[]
    if not a.get("required",False) and b.get("required",False):
        reasons.append("optional production request body became required")
    for media,x in a.get("content",{}).items():
        y=b.get("content",{}).get(media)
        if y is None: reasons.append(f"missing request media type {media}")
        elif not schema_accepts(x.get("schema",{}),y.get("schema",{})):
            reasons.append(f"request schema narrowed for {media}")
    return reasons

def responses_ok(p,l):
    reasons=[]
    for status,x in p.get("responses",{}).items():
        y=l.get("responses",{}).get(status)
        if y is None: reasons.append(f"missing response {status}")
        elif normalize(x)!=normalize(y): reasons.append(f"response contract changed {status}")
    return reasons

def security_ok(p,l):
    return [] if normalize(p.get("security",[]))==normalize(l.get("security",[])) else ["security contract changed"]

def raw(op):
    return {k:op[k] for k in ("parameters","requestBody","responses","security") if k in op}

def main():
    ap=argparse.ArgumentParser()
    ap.add_argument("--production",required=True)
    ap.add_argument("--local",required=True)
    ap.add_argument("--json-out")
    ap.add_argument("--allow-extra",action="store_true")
    args=ap.parse_args()
    prod,local=load(args.production),load(args.local)
    po,lo=operations(prod),operations(local)
    missing=sorted(set(po)-set(lo)); extra=sorted(set(lo)-set(po)); shared=sorted(set(po)&set(lo))
    breaking=[]; extensions=[]
    for path,method in shared:
        p,l=po[(path,method)],lo[(path,method)]
        if normalize(raw(p))==normalize(raw(l)): continue
        reasons=params_ok(p,l)+body_ok(p,l)+responses_ok(p,l)+security_ok(p,l)
        item={"path":path,"method":method.upper(),"reasons":reasons}
        (breaking if reasons else extensions).append(item)
    report={
        "production_paths":len(prod.get("paths",{})),
        "production_operations":len(po),
        "local_paths":len(local.get("paths",{})),
        "local_operations":len(lo),
        "missing_operations":[{"path":p,"method":m.upper()} for p,m in missing],
        "extra_operations":[{"path":p,"method":m.upper()} for p,m in extra],
        "breaking_contract_drift":breaking,
        "compatible_contract_extensions":extensions,
    }
    if args.json_out:
        Path(args.json_out).write_text(json.dumps(report,ensure_ascii=False,indent=2),encoding="utf-8")
    print(f"Production: {report['production_paths']} paths / {report['production_operations']} operations")
    print(f"Local:       {report['local_paths']} paths / {report['local_operations']} operations")
    print(f"Missing:     {len(missing)}")
    print(f"Extra:       {len(extra)}")
    print(f"Breaking drift: {len(breaking)}")
    print(f"Compatible extensions: {len(extensions)}")
    for p,m in missing: print(f"MISSING {m.upper()} {p}")
    for x in breaking: print(f"BREAKING {x['method']} {x['path']}: {'; '.join(x['reasons'])}")
    for x in extensions: print(f"EXTENSION {x['method']} {x['path']}")
    return 1 if (missing or breaking or (extra and not args.allow_extra)) else 0

if __name__=="__main__":
    raise SystemExit(main())
