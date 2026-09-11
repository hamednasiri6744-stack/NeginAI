from pathlib import Path
import subprocess,sys,re,json
from datetime import datetime,timezone

root=Path(__file__).resolve().parents[1]
out=root/"artifacts"/"neginai-guardian"
protected=re.compile(r"(^|/)(\.env|data/.*\.(db|pem|key)|android/.*/signing/.*\.(jks|keystore))$",re.I)
secret=re.compile(r"(-----BEGIN .*PRIVATE KEY-----|\bsk-(?:proj-)?[A-Za-z0-9_-]{20,})")
danger=re.compile(r"(?i)(git\s+(reset\s+--hard|clean\s+-[a-z]*f|push\s+--force)|robocopy[^\r\n]*(/mir|/move))")
sqlwrite=re.compile(r"(?i)\b(insert\s+into|update\s+\S+\s+set|delete\s+from|merge\s+into|drop\s+table|alter\s+table|truncate\s+table|exec(?:ute)?\s+)\b")
domains={
"sales":["tour","visit","customercall","seller","route","ویزیت"],
"orders":["order","savedata","replicate","draft","idempot","سفارش"],
"pricing":["price","discount","offer","prize","tax","credit","قیمت","تخفیف","مالیات"],
"inventory":["stock","inventory","warehouse","انبار","موجودی"],
"logistics":["delivery","shipment","driver","vehicle","routing","توزیع","ارسال"],
"database":["sql","pyodbc","postgres","clickhouse","sqlite"]
}
def git(*a):
 p=subprocess.run(["git",*a],cwd=root,text=True,encoding="utf-8",errors="replace",capture_output=True)
 return p.stdout if p.returncode==0 else ""
def main():
 mode=(sys.argv[1] if len(sys.argv)>1 else "manual").lower()
 if mode=="pre-commit":
  files=git("diff","--cached","--name-only","--diff-filter=ACMR").splitlines(); diff=git("diff","--cached","--unified=0","--no-color")
 elif mode=="post-commit":
  files=git("diff-tree","--no-commit-id","--name-only","-r","HEAD").splitlines(); diff=git("show","--format=","--unified=0","--no-color","HEAD")
 else:
  files=(git("diff","--cached","--name-only")+"\n"+git("diff","--name-only")).splitlines(); diff=git("diff","--cached","--unified=0")+"\n"+git("diff","--unified=0")
 files=sorted({x.replace("\\","/") for x in files if x.strip()})
 added="\n".join(x[1:] for x in diff.splitlines() if x.startswith("+") and not x.startswith("+++"))
 findings=[]
 for f in files:
  if protected.search(f): findings.append({"level":"block","code":"protected-path","path":f})
 if secret.search(added): findings.append({"level":"block","code":"secret-detected"})
 if danger.search(added): findings.append({"level":"block","code":"destructive-command"})
 if sqlwrite.search(added): findings.append({"level":"warn","code":"sql-write-review"})
 hay=("\n".join(files)+"\n"+diff).lower()
 hit=[d for d,terms in domains.items() if any(t.lower() in hay for t in terms)]
 if hit: findings.append({"level":"review","code":"business-invariants","domains":hit})
 status="blocked" if any(x["level"]=="block" for x in findings) else "pass"
 r={"mode":mode,"status":status,"branch":git("branch","--show-current").strip(),"head":git("rev-parse","--short","HEAD").strip(),"changed_files":files,"domains":hit,"findings":findings,"timestamp":datetime.now(timezone.utc).isoformat()}
 out.mkdir(parents=True,exist_ok=True); (out/"latest.json").write_text(json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
 (out/"latest.md").write_text("# NeginAI Guardian\n\n"+json.dumps(r,ensure_ascii=False,indent=2),encoding="utf-8")
 print(f"[neginai-guardian] {mode} status={status} domains={','.join(hit) or 'none'}")
 return 1 if mode=="pre-commit" and status=="blocked" else 0
if __name__=="__main__": raise SystemExit(main())
