"""Auto-reply guard untuk keyword tertentu."""
from __future__ import annotations

import logging
import re
import time
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Optional, Sequence, Set
from uuid import uuid4

from telethon import events
from telethon.events import NewMessage

from .rules_store import ReplyGuardStore

logger = logging.getLogger("userbot.reply_guard")


class ReplyGuard:
    def __init__(
        self,
        client,
        store: ReplyGuardStore,
        rate_limit_seconds: int = 30,
        log_dir: str | Path | None = None,
    ) -> None:
        self.client = client
        self.store = store
        self.rate_limit_seconds = rate_limit_seconds
        self._event: Optional[NewMessage] = None
        self._active = False
        self._include: list[str] = []
        self._exclude: list[str] = []
        self._regex_patterns: list[str] = []
        self._compiled_regex: list[re.Pattern[str]] = []
        self._raw_targets: Optional[list[int]] = None
        self._targets: Optional[Set[int]] = None
        self._reply_text: str = ""
        self._reply_image: Optional[str] = None
        self._last_reply: dict[int, float] = {}
        self._me_id: Optional[int] = None
        media_dir = self.store.path.parent / "reply_guard_media"
        self._media_dir = media_dir.resolve()
        self._setup_logger(log_dir)

    @property
    def is_active(self) -> bool:
        return self._active

    def activate(
        self,
        *,
        include: Sequence[str],
        exclude: Sequence[str],
        regex: Sequence[str],
        targets: Optional[Sequence[int]],
        reply_text: str,
        reply_image: Optional[str] = None,
        me_id: Optional[int] = None,
    ) -> None:
        self._configure(
            include=include,
            exclude=exclude,
            regex=regex,
            targets=targets,
            reply_text=reply_text,
            reply_image=reply_image,
            me_id=me_id,
            persist=True,
        )

    def deactivate(self) -> None:
        if self._event is not None:
            try:
                self.client.remove_event_handler(self._on_new_message, self._event)
            except Exception:
                logger.debug("Gagal melepas handler reply guard", exc_info=True)
        self._event = None
        self._active = False
        self._last_reply.clear()
        self.store.save(
            {
                "enabled": False,
                "include": self._include,
                "exclude": self._exclude,
                "regex": self._regex_patterns,
                "targets": self._raw_targets,
                "reply_text": self._reply_text,
                "image_path": self._reply_image,
                "rate_limit": self.rate_limit_seconds,
            }
        )
        logger.info("Reply guard dinonaktifkan")

    def restore(self, me_id: int) -> None:
        config = self.store.load()
        self._me_id = me_id
        if not config:
            logger.info("Tidak ada konfigurasi reply guard yang tersimpan")
            return
        if not config.get("enabled"):
            logger.info("Konfigurasi reply guard tersimpan dalam keadaan nonaktif")
            self._load_config_fields(config)
            return
        try:
            include, exclude, regex, targets, reply_text, image_path = self._extract_config(config)
        except ValueError as exc:
            logger.warning("Konfigurasi reply guard tidak valid: %s", exc)
            return
        try:
            self._configure(
                include=include,
                exclude=exclude,
                regex=regex,
                targets=targets,
                reply_text=reply_text,
                reply_image=image_path,
                me_id=me_id,
                persist=False,
            )
        except ValueError as exc:
            if image_path:
                logger.warning(
                    "Gagal memulihkan gambar reply guard (%s). Mengaktifkan tanpa gambar.",
                    exc,
                )
                self._configure(
                    include=include,
                    exclude=exclude,
                    regex=regex,
                    targets=targets,
                    reply_text=reply_text,
                    reply_image=None,
                    me_id=me_id,
                    persist=False,
                )
            else:
                logger.warning("Konfigurasi reply guard gagal dipulihkan: %s", exc)
                return
        logger.info("Reply guard dipulihkan dari konfigurasi sebelumnya")

    def summarize(self) -> str:
        target_desc = (
            "semua grup"
            if self._raw_targets is None
            else f"{len(self._raw_targets)} target"
        )
        state = "aktif" if self._active else "nonaktif"
        if self._reply_image:
            image_path = Path(self._reply_image)
            media_desc = image_path.name if image_path.exists() else f"{image_path.name} (missing)"
        else:
            media_desc = "-"
        return (
            f"Status {state}, balas ke {target_desc}, jeda minimal {self.rate_limit_seconds}s, "
            f"media: {media_desc}."
        )

    async def capture_media(self, message) -> Optional[str]:
        if message is None:
            logger.debug("capture_media: message kosong, skip pengambilan media")
            return None
        media = getattr(message, "media", None)
        if not media:
            logger.debug("capture_media: tidak ada media pada pesan perintah")
            return None

        if not self._is_image_message(message):
            logger.error("Lampiran pada perintah bukan tipe gambar; operasi dibatalkan")
            raise ValueError("Lampiran harus berupa foto atau gambar.")

        self._media_dir.mkdir(parents=True, exist_ok=True)
        timestamp = int(time.time())
        temp_prefix = f"tmp_{timestamp}_{uuid4().hex[:8]}"
        try:
            filename = await message.download_media(file=str(self._media_dir / temp_prefix))
        except Exception as exc:
            logger.exception("Gagal mengunduh lampiran dari pesan", exc_info=True)
            raise ValueError("Gagal menyimpan lampiran gambar.") from exc
        if not filename:
            logger.error("download_media mengembalikan nilai kosong")
            raise ValueError("Gagal menyimpan lampiran gambar.")

        path = Path(filename).resolve()
        if not path.exists() or path.is_dir():
            logger.error("File lampiran tidak ditemukan atau bukan file biasa: %s", path)
            raise ValueError("Gagal menyimpan lampiran gambar.")

        suffix = path.suffix or ".jpg"
        final_target = self._media_dir / f"reply_{timestamp}_{uuid4().hex[:8]}{suffix}"
        try:
            if path != final_target:
                path.rename(final_target)
                path = final_target.resolve()
        except OSError as exc:
            logger.warning("Gagal mengganti nama file media: %s", exc)
            path = path.resolve()

        try:
            path.relative_to(self._media_dir)
        except ValueError:
            logger.warning("File media berada di luar direktori target; mencoba memindahkan")
            try:
                destination = final_target
                if destination.exists() and destination != path:
                    destination.unlink()
                Path(path).replace(destination)
                path = destination.resolve()
            except Exception as exc:
                logger.exception("Gagal memindahkan file media", exc_info=True)
                raise ValueError("Gagal menyimpan lampiran gambar.") from exc

        logger.info("Lampiran reply guard tersimpan di %s", path)
        return str(path)

    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        if not self._active:
            return
        if event.out:
            return
        if not (event.is_group or event.is_channel):
            return
        if event.sender_id is not None and self._me_id is not None and event.sender_id == self._me_id:
            return
        chat_id = event.chat_id
        if chat_id is None:
            return
        if not self._is_target(chat_id):
            return
        text = event.raw_text or ""
        if not text:
            return
        if not self._match_rules(text):
            logger.debug(
                "Pesan tidak cocok dengan rules include=%s exclude=%s regex=%s",
                self._include,
                self._exclude,
                self._regex_patterns,
            )
            return
        now = time.monotonic()
        if not self._allow_send(chat_id, now):
            logger.info("Lewatkan auto-reply di chat %s karena rate limit", chat_id)
            return
        file_arg: Optional[str] = None
        if self._reply_image:
            image_path = Path(self._reply_image)
            if image_path.exists() and image_path.is_file():
                file_arg = str(image_path)
            else:
                logger.error("File gambar untuk auto-reply tidak ditemukan: %s", self._reply_image)
        try:
            await event.reply(self._reply_text, file=file_arg)
        except Exception:
            logger.exception(
                "Gagal mengirim auto-reply ke chat %s (message id=%s)",
                chat_id,
                getattr(event.message, "id", None),
            )
            return
        self._last_reply[chat_id] = now
        logger.info(
            "Auto-reply terkirim ke chat %s msg_id=%s teks='%s'",  # noqa: G004
            chat_id,
            getattr(event.message, "id", None),
            self._reply_text,
        )

    def _allow_send(self, chat_id: int, now: float) -> bool:
        last = self._last_reply.get(chat_id)
        if last is None:
            return True
        if now - last < self.rate_limit_seconds:
            return False
        return True

    def _configure(
        self,
        *,
        include: Sequence[str],
        exclude: Sequence[str],
        regex: Sequence[str],
        targets: Optional[Sequence[int]],
        reply_text: str,
        reply_image: Optional[str],
        me_id: Optional[int],
        persist: bool,
    ) -> None:
        if me_id is not None:
            self._me_id = me_id
        if self._me_id is None:
            raise ValueError("ID akun userbot belum tersedia.")
        reply_text = reply_text.strip()
        if not reply_text:
            raise ValueError("Pesan balasan tidak boleh kosong.")
        self._include = [item for item in include if item]
        self._exclude = [item for item in exclude if item]
        self._regex_patterns = [item for item in regex if item]
        try:
            self._compiled_regex = [re.compile(pattern, re.IGNORECASE) for pattern in self._regex_patterns]
        except re.error as exc:
            raise ValueError(f"Regex tidak valid: {exc}") from exc
        self._raw_targets = self._normalize_raw_targets(targets)
        self._targets = self._build_target_variants(self._raw_targets) if self._raw_targets is not None else None
        self._reply_text = reply_text
        self._set_reply_image(Path(reply_image) if reply_image else None)
        self._last_reply.clear()
        self._ensure_handler()
        self._active = True
        logger.info(
            "Reply guard aktif dengan include=%s exclude=%s regex=%s targets=%s",
            self._include,
            self._exclude,
            self._regex_patterns,
            self._raw_targets if self._raw_targets is not None else "semua grup",
        )
        if persist:
            self.store.save(
                {
                    "enabled": True,
                    "include": self._include,
                    "exclude": self._exclude,
                    "regex": self._regex_patterns,
                    "targets": self._raw_targets,
                    "reply_text": self._reply_text,
                    "image_path": self._reply_image,
                    "rate_limit": self.rate_limit_seconds,
                }
            )

    def _ensure_handler(self) -> None:
        if self._event is None:
            self._event = events.NewMessage(incoming=True)
            self.client.add_event_handler(self._on_new_message, self._event)

    def _match_rules(self, text: str) -> bool:
        lower_text = text.lower()
        if self._include and not all(keyword.lower() in lower_text for keyword in self._include):
            return False
        if self._exclude and any(keyword.lower() in lower_text for keyword in self._exclude):
            return False
        if self._compiled_regex:
            return any(pattern.search(text) for pattern in self._compiled_regex)
        return True

    def _is_target(self, chat_id: int) -> bool:
        if self._targets is None:
            return True
        variants = self._chat_id_variants(chat_id)
        return not self._targets.isdisjoint(variants)

    def _normalize_raw_targets(self, targets: Optional[Sequence[int]]) -> Optional[list[int]]:
        if targets is None:
            return None
        result: list[int] = []
        seen: Set[int] = set()
        for item in targets:
            try:
                value = int(item)
            except (TypeError, ValueError) as exc:
                raise ValueError(f"ID target tidak valid: {item}") from exc
            if value not in seen:
                result.append(value)
                seen.add(value)
        if not result:
            return None
        return result

    def _build_target_variants(self, targets: list[int]) -> Set[int]:
        variants: Set[int] = set()
        for target in targets:
            variants.update(self._chat_id_variants(target))
        return variants

    def _chat_id_variants(self, chat_id: int) -> Set[int]:
        result = {chat_id}
        if chat_id is None:
            return result
        if chat_id > 0:
            result.add(self._to_supergroup_id(chat_id))
        elif chat_id < 0 and str(chat_id).startswith("-100"):
            try:
                positive = int(str(chat_id)[4:])
            except ValueError:
                positive = None
            if positive:
                result.add(positive)
        return result

    @staticmethod
    def _to_supergroup_id(channel_id: int) -> int:
        return -1000000000000 - channel_id

    def _setup_logger(self, log_dir: str | Path | None) -> None:
        if log_dir is None:
            return
        log_path = Path(log_dir)
        log_path.mkdir(parents=True, exist_ok=True)
        file_path = log_path / "userbot_reply_guard.log"
        already = any(
            getattr(handler, "baseFilename", None) == str(file_path)
            for handler in logger.handlers
        )
        if not already:
            handler = RotatingFileHandler(file_path, maxBytes=5 * 1024 * 1024, backupCount=2)
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            logger.addHandler(handler)
        logger.setLevel(logging.INFO)
        logger.propagate = False

    def _extract_config(
        self, config: dict[str, object]
    ) -> tuple[list[str], list[str], list[str], Optional[list[int]], str, Optional[str]]:
        include = [str(item) for item in config.get("include", []) if isinstance(item, str)]
        exclude = [str(item) for item in config.get("exclude", []) if isinstance(item, str)]
        regex = [str(item) for item in config.get("regex", []) if isinstance(item, str)]
        raw_targets = config.get("targets")
        targets: Optional[list[int]]
        if raw_targets is None:
            targets = None
        elif isinstance(raw_targets, list):
            targets = []
            for item in raw_targets:
                try:
                    targets.append(int(item))
                except (TypeError, ValueError):
                    continue
        else:
            raise ValueError("Struktur target tidak valid")
        reply_text = str(config.get("reply_text", "")).strip()
        if not reply_text:
            raise ValueError("Pesan balasan pada konfigurasi kosong")
        image_path = config.get("image_path")
        if image_path is not None and not isinstance(image_path, str):
            image_path = None
        return include, exclude, regex, targets, reply_text, image_path or None

    def _load_config_fields(self, config: dict[str, object]) -> None:
        try:
            include, exclude, regex, targets, reply_text, image_path = self._extract_config(config)
        except ValueError:
            return
        self._include = include
        self._exclude = exclude
        self._regex_patterns = regex
        try:
            self._compiled_regex = [re.compile(pattern, re.IGNORECASE) for pattern in regex]
        except re.error:
            self._compiled_regex = []
        self._raw_targets = targets
        self._targets = self._build_target_variants(targets) if targets else None
        self._reply_text = reply_text
        if image_path:
            path = Path(image_path)
            if path.exists() and path.is_file():
                self._reply_image = str(path.resolve())
            else:
                logger.warning("File gambar reply guard hilang: %s", image_path)
                self._reply_image = None
        else:
            self._reply_image = None

    def _set_reply_image(self, candidate: Optional[Path]) -> None:
        if candidate is None:
            self._cleanup_media_path(self._reply_image)
            self._reply_image = None
            return
        if not candidate.exists() or not candidate.is_file():
            raise ValueError(f"File gambar tidak ditemukan: {candidate}")
        resolved = candidate.resolve()
        if self._reply_image and Path(self._reply_image) != resolved:
            self._cleanup_media_path(self._reply_image)
        self._reply_image = str(resolved)

    def _cleanup_media_path(self, path: Optional[str]) -> None:
        if not path:
            return
        candidate = Path(path)
        try:
            candidate.relative_to(self._media_dir)
        except ValueError:
            return
        if candidate.exists():
            try:
                candidate.unlink()
            except OSError:
                logger.debug("Gagal menghapus file media lama %s", candidate, exc_info=True)

    @staticmethod
    def _is_image_message(message) -> bool:
        photo = getattr(message, "photo", None)
        if photo is not None:
            return True
        document = getattr(message, "document", None)
        if document is None:
            return False
        mime = getattr(document, "mime_type", "") or ""
        return mime.startswith("image/")
