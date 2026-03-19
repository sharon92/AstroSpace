import os
from dataclasses import dataclass
from uuid import uuid4

from werkzeug.utils import secure_filename


@dataclass(frozen=True)
class StoredUpload:
    absolute_path: str
    public_path: str
    filename: str


def allowed_file(filename, allowed_extensions):
    return "." in filename and filename.rsplit(".", 1)[1].lower() in allowed_extensions


def ensure_directory(path):
    os.makedirs(path, exist_ok=True)
    return path


def save_user_upload(file_storage, upload_root, user_id, *, prefix_uuid=True):
    user_dir = ensure_directory(os.path.join(upload_root, str(user_id)))
    base_name = secure_filename(file_storage.filename)
    filename = f"{uuid4().hex}_{base_name}" if prefix_uuid else base_name
    absolute_path = os.path.join(user_dir, filename)
    file_storage.save(absolute_path)
    return StoredUpload(
        absolute_path=absolute_path,
        public_path=f"{user_id}/{filename}",
        filename=filename,
    )
