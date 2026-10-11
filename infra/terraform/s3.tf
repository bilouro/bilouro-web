resource "aws_s3_bucket" "media" {
  bucket = "${local.name_prefix}-media-${var.aws_region}"
}

resource "aws_s3_bucket_versioning" "media" {
  bucket = aws_s3_bucket.media.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_public_access_block" "media" {
  bucket                  = aws_s3_bucket.media.id
  block_public_acls       = true
  block_public_policy     = false # bucket policy grants public read on images/* only
  ignore_public_acls      = true
  restrict_public_buckets = false
}

resource "aws_s3_bucket_server_side_encryption_configuration" "media" {
  bucket = aws_s3_bucket.media.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# Public read for Wagtail image RENDITIONS only (images/*), so the site can use
# plain, non-expiring URLs (SEO, social previews, caching). Originals
# (original_images/*), avatars and anything else stay private and signed.
resource "aws_s3_bucket_policy" "media_public_renditions" {
  bucket = aws_s3_bucket.media.id
  policy = jsonencode({
    Version = "2012-10-17"
    Statement = [{
      Sid       = "PublicReadImageRenditions"
      Effect    = "Allow"
      Principal = "*"
      Action    = "s3:GetObject"
      Resource  = "${aws_s3_bucket.media.arn}/images/*"
    }]
  })
  depends_on = [aws_s3_bucket_public_access_block.media]
}
