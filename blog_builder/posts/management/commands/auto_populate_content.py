# -*- coding: utf-8 -*-
import json
import re
from pathlib import Path

from django.core.exceptions import FieldDoesNotExist
from django.core.management.base import BaseCommand, CommandError
from django.db import transaction
from posts.models import Post


def safe_assign(instance, field_name, value):
    """
    Post にそのフィールドがあり、かつ ManyToMany でなければ代入する。
    フィールドが無ければ何もしない。
    """
    if value is None:
        return
    model = instance.__class__
    try:
        field = model._meta.get_field(field_name)
    except FieldDoesNotExist:
        return
    from django.db.models.fields.related import ManyToManyField
    if isinstance(field, ManyToManyField):
        return
    setattr(instance, field_name, value)


def parse_sizes_to_bwh(sizes_text):
    """
    'T158 B88 W57 H84' のような文字列から B/W/H を整数で取り出す。
    取れなければ None を返す。
    """
    if not sizes_text:
        return None, None, None
    m_b = re.search(r"B(\d+)", sizes_text)
    m_w = re.search(r"W(\d+)", sizes_text)
    m_h = re.search(r"H(\d+)", sizes_text)
    b = int(m_b.group(1)) if m_b else None
    w = int(m_w.group(1)) if m_w else None
    h = int(m_h.group(1)) if m_h else None
    return b, w, h


class Command(BaseCommand):
    help = "FANZA enriched JSONL から Post モデルにデータを登録する"

    def add_arguments(self, parser):
        parser.add_argument(
            "--jsonl",
            required=True,
            help="入力となる JSONL ファイルへのパス",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="DB には書き込まず、内容だけ表示する",
        )

    def handle(self, *args, **options):
        jsonl_path = Path(options["jsonl"])
        dry_run = options["dry_run"]

        if not jsonl_path.exists():
            raise CommandError(f"JSONL ファイルが見つかりません: {jsonl_path}")

        lines = [
            ln.strip()
            for ln in jsonl_path.read_text(encoding="utf-8").splitlines()
            if ln.strip()
        ]
        if not lines:
            self.stdout.write(self.style.WARNING("JSONL が空のため、何も行いません"))
            return

        created = 0
        skipped = 0
        errors = 0

        for idx, line in enumerate(lines, 1):
            try:
                data = json.loads(line)
            except json.JSONDecodeError as e:
                errors += 1
                self.stderr.write(f"[WARN] {idx} 行目の JSON パースに失敗: {e}")
                continue

            cid = data.get("cid")
            if not cid:
                errors += 1
                self.stderr.write(f"[WARN] {idx} 行目: cid が無いためスキップ")
                continue

            if Post.objects.filter(cid=cid).exists():
                skipped += 1
                self.stdout.write(f"[SKIP] cid={cid} は既に登録済み")
                continue

            post = Post(cid=cid)

            title = data.get("title") or cid
            safe_assign(post, "title", title)

            name = data.get("name")
            if not name:
                performers = data.get("performers") or []
                if performers:
                    first = performers[0]
                    if isinstance(first, dict):
                        name = first.get("name") or first.get("title")
                    else:
                        name = str(first)
            safe_assign(post, "name", name)

            review = (
                data.get("review_body")
                or data.get("review")
                or data.get("description")
            )
            safe_assign(post, "review_html", review)

            safe_assign(post, "maker", data.get("maker"))
            safe_assign(post, "label", data.get("label"))
            safe_assign(post, "series", data.get("series"))

            safe_assign(post, "affiliate_url", data.get("affiliate_url"))
            safe_assign(post, "sample_movie_url", data.get("sample_movie_url"))
            safe_assign(post, "poster_url", data.get("poster_url"))

            imgs = data.get("sample_images") or []
            if imgs:
                imgs = imgs[:10]
                safe_assign(post, "sample_images", imgs)

            sizes_text = data.get("sizes") or data.get("sizes_text")
            if sizes_text:
                safe_assign(post, "sizes", sizes_text)
                b, w, h = parse_sizes_to_bwh(sizes_text)
                if b is not None:
                    safe_assign(post, "bust", b)
                if w is not None:
                    safe_assign(post, "waist", w)
                if h is not None:
                    safe_assign(post, "hip", h)

            if dry_run:
                self.stdout.write(
                f"[DRY-RUN] cid={cid} title={getattr(post, 'title', '')}"
                )
                continue

            try:
                with transaction.atomic():
                    post.save()
                created += 1
                self.stdout.write(
                    self.style.SUCCESS(
                        f"[OK] created cid={cid} id={post.id} title={post.title}"
                    )
                )
            except Exception as e:
                errors += 1
                self.stderr.write(
                    f"[ERROR] cid={cid} の保存に失敗しました: {e}"
                )

        self.stdout.write(
            self.style.SUCCESS(
                f"完了: created={created}, skipped_existing={skipped}, errors={errors}"
            )
        )
