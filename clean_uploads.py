import os, time, shutil
from pathlib import Path

TTL_HOURS = int(os.getenv("UPLOADS_TTL_HOURS", "6"))
GC_INTERVAL_MIN = int(os.getenv("UPLOADS_GC_MIN", "30"))
ROOT = os.getenv("UPLOADS_ROOT", "uploads")
 
def main():
    ttl = TTL_HOURS * 3600
    while True:
        now = time.time()
        base = Path(os.getcwd()) / ROOT
        if base.exists():
            for kind_dir in base.iterdir():
                if not kind_dir.is_dir():
                    continue
                for sid_dir in kind_dir.iterdir():
                    if not sid_dir.is_dir():
                        continue
                    age = now - sid_dir.stat().st_mtime
                    if age > ttl:
                        shutil.rmtree(sid_dir, ignore_errors=True)
        time.sleep(GC_INTERVAL_MIN * 60)

if __name__ == "__main__":
    main()
