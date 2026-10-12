

from __future__ import annotations

import hashlib
import json
import re
import sys
import urllib.request
import xml.etree.ElementTree as ET
from dataclasses import asdict, dataclass, field
from pathlib import Path

PARTS = [(46, "42"), (33, "157")]

API = "https://www.ecfr.gov/api/versioner/v1"
USER_AGENT = "regcite/0.1 (student research project; derin@thalwag.com)"

ROOT = Path(__file__).resolve().parent.parent
RAW_DIR = ROOT / "data" / "raw"
SECTIONS_FILE = ROOT / "data" / "sections.jsonl"
MANIFEST_FILE = ROOT / "data" / "manifest.json"


@dataclass
class Section:
    title: int
    section: str
    heading: str
    paragraphs: list[str] = field(default_factory=list)

    @property
    def cite(self) -> str:
        return f"{self.title} CFR {self.section}"

    @property
    def url(self) -> str:
        return f"https://www.ecfr.gov/current/title-{self.title}/section-{self.section}"

    @property
    def text(self) -> str:
        return "\n".join(self.paragraphs)



def _get(url: str) -> bytes:
    import gzip
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT, "Accept-Encoding": "gzip", "Accept": "*/*"})
    with urllib.request.urlopen(req, timeout=120) as resp:
        data = resp.read()
        try:
            return gzip.decompress(data)
        except Exception:
            return data

def latest_date(title: int) -> str:
    titles = json.loads(_get(f"{API}/titles.json"))["titles"]
    for t in titles:
        if t["number"] == title:
            return t["up_to_date_as_of"]
    raise RuntimeError(f"Title {title} not found in eCFR titles list")


def fetch() -> None:
    RAW_DIR.mkdir(parents=True, exist_ok=True)
    manifest = {"source": API, "parts": []}
    for title, part in PARTS:
        date = latest_date(title)
        url = f"{API}/full/{date}/title-{title}.xml?part={part}"
        print(f"Downloading {title} CFR Part {part} as of {date} ...")
        data = _get(url)
        path = RAW_DIR / f"title-{title}-part-{part}.xml"
        path.write_bytes(data)
        manifest["parts"].append({
            "title": title, "part": part, "date": date, "url": url,
            "file": path.name, "bytes": len(data),
            "sha256": hashlib.sha256(data).hexdigest(),
        })
        print(f"  saved {path.name}: {len(data):,} bytes")
    MANIFEST_FILE.write_text(json.dumps(manifest, indent=2))
    print(f"Manifest written to {MANIFEST_FILE.relative_to(ROOT)}")



_SKIP_TAGS = {"HEAD", "CITA", "SOURCE", "AUTH", "EDNOTE", "SECAUTH"}


def _clean(text: str) -> str:
    return re.sub(r"\s+", " ", text).strip()


def _table_text(table: ET.Element) -> list[str]:
    lines = []
    for row in table.iter():
        if row.tag in {"ROW", "BOXHD"}:
            cells = [_clean("".join(c.itertext())) for c in row]
            cells = [c for c in cells if c]
            if cells:
                lines.append(" | ".join(cells))
    return lines


def parse_xml(xml_bytes: bytes, title: int) -> list[Section]:
    root = ET.fromstring(xml_bytes)
    sections: list[Section] = []
    for div in root.iter():
        if not (div.tag.startswith("DIV") and div.get("TYPE") == "SECTION"):
            continue
        number = div.get("N", "").strip()
        head_el = div.find("HEAD")
        heading = _clean("".join(head_el.itertext())) if head_el is not None else ""
        heading = re.sub(r"^§+\s*[\w.\-]+\s*", "", heading)   # drop "§ 42.20-70"
        paras: list[str] = []
        for child in div:
            if child.tag in _SKIP_TAGS:
                continue
            if child.tag == "GPOTABLE":
                paras.extend(_table_text(child))
            else:
                t = _clean("".join(child.itertext()))
                if t:
                    paras.append(t)
        if number and paras and "[Reserved]" not in heading:
            sections.append(Section(title, number, heading, paras))
    if not sections:
        tags = sorted({el.tag for el in root.iter()})[:30]
        raise ValueError(
            "No sections found. The XML structure differs from what the parser "
            f"expects (DIVn elements with TYPE='SECTION'). Tags seen: {tags}"
        )
    return sections


def build() -> list[Section]:
    if not MANIFEST_FILE.exists():
        sys.exit("No downloaded text. Run: python -m regcite.corpus fetch")
    manifest = json.loads(MANIFEST_FILE.read_text())
    all_sections: list[Section] = []
    for p in manifest["parts"]:
        data = (RAW_DIR / p["file"]).read_bytes()
        if hashlib.sha256(data).hexdigest() != p["sha256"]:
            sys.exit(f"Checksum mismatch for {p['file']}: the file changed after download.")
        secs = parse_xml(data, p["title"])
        print(f"{p['title']} CFR Part {p['part']}: {len(secs)} sections, "
              f"{sum(len(s.paragraphs) for s in secs)} paragraphs")
        all_sections.extend(secs)
    save_sections(all_sections, SECTIONS_FILE)
    print(f"Wrote {len(all_sections)} sections to {SECTIONS_FILE.relative_to(ROOT)}")
    return all_sections


def save_sections(sections: list[Section], path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8") as f:
        for s in sections:
            f.write(json.dumps(asdict(s), ensure_ascii=False) + "\n")


def load_sections(path: Path = SECTIONS_FILE) -> list[Section]:
    if not path.exists():
        sys.exit("No parsed sections. Run: python -m regcite.corpus fetch, then build")
    with path.open(encoding="utf-8") as f:
        return [Section(**json.loads(line)) for line in f if line.strip()]



@dataclass
class Passage:
    section: Section
    index: int
    text: str

    @property
    def label(self) -> str:
        m = re.match(r"\((\w+)\)", self.text)
        return f"{self.section.cite}({m.group(1)})" if m else self.section.cite


def passages(sections: list[Section], min_words: int = 40, max_words: int = 180) -> list[Passage]:
    out: list[Passage] = []
    for s in sections:
        buf: list[str] = []
        count = 0
        for para in s.paragraphs:
            n = len(para.split())
            if buf and count + n > max_words and count >= min_words:
                out.append(Passage(s, len(out), " ".join(buf)))
                buf, count = [], 0
            buf.append(para)
            count += n
        if buf:
            out.append(Passage(s, len(out), " ".join(buf)))
    return out


if __name__ == "__main__":
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "fetch":
        fetch()
    elif cmd == "build":
        build()
    else:
        print(__doc__)
