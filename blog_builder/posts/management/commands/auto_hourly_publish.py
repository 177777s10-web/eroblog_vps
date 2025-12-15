import json
from pathlib import Path

from django.core.management.base import BaseCommand
from django.utils import timezone
from django.apps import apps


JSONL_PATH = Path("/root/eroblog/data_getter/out/videoc_latest_enriched.jsonl")


class Command(BaseCommand):
    help = "Publish all new CIDs found in videoc_latest_enriched.jsonl (multi-line supported)."

    def handle(self, *args, **options):
        Post = apps.get_model("posts", "Post")

        if not JSONL_PATH.exists():
            self.stdout.write(self.style.WARNING(f"SKIP: jsonl not found: {JSONL_PATH}"))
            return

        raw = JSONL_PATH.read_text(encoding="utf-8").strip()
        if not raw:
            self.stdout.write(self.style.WARNING("SKIP: jsonl is empty"))
            return

        model_fields = {f.name for f in Post._meta.get_fields()}

        created = 0
        skipped = 0

        for line in raw.splitlines():
            line = line.strip()
            if not line:
                continue

            try:
                item = json.loads(line)
            except Exception:
                self.stdout.write(self.style.WARNING("SKIP: invalid json line"))
                continue

            cid = (item.get("cid") or "").strip()
            if not cid:
                self.stdout.write(self.style.WARNING("SKIP: missing cid"))
                continue

            if Post.objects.filter(cid=cid).exists():
                skipped += 1
                continue

            p = Post(cid=cid)

            # よく使うキーだけ、モデルに存在するものだけ入れる
            mapping = {
                "title": item.get("title"),
                "description": item.get("description"),
                "affiliate_url": item.get("affiliate_url"),
                "poster_url": item.get("poster_url"),
                "sample_movie_url": item.get("sample_movie_url"),
                "sample_images": item.get("sample_images"),
                "review": item.get("review"),
                "review_html": item.get("review_html"),
                "name": item.get("name"),
                "label": item.get("label"),
                "maker": item.get("maker"),
                "series": item.get("series"),
                "genres": item.get("genres"),
                "performers": item.get("performers"),
                "date": item.get("date"),
                "price": item.get("price"),
                "review_count": item.get("review_count"),
                "review_average": item.get("review_average"),
                "bust": item.get("bust"),
                "waist": item.get("waist"),
                "hip": item.get("hip"),
            }

            for k, v in mapping.items():
                if k in model_fields and v is not None:
                    setattr(p, k, v)

            # 「公開」フラグがモデルにあれば立てる（無ければDB追加=公開扱い）
            if "is_published" in model_fields:
                setattr(p, "is_published", True)
            if "published_at" in model_fields:
                setattr(p, "published_at", timezone.now())
            if "status" in model_fields:
                try:
                    setattr(p, "status", "published")
                except Exception:
                    pass

            p.save()
            created += 1

        self.stdout.write(self.style.SUCCESS(f"done: created={created}, skipped_existing={skipped}"))
