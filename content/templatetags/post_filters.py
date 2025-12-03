from django import template

register = template.Library()


@register.filter
def review_excerpt(value, length=80):
    """レビュー本文からカード用の抜粋を作る

    方針:
      1) 「レビュー」という見出し行(例: `## レビュー`)を探す
      2) その見出しより下の行から、本文らしい行を上から2行ひろう
      3) どうしても見つからない場合は、先頭からメタ情報を除いた行を2行ひろう
    """
    if not value:
        return ""

    import re as _re

    text = str(value)
    lines = [ln.strip() for ln in text.splitlines()]

    def is_meta_line(s: str) -> bool:
        """出演者・メーカー・サイズ・アフィURLなどのメタ情報かどうか"""
        if not s:
            return False
        # 見出し
        if s.startswith("#"):
            return True
        # 箇条書きでもメタ情報ワードを含むものは除外
        META_KEYS = (
            "出演者", "メーカー", "レーベル", "サイズ",
            "アフィリエイトURL", "アフィリエイトＵＲＬ",
            "サンプル動画", "サンプル画像",
        )
        return any(k in s for k in META_KEYS)

    picked = []

    # 1) 「レビュー」セクション優先
    in_review = False
    for ln in lines:
        s = ln.strip()
        if not s:
            continue

        # 「レビュー」という見出しを検出
        if _re.search(r"レビュー", s) and s.lstrip().startswith(("#", "##", "###")):
            in_review = True
            continue

        if not in_review:
            continue

        if is_meta_line(s):
            continue

        picked.append(s)
        if len(picked) >= 2:
            break

    # 2) レビューセクションから拾えなかったときは全体から拾う
    if not picked:
        for ln in lines:
            s = ln.strip()
            if not s:
                continue
            if is_meta_line(s):
                continue
            picked.append(s)
            if len(picked) >= 2:
                break

    if not picked:
        return ""

    body = " ".join(picked)

    try:
        length = int(length)
    except Exception:
        length = 80

    return body[:length]
