#!/usr/bin/env python3
"""Verifica as 4 fontes e adiciona no news.json cada capitulo novo.
Formato exibido no site: (dd/mm/aaaa) capitulo novo lançado! ~ link
Na 1a vez que uma fonte e vista, so memoriza os capitulos existentes (sem anunciar)."""
import json, re, sys, urllib.request, datetime, os
import xml.etree.ElementTree as ET

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
NEWS, STATE = os.path.join(ROOT, "news.json"), os.path.join(ROOT, "state.json")
UA = {"User-Agent": "Mozilla/5.0 (compatible; HaitatsuninNewsBot/1.0)"}
TEXT = "New chapter released!"

SOURCES = [
 {"key": "rr-pt", "label": "Royal Road [ PT ]", "kind": "rr", "id": "156210"},
 {"key": "rr-en", "label": "Royal Road [ EN ]", "kind": "rr", "id": "156420"},
 {"key": "syosetu", "label": "Shōsetsuka ni Narō [ JP ]", "kind": "syosetu", "id": "n0841ly"},
 {"key": "kakuyomu", "label": "Kakuyomu [ JP ]", "kind": "kakuyomu", "id": "2912051595782318117"},
]

def get(url):
    return urllib.request.urlopen(urllib.request.Request(url, headers=UA), timeout=30).read().decode("utf-8", "replace")

def chapters(s):
    """lista de URLs de capitulos, do mais antigo ao mais novo"""
    if s["kind"] == "rr":
        root = ET.fromstring(get(f"https://www.royalroad.com/fiction/syndication/{s['id']}"))
        items = [(i.findtext("pubDate") or "", i.findtext("link")) for i in root.iter("item")]
        from email.utils import parsedate_to_datetime
        items.sort(key=lambda x: parsedate_to_datetime(x[0]) if x[0] else datetime.datetime.min.replace(tzinfo=datetime.timezone.utc))
        return [l.strip() for _, l in items if l]
    if s["kind"] == "syosetu":
        nums = sorted({int(n) for n in re.findall(rf"/{s['id']}/(\d+)/?", get(f"https://ncode.syosetu.com/{s['id']}/"))})
        return [f"https://ncode.syosetu.com/{s['id']}/{n}/" for n in nums]
    html = get(f"https://kakuyomu.jp/works/{s['id']}")
    seen = []
    for e in re.findall(rf"/works/{s['id']}/episodes/(\d+)", html):
        if e not in seen: seen.append(e)
    return [f"https://kakuyomu.jp/works/{s['id']}/episodes/{e}" for e in seen]

def load(p, d):
    try:
        with open(p, encoding="utf-8") as f: return json.load(f)
    except Exception: return d

def main():
    news, state = load(NEWS, []), load(STATE, {})
    today = (datetime.datetime.now(datetime.timezone.utc) - datetime.timedelta(hours=3)).strftime("%d/%m/%Y")  # horario de Brasilia
    changed = False
    for s in SOURCES:
        try:
            urls = chapters(s)
        except Exception as e:
            print(f"[{s['key']}] erro: {e}", file=sys.stderr); continue
        if not urls:
            print(f"[{s['key']}] nenhum capitulo encontrado (site mudou?)", file=sys.stderr); continue
        known = state.get(s["key"])
        if known is None:
            state[s["key"]] = urls; changed = True; print(f"[{s['key']}] memorizados {len(urls)} capitulos"); continue
        new = [u for u in urls if u not in known]
        for u in new:  # do mais antigo ao mais novo; o mais novo fica no topo
            news.insert(0, {"date": today, "text": TEXT, "label": s["label"], "url": u})
            print(f"[{s['key']}] NOVO: {u}")
        if new:
            state[s["key"]] = known + new; changed = True
    if changed:
        json.dump(news, open(NEWS, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
        json.dump(state, open(STATE, "w", encoding="utf-8"), ensure_ascii=False, indent=1)

main()
