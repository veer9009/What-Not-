"""Bounded image decoding and private, immutable image storage."""

import io
import os
from pathlib import Path
import re
import stat
from uuid import uuid4
import warnings

from PIL import Image, ImageOps


MAX_IMAGE_BYTES = 5 * 1024 * 1024
MAX_IMAGE_SIDE = 8000
MAX_IMAGE_PIXELS = 16_000_000
_KEY = re.compile(r"[a-f0-9]{32}\.webp", re.ASCII)
_REFERENCE_PREFIX = "whatnot-upload:"


class ImageValidationError(ValueError):
    """The supplied content is not an acceptable product image."""


class ImageStorageError(Exception):
    """A private storage operation could not be completed."""


def normalize_image(raw: bytes) -> bytes:
    if not isinstance(raw, bytes) or not raw or len(raw) > MAX_IMAGE_BYTES:
        raise ImageValidationError("Image must contain between 1 byte and 5 MiB.")
    try:
        with warnings.catch_warnings():
            warnings.simplefilter("error", Image.DecompressionBombWarning)
            with Image.open(io.BytesIO(raw)) as source:
                if source.format not in {"JPEG", "PNG", "WEBP"}:
                    raise ImageValidationError("Only JPEG, PNG and WebP images are accepted.")
                width, height = source.size
                if not (0 < width <= MAX_IMAGE_SIDE and 0 < height <= MAX_IMAGE_SIDE
                        and width * height <= MAX_IMAGE_PIXELS):
                    raise ImageValidationError("Image dimensions exceed the allowed limits.")
                if getattr(source, "is_animated", False) or getattr(source, "n_frames", 1) != 1:
                    raise ImageValidationError("Animated images are not accepted.")
                source.verify()
            with Image.open(io.BytesIO(raw)) as source:
                source.load()
                oriented = ImageOps.exif_transpose(source)
                mode = "RGBA" if "A" in oriented.getbands() or "transparency" in oriented.info else "RGB"
                converted = oriented.convert(mode)
                # A new pixel-only image prevents EXIF, XMP and ICC metadata inheritance.
                clean = Image.new(mode, converted.size)
                clean.paste(converted)
                output = io.BytesIO()
                clean.save(output, "WEBP", quality=85, method=4)
                result = output.getvalue()
                if not result or len(result) > MAX_IMAGE_BYTES:
                    raise ImageValidationError("Normalized image exceeds 5 MiB.")
                return result
    except ImageValidationError:
        raise
    except Exception:
        raise ImageValidationError("Image content is invalid or cannot be safely decoded.") from None


def _validate_key(key: str) -> str:
    if not isinstance(key, str) or _KEY.fullmatch(key) is None:
        raise ValueError("Invalid image key.")
    return key


def new_image_key() -> str:
    return uuid4().hex + ".webp"


def managed_reference(key: str) -> str:
    return _REFERENCE_PREFIX + _validate_key(key)


def image_key(reference: str) -> str | None:
    if not isinstance(reference, str) or not reference.startswith(_REFERENCE_PREFIX):
        return None
    key = reference[len(_REFERENCE_PREFIX):]
    return key if _KEY.fullmatch(key) is not None else None


def _is_link(path: Path) -> bool:
    info = path.lstat()
    return stat.S_ISLNK(info.st_mode) or bool(getattr(info, "st_file_attributes", 0) & 0x400)


def _safe_directory(path: Path) -> None:
    for component in [*reversed(path.parents), path]:
        if component.exists() or component.is_symlink():
            if _is_link(component) or not component.is_dir():
                raise ImageStorageError("Image storage operation failed.")


class LocalImageStorage:
    def __init__(self, directory: Path):
        try:
            self.directory = Path(os.path.abspath(directory))
            _safe_directory(self.directory)
            self.directory.mkdir(parents=True, exist_ok=True, mode=0o700)
            _safe_directory(self.directory)
            self.directory.chmod(0o700)
        except ImageStorageError:
            raise
        except Exception:
            raise ImageStorageError("Image storage operation failed.") from None

    def _path(self, key: str) -> Path:
        _validate_key(key)
        try:
            _safe_directory(self.directory)
            path = self.directory / key
            if (path.exists() or path.is_symlink()) and _is_link(path):
                raise ImageStorageError("Image storage operation failed.")
            return path
        except Exception:
            raise ImageStorageError("Image storage operation failed.") from None

    def put(self, key: str, data: bytes) -> None:
        path = self._path(key)
        try:
            flags = os.O_WRONLY | os.O_CREAT | os.O_EXCL | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            descriptor = os.open(path, flags, 0o600)
            try:
                with os.fdopen(descriptor, "wb") as stream:
                    stream.write(data)
            except Exception:
                path.unlink(missing_ok=True)
                raise
        except Exception:
            raise ImageStorageError("Image storage operation failed.") from None

    def get(self, key: str) -> bytes:
        path = self._path(key)
        try:
            flags = os.O_RDONLY | getattr(os, "O_BINARY", 0) | getattr(os, "O_NOFOLLOW", 0)
            with os.fdopen(os.open(path, flags), "rb") as stream:
                if not stat.S_ISREG(os.fstat(stream.fileno()).st_mode):
                    raise ImageStorageError("Image storage operation failed.")
                data = stream.read(MAX_IMAGE_BYTES + 1)
                if len(data) > MAX_IMAGE_BYTES:
                    raise ImageStorageError("Image storage operation failed.")
                return data
        except FileNotFoundError:
            raise FileNotFoundError("Image not found.") from None
        except Exception:
            raise ImageStorageError("Image storage operation failed.") from None

    def delete(self, key: str) -> None:
        path = self._path(key)
        try:
            path.unlink(missing_ok=True)
        except Exception:
            raise ImageStorageError("Image storage operation failed.") from None


class S3ImageStorage:
    def __init__(self, bucket: str, region: str | None = None, *, client=None):
        if not bucket:
            raise ImageStorageError("Image storage operation failed.")
        self.bucket = bucket
        try:
            if client is None:
                import boto3
                from botocore.config import Config
                client = boto3.client("s3", region_name=region, config=Config(
                    connect_timeout=3, read_timeout=10,
                    retries={"mode": "standard", "total_max_attempts": 3}))
            self.client = client
        except Exception:
            raise ImageStorageError("Image storage operation failed.") from None

    def put(self, key: str, data: bytes) -> None:
        key = "product-images/" + _validate_key(key)
        try:
            self.client.put_object(Bucket=self.bucket, Key=key, Body=data,
                ContentType="image/webp", ServerSideEncryption="AES256", IfNoneMatch="*")
        except Exception:
            raise ImageStorageError("Image storage operation failed.") from None

    def get(self, key: str) -> bytes:
        key = "product-images/" + _validate_key(key)
        try:
            body = self.client.get_object(Bucket=self.bucket, Key=key)["Body"]
            try:
                data = body.read(MAX_IMAGE_BYTES + 1)
                if len(data) > MAX_IMAGE_BYTES:
                    raise ImageStorageError("Image storage operation failed.")
                return data
            finally:
                body.close()
        except Exception as error:
            code = getattr(error, "response", {}).get("Error", {}).get("Code")
            if code in {"NoSuchKey", "NotFound", "404"}:
                raise FileNotFoundError("Image not found.") from None
            raise ImageStorageError("Image storage operation failed.") from None

    def delete(self, key: str) -> None:
        key = "product-images/" + _validate_key(key)
        try:
            self.client.delete_object(Bucket=self.bucket, Key=key)
        except Exception:
            raise ImageStorageError("Image storage operation failed.") from None


def get_image_storage(settings):
    if settings.image_storage == "local":
        if getattr(settings, "environment", None) == "production":
            raise ImageStorageError("Image storage operation failed.")
        return LocalImageStorage(settings.image_local_directory)
    if settings.image_storage == "s3":
        return S3ImageStorage(settings.image_s3_bucket, settings.image_s3_region)
    raise ImageStorageError("Image storage operation failed.")
