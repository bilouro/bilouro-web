"""S3 media storage: plain URLs for Wagtail image renditions, signed URLs for
everything else.

Renditions live under images/ and the bucket policy grants public read on
images/* only (infra/terraform/s3.tf). Unsigned URLs never expire, so search
engines, social previews and browser caches keep working. Originals
(original_images/), avatars and documents stay private and signed.
"""
from django.utils.encoding import filepath_to_uri
from storages.backends.s3 import S3Storage

PUBLIC_PREFIXES = ("images/",)


class MediaStorage(S3Storage):
    def url(self, name, parameters=None, expire=None, http_method=None):
        if name and name.startswith(PUBLIC_PREFIXES):
            region = self.region_name or "eu-west-1"
            return f"https://{self.bucket_name}.s3.{region}.amazonaws.com/{filepath_to_uri(name)}"
        return super().url(name, parameters=parameters, expire=expire, http_method=http_method)
