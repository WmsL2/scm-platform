LOCAL_MEDIA_PREFIX = "local-media/"


def local_media_storage_key(image_reference: str | None) -> str | None:
    if image_reference and image_reference.startswith(LOCAL_MEDIA_PREFIX):
        return image_reference.removeprefix(LOCAL_MEDIA_PREFIX)
    return None
