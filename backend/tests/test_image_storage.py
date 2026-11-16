import io
import os
import re
from types import SimpleNamespace

import pytest
from PIL import Image


def encoded(fmt="PNG", size=(12, 8), **kwargs):
    output = io.BytesIO()
    Image.new("RGB", size, "red").save(output, fmt, **kwargs)
    return output.getvalue()


def test_storage_module_exists():
    import importlib.util
    assert importlib.util.find_spec("app.storage") is not None


@pytest.mark.parametrize("fmt", ["JPEG", "PNG", "WEBP"])
def test_normalization_decodes_content_and_strips_metadata(fmt):
    from app.storage.product_images import normalize_image
    exif = Image.Exif()
    exif[270] = "private metadata"
    result = normalize_image(encoded(fmt, exif=exif))
    with Image.open(io.BytesIO(result)) as image:
        assert image.format == "WEBP"
        assert image.size == (12, 8)
        assert not image.getexif()
        assert "icc_profile" not in image.info
        image.load()


def test_orientation_is_applied():
    from app.storage.product_images import normalize_image
    exif = Image.Exif()
    exif[274] = 6
    with Image.open(io.BytesIO(normalize_image(encoded("JPEG", exif=exif)))) as image:
        assert image.size == (8, 12)


@pytest.mark.parametrize("data", [b"", b"malformed", b"<svg></svg>", b"GIF89a", b"x" * (5 * 1024 * 1024 + 1)], ids=["empty", "malformed", "svg", "gif", "oversized"])
def test_invalid_content_is_rejected(data):
    from app.storage.product_images import ImageValidationError, normalize_image
    with pytest.raises(ImageValidationError):
        normalize_image(data)


def test_exact_raw_size_boundary():
    from app.storage.product_images import MAX_IMAGE_BYTES, normalize_image
    raw = encoded()
    assert normalize_image(raw + b"\0" * (MAX_IMAGE_BYTES - len(raw)))


@pytest.mark.parametrize("fmt", ["GIF", "PNG", "WEBP"])
def test_animated_images_are_rejected(fmt):
    from app.storage.product_images import ImageValidationError, normalize_image
    output = io.BytesIO()
    Image.new("RGB", (8, 8), "red").save(output, fmt, save_all=True,
        append_images=[Image.new("RGB", (8, 8), "blue")], duration=100, loop=0)
    with pytest.raises(ImageValidationError):
        normalize_image(output.getvalue())


@pytest.mark.parametrize("size", [(8001, 1), (4001, 4000)])
def test_dimension_limits(size):
    from app.storage.product_images import ImageValidationError, normalize_image
    with pytest.raises(ImageValidationError):
        normalize_image(encoded(size=size))


def test_decompression_bomb_warning_rejected(monkeypatch):
    from app.storage.product_images import ImageValidationError, normalize_image
    raw = encoded(size=(12, 8))
    monkeypatch.setattr(Image, "MAX_IMAGE_PIXELS", 50)
    with pytest.raises(ImageValidationError):
        normalize_image(raw)


@pytest.mark.parametrize("fmt", ["JPEG", "PNG", "WEBP"])
def test_truncated_content_rejected(fmt):
    from app.storage.product_images import ImageValidationError, normalize_image
    with pytest.raises(ImageValidationError):
        normalize_image(encoded(fmt)[:40])


def test_keys_and_references_are_strict():
    from app.storage.product_images import new_image_key, managed_reference, image_key
    key = new_image_key()
    assert re.fullmatch(r"[a-f0-9]{32}\.webp", key)
    assert image_key(managed_reference(key)) == key
    for bad in ["../a.webp", key, "whatnot-upload:" + key + "/x", "whatnot-upload:" + key.upper(), None]:
        assert image_key(bad) is None


def test_local_roundtrip_and_immutable_private_files(tmp_path):
    from app.storage.product_images import LocalImageStorage, ImageStorageError, new_image_key
    directory = tmp_path / "private"
    storage = LocalImageStorage(directory)
    key = new_image_key()
    storage.put(key, b"image")
    assert storage.get(key) == b"image"
    with pytest.raises(ImageStorageError):
        storage.put(key, b"overwrite")
    if os.name != "nt":
        assert directory.stat().st_mode & 0o777 == 0o700
        assert (directory / key).stat().st_mode & 0o777 == 0o600
    storage.delete(key)
    storage.delete(key)
    with pytest.raises(FileNotFoundError):
        storage.get(key)
    for action in [storage.get, storage.delete]:
        with pytest.raises(ValueError):
            action("../escape")
    with pytest.raises(ValueError):
        storage.put("../escape", b"bad")


def test_local_rejects_symlink_files_and_directory(tmp_path):
    from app.storage.product_images import LocalImageStorage, ImageStorageError, new_image_key
    outside = tmp_path / "outside"
    outside.mkdir()
    link = tmp_path / "link"
    try:
        link.symlink_to(outside, target_is_directory=True)
    except OSError:
        pytest.skip("symlink privilege unavailable")
    with pytest.raises(ImageStorageError):
        LocalImageStorage(link)
    storage = LocalImageStorage(tmp_path / "private")
    key = new_image_key()
    target = outside / "secret"
    target.write_bytes(b"secret")
    (storage.directory / key).symlink_to(target)
    with pytest.raises(ImageStorageError):
        storage.get(key)
    with pytest.raises(ImageStorageError):
        storage.delete(key)
    assert target.read_bytes() == b"secret"


def test_local_provider_failures_are_generic(tmp_path, monkeypatch):
    from app.storage import product_images
    storage = product_images.LocalImageStorage(tmp_path / "private")
    def fail(path):
        raise PermissionError("private filesystem details")
    monkeypatch.setattr(product_images, "_safe_directory", fail)
    with pytest.raises(product_images.ImageStorageError, match="^Image storage operation failed\\.$"):
        storage.get(product_images.new_image_key())


class FakeS3:
    def __init__(self):
        self.calls = []
    def put_object(self, **kwargs):
        self.calls.append(kwargs)
    def get_object(self, **kwargs):
        self.calls.append(kwargs)
        return {"Body": io.BytesIO(b"normalized")}
    def delete_object(self, **kwargs):
        self.calls.append(kwargs)


def test_s3_private_encrypted_immutable_calls():
    from app.storage.product_images import S3ImageStorage, new_image_key
    client = FakeS3()
    storage = S3ImageStorage("bucket", client=client)
    key = new_image_key()
    storage.put(key, b"normalized")
    assert client.calls[0] == dict(Bucket="bucket", Key="product-images/" + key,
        Body=b"normalized", ContentType="image/webp", ServerSideEncryption="AES256", IfNoneMatch="*")
    assert storage.get(key) == b"normalized"
    storage.delete(key)


def test_s3_provider_errors_are_generic():
    from app.storage.product_images import S3ImageStorage, ImageStorageError, new_image_key
    class Broken(FakeS3):
        def get_object(self, **kwargs):
            raise RuntimeError("credential secret")
    with pytest.raises(ImageStorageError, match="^Image storage operation failed\\.$") as caught:
        S3ImageStorage("bucket", client=Broken()).get(new_image_key())
    assert "secret" not in str(caught.value)


def test_s3_absent_object():
    from botocore.exceptions import ClientError
    from app.storage.product_images import S3ImageStorage, new_image_key
    class Missing(FakeS3):
        def get_object(self, **kwargs):
            raise ClientError({"Error": {"Code": "NoSuchKey"}}, "GetObject")
    with pytest.raises(FileNotFoundError):
        S3ImageStorage("bucket", client=Missing()).get(new_image_key())


def test_s3_client_uses_default_credentials_and_bounded_retries(monkeypatch):
    import boto3
    from app.storage.product_images import S3ImageStorage
    calls = []
    def client(service, **kwargs):
        calls.append((service, kwargs))
        return FakeS3()
    monkeypatch.setattr(boto3, "client", client)
    S3ImageStorage("bucket", "region")
    service, options = calls[0]
    assert service == "s3"
    assert set(options) == {"region_name", "config"}
    assert options["region_name"] == "region"
    assert options["config"].connect_timeout == 3
    assert options["config"].read_timeout == 10
    assert options["config"].retries["total_max_attempts"] == 3


def test_s3_sdk_supports_conditional_immutable_write():
    from botocore.session import Session
    model = Session().get_service_model("s3").operation_model("PutObject")
    assert "IfNoneMatch" in model.input_shape.members


def test_factory_uses_settings(tmp_path):
    from app.storage.product_images import LocalImageStorage, get_image_storage
    assert isinstance(get_image_storage(SimpleNamespace(image_storage="local", image_local_directory=tmp_path)), LocalImageStorage)


def test_factory_rejects_production_local_storage(tmp_path):
    from app.storage.product_images import ImageStorageError, get_image_storage
    with pytest.raises(ImageStorageError):
        get_image_storage(SimpleNamespace(environment="production", image_storage="local", image_local_directory=tmp_path))
