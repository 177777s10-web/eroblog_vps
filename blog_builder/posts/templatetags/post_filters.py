from django import template
import re

register = template.Library()




# === review_excerpt: レビュー本文だけから 62 文字抜粋するフィルタ ===
import re as _re

@register.filter
def review_excerpt(text, limit=62):
    """post.review / post.review_body から
    - 見出し(#, ##) や画像(!) 行
    - 「* 出演者」「* メーカー」などの基本情報行
    を全て除外して、
    残った本文を 1 行にまとめて limit 文字＋「・・・」にする。
    """
    if not text:
        return ""

    s = str(text)

    lines = []
    for line in s.splitlines():
        line = line.strip()
        if not line:
            continue
        # 見出しと画像行は捨てる
        if line.startswith("#") or line.startswith("!"):
            continue
        # 基本情報系は捨てる
        if line.startswith("* 出演者")            or line.startswith("* メーカー")            or line.startswith("* レーベル")            or line.startswith("* サイズ")            or line.startswith("* アフィリエイトURL")            or line.startswith("* サンプル動画"):
            continue
        lines.append(line)

    if not lines:
        return ""

    s = " ".join(lines)
    s = _re.sub(r"\s+", " ", s)

    if len(s) > limit:
        return s[:limit] + "・・・"
    return s
