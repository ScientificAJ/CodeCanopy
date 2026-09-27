import stat
import zipfile
import zlib
from dataclasses import dataclass
from pathlib import Path, PureWindowsPath

from fastapi import UploadFile

MAX_UPLOAD_BYTES = 1024 * 1024 * 1024
MAX_ARCHIVE_ENTRIES = 200_000
MAX_PROJECT_FILES = 50_000
MAX_FILE_BYTES = 25 * 1024 * 1024
MAX_TOTAL_UNCOMPRESSED_BYTES = 250 * 1024 * 1024
CHUNK_SIZE = 64 * 1024
IGNORED_DIRECTORIES = {".git", "node_modules", "__pycache__", ".venv", "venv", "dist", "build", ".next", ".nuxt", ".pytest_cache", "coverage"}
WINDOWS_RESERVED_NAMES = {
    "CON", "PRN", "AUX", "NUL",
    *(f"COM{index}" for index in range(1, 10)),
    *(f"LPT{index}" for index in range(1, 10)),
}
WINDOWS_INVALID_CHARACTERS = '<>:"|?*'


class ProjectUploadError(ValueError):
    pass


class ProjectUploadTooLargeError(ProjectUploadError):
    pass


@dataclass(frozen=True)
class ArchiveEntry:
    info: zipfile.ZipInfo
    relative_path: Path
    path_parts: tuple[str, ...]
    is_directory: bool


def _member_path(info: zipfile.ZipInfo, allow_symlink: bool = False) -> tuple[Path, tuple[str, ...], bool]:
    name = info.filename
    if not name or "\x00" in name or any(ord(character) < 32 for character in name):
        raise ProjectUploadError("The archive contains an invalid path.")

    normalized_name = name.replace("\\", "/")
    has_trailing_separator = normalized_name.endswith("/")
    if has_trailing_separator:
        normalized_name = normalized_name[:-1]

    windows_path = PureWindowsPath(normalized_name)
    if (
        normalized_name.startswith("/")
        or windows_path.is_absolute()
        or windows_path.drive
        or not normalized_name
    ):
        raise ProjectUploadError("The archive contains an absolute path.")

    parts = tuple(normalized_name.split("/"))
    if any(part in ("", ".", "..") for part in parts):
        raise ProjectUploadError("The archive contains a path traversal entry.")
    for part in parts:
        if any(character in WINDOWS_INVALID_CHARACTERS for character in part) or part.endswith((" ", ".")):
            raise ProjectUploadError("The archive contains an unsafe path component.")
        if part.split(".", maxsplit=1)[0].upper() in WINDOWS_RESERVED_NAMES:
            raise ProjectUploadError("The archive contains a reserved path component.")

    unix_mode = info.external_attr >> 16
    file_type = stat.S_IFMT(unix_mode)
    if (stat.S_ISLNK(unix_mode) or info.external_attr & 0xFFFF & 0x400) and not allow_symlink:
        raise ProjectUploadError("Symbolic links are not allowed in project archives.")
    if file_type not in (0, stat.S_IFREG, stat.S_IFDIR) and not (allow_symlink and file_type == stat.S_IFLNK):
        raise ProjectUploadError("The archive contains a non-regular file.")

    is_directory = has_trailing_separator or info.is_dir() or file_type == stat.S_IFDIR
    if file_type == stat.S_IFREG and is_directory:
        raise ProjectUploadError("The archive contains a conflicting file type.")

    return Path(*parts), parts, is_directory


def _validated_entries(archive: zipfile.ZipFile, check_cancel=lambda: None, *, skip_symlinks=False, on_skip=lambda path: None) -> list[ArchiveEntry]:
    infos = archive.infolist()
    if not infos:
        raise ProjectUploadError("The ZIP archive is empty.")
    if len(infos) > MAX_ARCHIVE_ENTRIES:
        raise ProjectUploadError(f"The archive may contain at most {MAX_ARCHIVE_ENTRIES} entries.")

    entries: list[ArchiveEntry] = []
    path_types: dict[str, bool] = {}
    declared_uncompressed_bytes = 0
    file_count = 0

    for index, info in enumerate(infos):
        if index % 256 == 0:
            check_cancel()
        relative_path, parts, is_directory = _member_path(info, allow_symlink=skip_symlinks)
        if skip_symlinks and (stat.S_ISLNK(info.external_attr >> 16) or info.external_attr & 0xFFFF & 0x400):
            on_skip(relative_path.as_posix())
            continue
        if info.flag_bits & 0x1:
            raise ProjectUploadError("Encrypted ZIP entries are not supported.")
        if info.compress_type not in (zipfile.ZIP_STORED, zipfile.ZIP_DEFLATED):
            raise ProjectUploadError("The archive uses an unsupported compression method.")
        directory_parts = parts if is_directory else parts[:-1]
        if any(part.casefold() in IGNORED_DIRECTORIES for part in directory_parts):
            continue

        path_key = "/".join(parts).casefold()
        previous_type = path_types.get(path_key)
        if previous_type is not None:
            if previous_type and is_directory:
                continue
            raise ProjectUploadError("The archive contains duplicate or conflicting paths.")
        path_types[path_key] = is_directory

        if not is_directory:
            file_count += 1
            if file_count > MAX_PROJECT_FILES:
                raise ProjectUploadError(f"The project may contain at most {MAX_PROJECT_FILES:,} files after dependency and build folders are excluded. Import a smaller package.")
            if info.file_size > MAX_FILE_BYTES:
                raise ProjectUploadError(f"A file exceeds the {MAX_FILE_BYTES // (1024 * 1024)} MiB limit.")
            declared_uncompressed_bytes += info.file_size
            if declared_uncompressed_bytes > MAX_TOTAL_UNCOMPRESSED_BYTES:
                raise ProjectUploadError("The extracted project exceeds the total size limit.")

        entries.append(ArchiveEntry(info, relative_path, parts, is_directory))

    for entry in entries:
        folded_parts = tuple(part.casefold() for part in entry.path_parts)
        for index in range(1, len(folded_parts)):
            parent_key = "/".join(folded_parts[:index])
            if path_types.get(parent_key) is False:
                raise ProjectUploadError("A file path conflicts with a directory path in the archive.")

    if not any(not entry.is_directory for entry in entries):
        raise ProjectUploadError("The archive contains no uploadable files.")
    return entries


async def _save_upload(upload: UploadFile, archive_path: Path) -> None:
    if upload.size is not None and upload.size > MAX_UPLOAD_BYTES:
        raise ProjectUploadTooLargeError("The ZIP upload exceeds the 1 GiB limit.")

    size = 0
    with archive_path.open("xb") as destination:
        while chunk := await upload.read(CHUNK_SIZE):
            size += len(chunk)
            if size > MAX_UPLOAD_BYTES:
                raise ProjectUploadTooLargeError("The ZIP upload exceeds the 1 GiB limit.")
            destination.write(chunk)


def _extract_entries(
    archive: zipfile.ZipFile,
    entries: list[ArchiveEntry],
    extraction_root: Path,
    check_cancel=lambda: None,
) -> int:
    extraction_root.mkdir()
    resolved_root = extraction_root.resolve()
    extracted_bytes = 0
    file_count = 0

    for entry in entries:
        check_cancel()
        destination = (extraction_root / entry.relative_path).resolve()
        try:
            destination.relative_to(resolved_root)
        except ValueError as error:
            raise ProjectUploadError("The archive contains a path outside the project directory.") from error

        if entry.is_directory:
            destination.mkdir(parents=True, exist_ok=True)
            continue

        destination.parent.mkdir(parents=True, exist_ok=True)
        file_bytes = 0
        with archive.open(entry.info, "r") as source, destination.open("xb") as output:
            while chunk := source.read(CHUNK_SIZE):
                check_cancel()
                file_bytes += len(chunk)
                extracted_bytes += len(chunk)
                if file_bytes > MAX_FILE_BYTES or extracted_bytes > MAX_TOTAL_UNCOMPRESSED_BYTES:
                    raise ProjectUploadError("The extracted project exceeds the size limit.")
                if file_bytes > entry.info.file_size:
                    raise ProjectUploadError("An archive entry expands beyond its declared size.")
                output.write(chunk)

        if file_bytes != entry.info.file_size:
            raise ProjectUploadError("An archive entry does not match its declared size.")
        file_count += 1

    return file_count


async def extract_project_archive(
    upload: UploadFile,
    archive_path: Path,
    extraction_root: Path,
) -> int:
    await _save_upload(upload, archive_path)
    try:
        with zipfile.ZipFile(archive_path, "r") as archive:
            entries = _validated_entries(archive)
            return _extract_entries(archive, entries, extraction_root)
    except (
        zipfile.BadZipFile,
        zipfile.LargeZipFile,
        RuntimeError,
        NotImplementedError,
        EOFError,
        zlib.error,
    ) as error:
        raise ProjectUploadError("The uploaded file is not a valid supported ZIP archive.") from error