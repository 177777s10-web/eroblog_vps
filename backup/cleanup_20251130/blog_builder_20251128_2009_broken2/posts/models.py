from django.db import models
from django.utils import timezone

class Post(models.Model):
    """
    ブログ記事のデータベース設計図
    """
    
    # ------------------------------------------
    # 1. API/JSONL から取得する主要データ
    # ------------------------------------------
    
    # 品番 (例: 'bshi021')
    cid = models.CharField(max_length=20, unique=True, db_index=True, help_text="作品CID (ユニークID)")
    
    # タイトル (例: 'セリ')
    title = models.CharField(max_length=255, help_text="作品タイトル")
    
    # 出演者名 (例: 'セリ')
    name = models.CharField(max_length=100, blank=True, help_text="出演者名 (probe由来)")
    
    # メーカー (例: 'ブロッコリー')
    maker = models.CharField(max_length=100, blank=True, db_index=True, help_text="メーカー名")
    
    # レーベル (例: 'ブロッコリー')
    label = models.CharField(max_length=100, blank=True, help_text="レーベル名")
    
    # サイズ (例: 'B-- W-- H--')
    sizes = models.CharField(max_length=50, blank=True, help_text="サイズ (T/B/W/H)")
    
    # ジャンル (JSON配列をそのままテキストで保存)
    genres = models.JSONField(default=list, blank=True, help_text="ジャンルのリスト")
    
    # レビュー本文 (Markdown)
    review_body = models.TextField(blank=True, help_text="紹介文（レビュー本文）")
    
    # ------------------------------------------
    # 2. URL関連
    # ------------------------------------------
    
    # アフィリエイトURL
    affiliate_url = models.URLField(max_length=1024, blank=True)
    
    # サンプル動画URL
    sample_movie_url = models.URLField(max_length=1024, blank=True)
    
    # ------------------------------------------
    # 3. ファイルパス（content/ 以下のどこにあるか）
    # ------------------------------------------
    
    # 元のMarkdown原稿へのパス (例: 'content/drafts/20251111_bshi021_セリ.md')
    draft_path = models.CharField(max_length=512, blank=True, help_text="元のMD原稿ファイルのパス")
    
    # 本物のポスター画像のパス (例: 'content/assets/bshi021_poster.jpg')
    poster_image_file = models.CharField(max_length=512, blank=True, help_text="ポスター画像(poster.jpg)のパス")
    
    # サンプル画像のパス (JSON配列で保存) (例: ['content/assets/bshi021_01.jpg', ...])
    sample_image_files = models.JSONField(default=list, blank=True, help_text="サンプル画像(01.jpg...)のパスリスト")
    
    # ------------------------------------------
    # 4. 管理用の日付
    # ------------------------------------------
    
    # 記事の公開日（APIの日付）
    release_date = models.DateTimeField(null=True, blank=True, help_text="作品の配信開始日")
    
    # このDBに登録された日
    created_at = models.DateTimeField(auto_now_add=True, help_text="DB登録日")
    
    # 最終更新日
    updated_at = models.DateTimeField(auto_now=True, help_text="DB最終更新日")


    # --- 取得データ由来の追加フィールド ---
    # 出演者名（例: "YUNA(21)"）
    name  = models.CharField(max_length=200, blank=True, default="")
    # スリーサイズ
    bust  = models.IntegerField(null=True, blank=True)
    waist = models.IntegerField(null=True, blank=True)
    hip   = models.IntegerField(null=True, blank=True)
    # レビュー本文
    review = models.TextField(blank=True, default="")
    def __str__(self):
        return f"[{self.cid}] {self.title}"

    class Meta:
        ordering = ['-release_date'] # 新しい順に並べる
        verbose_name = "記事"
        verbose_name_plural = "記事"

