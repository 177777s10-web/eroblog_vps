import json
from pathlib import Path

from django.core.management.base import BaseCommand
from posts.models import Post


class Command(BaseCommand):
    help = "data_getter/out/history.jsonl から Post.sizes を埋める（空のものだけ）"

    def handle(self, *args, **options):
        # manage.py を実行するディレクトリが blog_builder/ 前提
        src = Path("..") / "data_getter" / "out" / "history.jsonl"
        if not src.exists():
            self.stderr.write(self.style.ERROR(f"{src} が見つかりません"))
            return

        updated = 0
        total = 0

        with src.open(encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                total += 1
                data = json.loads(line)
                cid = data.get("cid")
                sizes = data.get("sizes") or data.get("sizes_text")
                if not cid or not sizes:
                    continue

                try:
                    post = Post.objects.get(cid=cid)
                except Post.DoesNotExist:
                    continue

                # すでに sizes が入っているものは上書きしない
                if post.sizes:
                    continue

                post.sizes = sizes
                post.save(update_fields=["sizes"])
                updated += 1

        self.stdout.write(
            self.style.SUCCESS(f"history.jsonl を {total} 件走査、sizes を埋めた件数: {updated}")
        )
