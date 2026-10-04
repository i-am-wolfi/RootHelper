# ROM/root fetchers (pure functions, no userbot deps) — shared logic ported from KannaX

"""buscas web: ofox, los, cr, axion, ksu, lsp, apatch, zygisk, xfw, ngapps, gsm device"""

import datetime
import os
import re
import time
import xml.etree.ElementTree as ET

import requests
from bs4 import BeautifulSoup

_UA = {"User-Agent": "Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 Chrome/120 Safari/537.36"}
_GH = {"User-Agent": "KannaX-bot"}
CACHE = os.environ.get("DATA_DIR", "data")


def _human_size(num):
    num = num or 0
    for unit in ("B", "KB", "MB", "GB"):
        if num < 1024 or unit == "GB":
            return f"{num:.1f} {unit}" if unit != "B" else f"{num} {unit}"
        num /= 1024
    return f"{num:.1f} GB"


def _gh_releases(repo):
    """(latest_tag, {asset_name: url}) via web (API costuma estar desativada)."""
    page = requests.get(f"https://github.com/{repo}/releases", headers=_UA, timeout=60)
    page.raise_for_status()
    org, name = repo.split("/")
    tags = list(dict.fromkeys(re.findall(rf"/{org}/{name}/releases/tag/([^\"']+)", page.text)))
    if not tags:
        raise RuntimeError("nenhuma release encontrada")
    tag = tags[0]
    assets = requests.get(
        f"https://github.com/{repo}/releases/expanded_assets/{tag}",
        headers={"Accept": "text/html", **_UA}, timeout=60)
    assets.raise_for_status()
    out = {}
    for href in sorted(set(re.findall(r'href="([^"]+)"', assets.text))):
        if href.endswith((".apk", ".zip")):
            out[href.rsplit("/", 1)[1]] = href if href.startswith("http") else f"https://github.com{href}"
    return tag, out


# ---- root ----
def ksu():
    tag, assets = _gh_releases("tiann/KernelSU")
    apk = next(iter(assets.values()))
    return f"🔓 **KernelSU `{tag}`**\n\n⬇️ [Manager APK]({apk})"


def lsp():
    tag, assets = _gh_releases("LSPosed/LSPosed")
    lines = [f"🧩 **LSPosed `{tag}`**", ""]
    for name, url in assets.items():
        flavor = "riru" if "riru" in name.lower() else ("zygisk" if "zygisk" in name.lower() else "zip")
        lines.append(f"⬇️ [{flavor}]({url})")
    return "\n".join(lines)


def zygisk():
    tag, assets = _gh_releases("LSPosed/ZygiskNext")
    lines = [f"⚡ **ZygiskNext `{tag}`**", ""]
    for name, url in assets.items():
        lines.append(f"⬇️ [{name}]({url})")
    return "\n".join(lines)


def apatch():
    page = requests.get("https://github.com/bmax121/APatch/releases", headers=_UA, timeout=60)
    page.raise_for_status()
    tags = list(dict.fromkeys(re.findall(r"/bmax121/APatch/releases/tag/(\d+)", page.text)))
    if not tags:
        raise RuntimeError("nenhuma release encontrada")
    tag = tags[0]
    assets = requests.get(
        f"https://github.com/bmax121/APatch/releases/expanded_assets/{tag}",
        headers={"Accept": "text/html", **_UA}, timeout=60)
    assets.raise_for_status()
    for href in re.findall(r'href="([^"]+)"', assets.text):
        if href.endswith(".apk"):
            url = href if href.startswith("http") else f"https://github.com{href}"
            return f"🩹 **APatch `{tag}`**\n\n⬇️ [Baixar APK]({url})"
    raise RuntimeError(f"sem APK na release {tag}")


# ---- roms ----
def ofox(code, want="stable"):
    code = code.strip().lower()
    devs = requests.get("https://api.orangefox.download/v3/devices", timeout=60).json().get("data", [])
    exact = [d for d in devs if code in [d.get("codename", "").lower()] + [n.lower() for n in (d.get("codenames") or []) if n]]
    if not exact:
        return f"`recovery não achada para {code}!`"
    dev = exact[0]
    rels = requests.get("https://api.orangefox.download/v3/releases",
                        params={"device_id": dev["id"]}, timeout=60).json().get("data", [])
    rels = [r for r in rels if r.get("device_id") == dev["id"]]
    pool = [r for r in rels if r.get("type") == want] or rels
    if not pool:
        return f"`sem build {want} para {code}!`"
    active = [r for r in pool if not r.get("archived")] or pool
    s = max(active, key=lambda r: r.get("date", 0))
    date = datetime.datetime.fromtimestamp(s.get("date", 0)).strftime("%Y-%m-%d")
    dl = s.get("url") or ""
    if not dl and isinstance(s.get("mirrors"), list) and s["mirrors"]:
        dl = s["mirrors"][0].get("url", "")
    maint = (dev.get("maintainer") or {}).get("name", "?")
    clog = "\n".join(f"• {c}" for c in (s.get("changelog") or [])[:8])
    msg = (f"📱 **Device**: {dev.get('full_name', code)}\n👤 **Maintainer**: {maint}\n\n"
           f"🦊 `{s.get('filename', '?')}`\n📅 {date}\nℹ️ **Version:** {s.get('version', '?')}\n"
           f"📌 **Build Type:** {s.get('type', '?')}\n🔰 **Size:** {_human_size(s.get('size', 0))}\n")
    if clog:
        msg += f"\n📍 **Changelog:**\n`{clog}`\n"
    return msg + f"\n⬇️ [DOWNLOAD]({dl})"


def los(code):
    code = code.strip().lower()
    dev = requests.get(f"https://download.lineageos.org/api/v2/devices/{code}", timeout=60)
    if dev.status_code == 400:
        return f"`{code} sem suporte no LineageOS oficial.`"
    dev.raise_for_status()
    dev = dev.json()
    builds = requests.get(f"https://download.lineageos.org/api/v2/devices/{code}/builds", timeout=60).json()
    zips = []
    for b in builds:
        for f in b.get("files", []):
            if f.get("filename", "").endswith(".zip"):
                zips.append((b.get("datetime", 0), f))
    if not zips:
        return f"`Sem builds para {code}.`"
    zips.sort(reverse=True)
    build = zips[0][1]
    date = datetime.datetime.fromtimestamp(build.get("datetime", 0)).strftime("%Y-%m-%d")
    return (f"📱 **Aparelho**: {dev.get('name', code)}\n🏭 **OEM**: {dev.get('oem', '?')}\n"
            f"📦 **Versões**: {', '.join(dev.get('versions', []))}\n\n"
            f"🦊 `{build.get('filename', '?')}`\n📅 {date}\n🔰 **{_human_size(build.get('size', 0))}**\n"
            f"🔑 **SHA256:** `{build.get('sha256', '?')[:16]}...`\n🩹 **Patch:** {build.get('os_patch_level', '?')}\n\n"
            f"⬇️ [DOWNLOAD]({build.get('url', '')}) | 📖 [WIKI]({dev.get('info_url', '')})")


def cr(code, want=0):
    code = code.strip().lower()
    page = requests.get(f"https://crdroid.net/{code}", headers=_UA, timeout=60)
    if page.status_code == 404:
        return f"`{code} sem suporte na crDroid.`"
    page.raise_for_status()
    vers = sorted({int(v) for v in re.findall(rf"{re.escape(code)}/(\d+)", page.text)})
    if not vers:
        return f"`{code} sem suporte na crDroid.`"
    want = want or max(vers)
    if want not in vers:
        return f"`crDroid {want} não existe para {code}. Versões: {vers}`"
    html = requests.get(f"https://crdroid.net/{code}/{want}", headers=_UA, timeout=60).text
    txt = BeautifulSoup(html, "html.parser").get_text(" | ", strip=True)

    def field(label):
        m = re.search(rf"{label} \| ([^|]+)", txt)
        return m.group(1).strip() if m else "?"

    zips = re.findall(r"https://sourceforge\.net/projects/crdroid/files/[^\"']+\.zip/download", html)
    clog = re.findall(r"(changelog/[^\"']+\.txt)", html)
    md5 = re.findall(r"value=['\"]([a-f0-9]{32})['\"]", html)
    msg = (f"📱 **crDroid {field('Version')} — {code}**\n👤 **Maintainer:** {field('Maintainer')}\n"
           f"🤖 **Android:** {field('Android')}\n📅 **Build:** {field('Build date')} | 🔰 **{field('ZIP size')}**\n")
    if md5:
        msg += f"🔑 **MD5:** `{md5[0]}`\n"
    msg += "\n"
    if zips:
        msg += f"⬇️ [DOWNLOAD]({zips[0]})\n"
    if clog:
        cu = clog[0] if clog[0].startswith("http") else f"https://crdroid.net/{clog[0]}"
        msg += f"📝 [Changelog]({cu})\n"
    return msg + f"🌐 [Outras versões](https://crdroid.net/{code})"


def axion(code, variant="VANILLA"):
    code = code.strip().lower()
    resp = requests.get(
        f"https://raw.githubusercontent.com/AxionAOSP/official_devices/main/OTA/{variant}/{code}.json",
        headers={"User-Agent": "KannaX-bot"}, timeout=60)
    if resp.status_code == 404:
        return f"`{code} sem build {variant}.`"
    resp.raise_for_status()
    builds = resp.json().get("response", [])
    if not builds:
        return f"`{code} sem build {variant}.`"
    b = max(builds, key=lambda x: x.get("datetime", 0))
    date = datetime.datetime.fromtimestamp(b.get("datetime", 0)).strftime("%Y-%m-%d")
    return (f"📱 **AxionOS {b.get('version', '?')} {variant} — {code}**\n"
            f"🦊 `{b.get('filename', '?')}`\n📅 {date} | 🔰 **{_human_size(b.get('size', 0))}**\n\n"
            f"⬇️ [DOWNLOAD]({b.get('url', '')})")


def xfw(code):
    code = code.strip().lower()
    resp = requests.get(
        f"https://raw.githubusercontent.com/XiaomiFirmwareUpdater/miui-updates-tracker/master/rss/{code}.xml",
        headers=_UA, timeout=60)
    if resp.status_code == 404:
        return f"`Nada achado para {code}. Confira o codinome.`"
    resp.raise_for_status()
    items = []
    for item in ET.fromstring(resp.content).find("channel").findall("item")[:4]:
        title = item.findtext("title") or ""
        link = item.findtext("link") or ""
        desc = re.sub(r"<[^>]+>", " ", item.findtext("description") or "")
        size = re.search(r"Size:\s*([0-9.]+ ?[GMK]B)", desc)
        kind = "Fastboot" if "fastboot" in title.lower() else ("Recovery" if "recovery" in title.lower() else "Update")
        short = re.sub(r"\s+(Fastboot|Recovery) update.*$", "", title, flags=re.IGNORECASE)
        items.append(f"• [{kind}]({link}) — {short} ({size.group(1) if size else '?'})")
    return f"📱 **Firmware {code}** (mais recentes)\n\n" + "\n".join(items)


NG_LETTERS = {"12": "S", "13": "T", "14": "U", "15": "V", "16": "B"}
NG_VARIANTS = ["Core", "Pico", "Basic", "Omni", "Stock", "Full"]


def ngapps(ver="", var=""):
    sf = "https://sourceforge.net/projects/nikgapps/files/Releases"
    var = {"pico": "Core", "nano": "Core", "micro": "Basic"}.get(var.lower(), var.capitalize() if var else "")
    if var and var not in NG_VARIANTS:
        return f"`Variante inválida. Use: {', '.join(NG_VARIANTS)}`"
    if not ver or ver not in NG_LETTERS:
        return ("**NikGapps** — `,ngapps [android 12-16] [variante]`\n"
                f"Variantes: {' | '.join(NG_VARIANTS)} (Pico = Core)\n📂 [Todas as releases]({sf})")
    folder = f"{sf}/NikGapps-{NG_LETTERS[ver]}/"
    if not var:
        lines = [f"📦 **NikGapps Android {ver}**\n"] + [f"• [{v}]({folder})" for v in NG_VARIANTS]
        return "\n".join(lines)
    return (f"📦 **NikGapps {var} — Android {ver}**\n\n⬇️ [Pasta da release]({folder})\n"
            f"Arquivo: `NikGapps-{var}-arm64-{ver}-DATA-signed.zip`\n💬 [Canal @NikGapps](https://t.me/NikGapps)")


# ---- gsm device ----
def _gsm_index():
    import json as _json
    os.makedirs(f"{CACHE}/.gsm_cache", exist_ok=True)
    path = f"{CACHE}/.gsm_cache/phones.xml"
    if not os.path.isfile(path) or time.time() - os.path.getmtime(path) > 7 * 24 * 3600:
        r = requests.get("https://www.gsmarena.com/sitemaps/phones.xml", headers=_UA, timeout=120)
        r.raise_for_status()
        open(path, "wb").write(r.content)
    xml = open(path, encoding="utf-8", errors="replace").read()
    return [(u.rsplit("/", 1)[1][:-4].rsplit("-", 1)[0].replace("_", " "), u)
            for u in re.findall(r"<loc>(https://www\.gsmarena\.com/[a-z0-9_\-]+\.php)</loc>", xml)
            if "-pictures-" not in u]


def gsm_search(query, limit=6):
    def norm(t):
        return [x for x in re.sub(r"[^a-z0-9]+", " ", t.lower()).split() if x]

    def variants(q):
        out = [q]
        v2 = re.sub(r"[a-z]+$", "", q.strip().lower()).strip()
        if v2 and v2 not in out:
            out.append(v2)
        m = re.match(r"^([a-z]+)\d*?(\d)", v2.split()[0] if v2 else "")
        if m:
            v3 = " ".join([f"{m.group(1)}{m.group(2)}"] + v2.split()[1:])
            if v3 not in out:
                out.append(v3)
        return out

    qt = norm(query)
    if not qt:
        return []
    index = _gsm_index()
    for variant in variants(query):
        vt = norm(variant)
        scored = []
        for name, url in index:
            nt = set(norm(name))
            flat = name.replace(" ", "")
            hits = exact = 0
            for t in vt:
                if t in nt:
                    hits += 1
                    exact += 1
                elif len(t) > 1 and t in flat:
                    hits += 1
            if not hits:
                continue
            m = re.search(r"-(\d+)\.php$", url)
            scored.append((hits / len(vt), exact, -(len(nt) - hits), int(m.group(1)) if m else 0, name, url))
        scored.sort(reverse=True)
        if scored and scored[0][0] == 1.0:
            return [(n, u) for _, _, _, _, n, u in scored[:limit]]
    scored.sort(reverse=True)
    return [(n, u) for _, _, _, _, n, u in scored[:limit]]


def gsm_card(name, url):
    def vals(sec, want=None):
        out = specs.get(sec, [])
        return [(t, v) for t, v in out if v and (want is None or t in want)]

    resp = requests.get(url, headers=_UA, timeout=60)
    resp.raise_for_status()
    soup = BeautifulSoup(resp.content, "html.parser")
    h1 = soup.find("h1")
    name = h1.get_text(strip=True) if h1 else name
    hl = {}
    for k, v in re.findall(r'data-spec="([a-z0-9\-]+)"[^>]*>([^<]{0,200})', resp.text):
        v = v.strip()
        if v and k not in hl:
            hl[k] = v
    cur, specs, picked = "", {}, {}
    for tr in soup.select("#specs-list tr"):
        th = tr.find("th")
        if th:
            cur = th.get_text(strip=True)
            continue
        ttl = tr.find("td", class_="ttl")
        nfo = tr.find("td", class_="nfo")
        if ttl and nfo and (cur, ttl.get_text(strip=True)) not in picked:
            picked[(cur, ttl.get_text(strip=True))] = nfo.get_text(" ", strip=True)
            specs.setdefault(cur, []).append((ttl.get_text(strip=True), nfo.get_text(" ", strip=True)))

    def g(sec, ttl):
        for t, v in specs.get(sec, []):
            if t == ttl:
                return v
        return ""

    bsize = hl.get("batsize-hl", "")
    bsize = bsize if "mah" in bsize.lower() else (f"{bsize} mAh" if bsize else "")
    btype = g("Battery", "Type")
    batt = btype if btype and "mah" in btype.lower() else (f"{bsize} ({btype})" if bsize and btype else (bsize or btype))
    disp = "\n".join(v for v in (hl.get("displaytype", ""), g("Display", "Size"), g("Display", "Resolution")) if v)
    chip = "\n".join(v for v in (g("Platform", "Chipset"), g("Platform", "CPU"), g("Platform", "GPU")) if v)
    rows = [
        ("Status", hl.get("status", "") or g("Launch", "Status")),
        ("Network", hl.get("nettech", "")),
        ("WiFi", hl.get("wlan", "")),
        ("Bluetooth", hl.get("bluetooth", "") or g("Comms", "Bluetooth")),
        ("Weight", hl.get("weight", "") or g("Body", "Weight")),
        ("Display", disp),
        ("Chipset", chip),
        ("Memory", hl.get("internalmemory", "") or g("Memory", "Internal")),
        ("Rear Camera", hl.get("cam1modules", "")),
        ("Front Camera", hl.get("cam2modules", "")),
        ("3.5mm jack", g("Sound", "3.5mm jack")),
        ("USB", g("Comms", "USB")),
        ("Sensors", hl.get("sensors", "")),
        ("Battery", batt),
    ]
    lines = [f"[{name}]({url})", ""]
    for label, val in rows:
        if not val:
            continue
        lines.append(f"**{label}:**\n{val}" if "\n" in val else f"**{label}:** {val}")
        lines.append("")
    img = soup.select_one(".specs-photo-main img")
    photo = img["src"] if img and img.get("src") else ""
    return "\n".join(lines).rstrip(), photo
