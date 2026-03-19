from AstroSpace.services.uploads import allowed_file, save_user_upload


class DummyStorage:
    def __init__(self, filename, content=b"hello"):
        self.filename = filename
        self._content = content

    def save(self, target):
        with open(target, "wb") as handle:
            handle.write(self._content)


def test_allowed_file_checks_extension():
    assert allowed_file("image.jpg", {"jpg", "png"})
    assert not allowed_file("image.exe", {"jpg", "png"})


def test_save_user_upload_stores_file(tmp_path):
    storage = DummyStorage("capture.jpg", b"data")
    stored = save_user_upload(storage, str(tmp_path), 42, prefix_uuid=False)

    assert stored.public_path == "42/capture.jpg"
    assert (tmp_path / "42" / "capture.jpg").read_bytes() == b"data"
