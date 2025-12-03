# -*- coding: utf-8 -*-
def merge(api: dict, probe: dict, samples: list, sample_filter) -> dict:
    d = dict(api or {})
    if probe.get("review_body") or probe.get("review") or probe.get("description"):
        d["review_body"] = probe.get("review_body") or probe.get("review") or probe.get("description")
    if probe.get("sizes") or probe.get("sizes_text"):
        d["sizes"] = probe.get("sizes") or probe.get("sizes_text")
    if probe.get("name") and not d.get("performers"):
        d["name"] = probe.get("name")
    if probe.get("label") and not d.get("series"):
        d["label"] = probe.get("label")
    d["sample_images"] = sample_filter(d.get("sample_images") or samples, d.get("cid"))
    return d
