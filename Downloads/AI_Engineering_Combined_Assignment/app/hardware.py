"""Safe, read-only Linux hardware inspection. No shell=True and no arbitrary commands."""
import os, re, shutil, subprocess, platform

ALLOWED = {"lscpu":["lscpu"], "lsblk":["lsblk","-J","-o","NAME,TYPE,SIZE,ROTA,TRAN,MODEL,MOUNTPOINT"],
           "free":["free","-b"], "lspci":["lspci","-mm"]}

def _run(key, timeout=3):
    if key not in ALLOWED: return None, "command is not allow-listed"
    exe=ALLOWED[key][0]
    if not shutil.which(exe): return None, f"{exe} is not installed"
    try:
        p=subprocess.run(ALLOWED[key],capture_output=True,text=True,timeout=timeout,check=False)
        if p.returncode != 0: return None, (p.stderr.strip() or f"{exe} exited with {p.returncode}")
        return p.stdout, None
    except (subprocess.TimeoutExpired, OSError) as e:
        return None, str(e)

def _read(path):
    try:
        with open(path,encoding="utf-8",errors="replace") as f: return f.read().strip()
    except (OSError, PermissionError): return None

def collect_hardware():
    data={"platform":platform.platform(),"system":platform.system(),"cpu":{},"memory":{},"disks":[],"gpu":[],"errors":[]}
    if platform.system() != "Linux":
        data["errors"].append("Hardware command collection is designed for Linux; platform metadata only is available.")
        return data
    out,err=_run("lscpu")
    if err: data["errors"].append(err)
    else:
        for line in out.splitlines():
            if ":" in line:
                k,v=line.split(":",1); data["cpu"][k.strip()]=v.strip()
    mem=_read("/proc/meminfo")
    if mem:
        for line in mem.splitlines():
            m=re.match(r"(MemTotal|MemAvailable|SwapTotal|SwapFree):\s+(\d+)\s+kB",line)
            if m: data["memory"][m.group(1)]=int(m.group(2))*1024
    else: data["errors"].append("Cannot read /proc/meminfo")
    out,err=_run("lsblk")
    if err: data["errors"].append(err)
    else:
        import json
        try:
            for d in json.loads(out).get("blockdevices",[]):
                if d.get("type")=="disk":
                    data["disks"].append({k:d.get(k) for k in ("name","size","rota","tran","model")})
        except (ValueError,TypeError): data["errors"].append("Could not parse lsblk JSON output")
    out,err=_run("lspci")
    if err: data["errors"].append(err)
    else:
        data["gpu"]=[line.strip() for line in out.splitlines() if re.search(r"vga|3d controller|display controller",line,re.I)]
    return data

def _gb(n):
    return f"{n/1_000_000_000:.1f} GB" if isinstance(n,(int,float)) else "unknown"

def answer_question(question, facts=None):
    facts=facts or collect_hardware()
    q=question.lower()
    if any(x in q for x in ("ram","memory")):
        total=facts.get("memory",{}).get("MemTotal")
        avail=facts.get("memory",{}).get("MemAvailable")
        if total:
            answer=f"This system has approximately {_gb(total)} of RAM."
            if avail: answer+=f" About {_gb(avail)} is currently available."
            return {"answer":answer,"sources":["/proc/meminfo"],"confidence":"high"}
        return {"answer":"I couldn't read the system memory information, so I can't confirm the RAM capacity.","sources":[],"confidence":"low"}
    if "cpu" in q or "processor" in q:
        cpu=facts.get("cpu",{})
        model=cpu.get("Model name") or cpu.get("Vendor ID")
        cores=cpu.get("CPU(s)")
        if model: return {"answer":f"Your CPU is {model}"+(f", with {cores} logical CPUs." if cores else "."),"sources":["lscpu"],"confidence":"high"}
        return {"answer":"CPU model information is unavailable on this system.","sources":[],"confidence":"low"}
    if any(x in q for x in ("ssd","nvme","disk","storage")):
        disks=facts.get("disks",[])
        if not disks: return {"answer":"I couldn't identify any physical disks from lsblk output.","sources":["lsblk"],"confidence":"low"}
        parts=[]
        for d in disks:
            typ="NVMe" if (d.get("tran") or "").lower()=="nvme" or d["name"].startswith("nvme") else ("rotational HDD" if d.get("rota")==True else "non-rotational drive; exact type not confirmed")
            parts.append(f"{d['name']} ({d.get('model') or 'model unknown'}): {d.get('size') or 'size unknown'}, {typ}")
        return {"answer":"Detected storage: "+"; ".join(parts)+".","sources":["lsblk"],"confidence":"high"}
    if "gpu" in q or "graphics" in q or "graphic" in q:
        g=facts.get("gpu",[])
        return {"answer":"Detected graphics hardware: "+"; ".join(g) if g else "No GPU entry was found in lspci output; this does not prove the machine has no graphics device.","sources":["lspci"],"confidence":"medium" if g else "low"}
    if any(x in q for x in ("slot","upgrade","maximum ram","max ram","add more ram")):
        return {"answer":"I can report installed RAM, but available DIMM slots and the motherboard's maximum supported capacity are not reliably exposed by the unprivileged read-only checks enabled here. I won't guess. Check the laptop's service manual or run an explicitly approved SMBIOS inspection if appropriate.","sources":["/proc/meminfo"],"confidence":"high"}
    if any(x in q for x in ("summary","hardware","specification","specs")):
        cpu=facts.get("cpu",{}).get("Model name","unknown CPU")
        mem=facts.get("memory",{}).get("MemTotal")
        disks=facts.get("disks",[])
        gpu=facts.get("gpu",[])
        return {"answer":f"Hardware summary — CPU: {cpu}; RAM: {_gb(mem)}; disks detected: {len(disks)}; GPU entries: {len(gpu)}.","sources":["lscpu","/proc/meminfo","lsblk","lspci"],"confidence":"medium"}
    return {"answer":"I can answer questions about CPU, RAM, storage/NVMe, GPU, and a general hardware summary. Please ask about one of those. I will not invent specifications that the system tools cannot verify.","sources":[],"confidence":"high"}
