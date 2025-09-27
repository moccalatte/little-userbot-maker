"""Auto-reply guard untuk keyword tertentu."""
from __future__ import annotations

import logging
import re
import time
from dataclasses import dataclass, field
from logging.handlers import RotatingFileHandler
from pathlib import Path
from typing import Dict, Iterable, List, Optional, Sequence, Set
from uuid import uuid4

from telethon import events
from telethon.events import NewMessage

from .database import Database


@dataclass(slots=True)
class GuardRule:
    rule_id: int
    include: List[str]
    exclude: List[str]
    regex_patterns: List[str]
    compiled_regex: List[re.Pattern[str]]
    raw_targets: Optional[List[int]]
    target_variants: Optional[Set[int]]
    reply_text: str
    reply_image: Optional[str]
    created_at: float = field(default_factory=lambda: time.time())
    last_reply: Dict[int, float] = field(default_factory=dict)


class ReplyGuard:
    """Menangani beberapa aturan auto-reply sekaligus."""

    def __init__(
        self,
        client,
        database: Database,
        user_id: int,
        media_dir: Path,
        rate_limit_seconds: int = 30,
        log_dir: str | Path | None = None,
    ) -> None:
        self.client = client
        self._database = database
        self._user_id = user_id
        self.rate_limit_seconds = rate_limit_seconds
        self._event: Optional[NewMessage] = None
        self._me_id: Optional[int] = None
        self._rules: Dict[int, GuardRule] = {}
        self._next_rule_id = 1
        self._media_dir = media_dir.resolve()
        self.logger = logging.getLogger(f"userbot.reply_guard.{user_id}")
        self._setup_logger(log_dir)

    # ------------------------------------------------------------------
    # Public API
    # ------------------------------------------------------------------
    @property
    def is_active(self) -> bool:
        return bool(self._rules)

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
        rule_id: Optional[int] = None,
        persist: bool = True,
    ) -> int:
        if me_id is not None:
            self._me_id = me_id
        if self._me_id is None:
            raise ValueError("ID akun userbot belum tersedia.")

        if rule_id is not None and rule_id in self._rules:
            raise ValueError(f"Rule dengan id {rule_id} sudah ada.")

        include_list = [item for item in include if item]
        exclude_list = [item for item in exclude if item]
        regex_list = [item for item in regex if item]

        compiled_regex: List[re.Pattern[str]] = []
        for pattern in regex_list:
            try:
                compiled_regex.append(re.compile(pattern, re.IGNORECASE))
            except re.error as exc:
                raise ValueError(f"Regex tidak valid: {pattern} ({exc})") from exc

        normalized_targets = self._normalize_raw_targets(targets)
        target_variants = (
            self._build_target_variants(normalized_targets)
            if normalized_targets is not None
            else None
        )

        reply_text = reply_text.strip()
        if not reply_text:
            raise ValueError("Pesan balasan tidak boleh kosong.")

        reply_image_path = self._prepare_media_path(reply_image) if reply_image else None

        if persist:
            rule_id = self._database.add_reply_guard_rule(
                user_id=self._user_id,
                include=include_list,
                exclude=exclude_list,
                regex=regex_list,
                targets=normalized_targets,
                reply_text=reply_text,
                reply_image=reply_image_path,
            )
            self._next_rule_id = max(self._next_rule_id, rule_id + 1)
        else:
            if rule_id is None:
                raise ValueError("rule_id harus disediakan saat persist=False")
            self._next_rule_id = max(self._next_rule_id, rule_id + 1)

        rule = GuardRule(
            rule_id=rule_id,
            include=include_list,
            exclude=exclude_list,
            regex_patterns=regex_list,
            compiled_regex=compiled_regex,
            raw_targets=normalized_targets,
            target_variants=target_variants,
            reply_text=reply_text,
            reply_image=reply_image_path,
        )

        self._rules[rule_id] = rule
        self._ensure_handler()
        self.logger.info(
            "Reply guard rule ditambahkan id=%s include=%s exclude=%s regex=%s targets=%s",
            rule.rule_id,
            rule.include,
            rule.exclude,
            rule.regex_patterns,
            rule.raw_targets if rule.raw_targets is not None else "allgroup",
        )
        return rule_id

    def deactivate(self, rule_id: Optional[int] = None) -> bool:
        if rule_id is None:
            removed = list(self._rules.keys())
            self._rules.clear()
            self._remove_event_handler()
            self.logger.info("Semua aturan reply guard dihentikan (%s rule)", len(removed))
            if removed:
                self._database.delete_all_reply_guard_rules(self._user_id)
            changed = bool(removed)
        else:
            removed = self._rules.pop(rule_id, None)
            if removed is None:
                self.logger.info("Tidak ada rule reply guard dengan id=%s", rule_id)
                changed = False
            else:
                self.logger.info("Rule reply guard dihentikan id=%s", rule_id)
                self._database.delete_reply_guard_rule(self._user_id, rule_id)
                changed = True
        if not self._rules:
            self._remove_event_handler()
        return changed

    def restore(self, me_id: int) -> None:
        self._me_id = me_id
        self._rules.clear()
        db_rules = self._database.list_reply_guard_rules(self._user_id)
        for row in db_rules:
            try:
                self.activate(
                    include=row.get("include", []),
                    exclude=row.get("exclude", []),
                    regex=row.get("regex", []),
                    targets=row.get("targets"),
                    reply_text=row.get("reply_text", ""),
                    reply_image=row.get("reply_image"),
                    me_id=me_id,
                    rule_id=row.get("id"),
                    persist=False,
                )
            except ValueError as exc:
                self.logger.warning("Lewati rule id=%s karena error restore: %s", row.get("id"), exc)
        if self._rules:
            self.logger.info("Reply guard dipulihkan (%s rule)", len(self._rules))
        else:
            self.logger.info("Tidak ada rule reply guard tersimpan")

    def get_status(self) -> dict[str, object]:
        rules = []
        for rule in sorted(self._rules.values(), key=lambda item: item.rule_id):
            media_label = "ADA" if rule.reply_image else "TIDAK"
            rules.append(
                {
                    "id": rule.rule_id,
                    "include": list(rule.include),
                    "exclude": list(rule.exclude),
                    "regex": list(rule.regex_patterns),
                    "targets": list(rule.raw_targets) if rule.raw_targets is not None else None,
                    "reply_text": rule.reply_text,
                    "has_media": bool(rule.reply_image),
                    "media_label": media_label,
                    "created_at": rule.created_at,
                }
            )
        return {
            "active": bool(self._rules),
            "rules": rules,
            "rate_limit": self.rate_limit_seconds,
        }

    async def capture_media(self, message) -> Optional[str]:
        if message is None:
            self.logger.debug("capture_media: message kosong, skip pengambilan media")
            return None
        media = getattr(message, "media", None)
        if not media:
            self.logger.debug("capture_media: tidak ada media pada pesan perintah")
            return None
        if not self._is_image_message(message):
            self.logger.error("Lampiran pada perintah bukan tipe gambar; operasi dibatalkan")
            raise ValueError("Lampiran harus berupa foto atau gambar.")
        self._media_dir.mkdir(parents=True, exist_ok=True)
        timestamp = int(time.time())
        temp_prefix = f"tmp_{timestamp}_{uuid4().hex[:8]}"
        try:
            filename = await message.download_media(file=str(self._media_dir / temp_prefix))
        except Exception as exc:
            self.logger.exception("Gagal mengunduh lampiran dari pesan", exc_info=True)
            raise ValueError("Gagal menyimpan lampiran gambar.") from exc
        if not filename:
            self.logger.error("download_media mengembalikan nilai kosong")
            raise ValueError("Gagal menyimpan lampiran gambar.")
        path = Path(filename).resolve()
        if not path.exists() or path.is_dir():
            self.logger.error("File lampiran tidak ditemukan atau bukan file biasa: %s", path)
            raise ValueError("Gagal menyimpan lampiran gambar.")
        suffix = path.suffix or ".jpg"
        final_target = self._media_dir / f"reply_{timestamp}_{uuid4().hex[:8]}{suffix}"
        try:
            if path != final_target:
                path.rename(final_target)
                path = final_target.resolve()
        except OSError as exc:
            self.logger.warning("Gagal mengganti nama file media: %s", exc)
            path = path.resolve()
        try:
            path.relative_to(self._media_dir)
        except ValueError:
            self.logger.warning("File media berada di luar direktori target; mencoba memindahkan")
            try:
                if final_target.exists() and final_target != path:
                    final_target.unlink()
                path.replace(final_target)
                path = final_target.resolve()
            except Exception as exc:
                self.logger.exception("Gagal memindahkan file media", exc_info=True)
                raise ValueError("Gagal menyimpan lampiran gambar.") from exc
        self.logger.info("Lampiran reply guard tersimpan di %s", path)
        return str(path)

    # ------------------------------------------------------------------
    # Internal helpers
    # ------------------------------------------------------------------
    def _ensure_handler(self) -> None:
        if self._event is None:
            self._event = events.NewMessage(incoming=True)
            self.client.add_event_handler(self._on_new_message, self._event)

    def _remove_event_handler(self) -> None:
        if self._event is not None:
            try:
                self.client.remove_event_handler(self._on_new_message, self._event)
            except Exception:
                self.logger.debug("Gagal melepas handler reply guard", exc_info=True)
        self._event = None

    async def _on_new_message(self, event: events.NewMessage.Event) -> None:
        if not self._rules:
            return
        if event.out:
            return
        if not (event.is_group or event.is_channel):
            return
        if self._me_id is not None and event.sender_id == self._me_id:
            return
        chat_id = event.chat_id
        if chat_id is None:
            return
        message_text = event.raw_text or ""
        if not message_text:
            return
        now = time.monotonic()
        for rule in list(self._rules.values()):
            if not self._is_target(rule, chat_id):
                continue
            if not self._match_rule(rule, message_text):
                continue
            if not self._allow_send(rule, chat_id, now):
                continue
            await self._send_reply(rule, event, chat_id, now)

    async def _send_reply(
        self,
        rule: GuardRule,
        event: events.NewMessage.Event,
        chat_id: int,
        now: float,
    ) -> None:
        file_arg: Optional[str] = None
        if rule.reply_image:
            image_path = Path(rule.reply_image)
            if image_path.exists() and image_path.is_file():
                file_arg = str(image_path)
            else:
                self.logger.warning(
                    "File gambar rule reply guard hilang id=%s path=%s",
                    rule.rule_id,
                    rule.reply_image,
                )
        try:
            await event.reply(rule.reply_text, file=file_arg)
        except Exception:
            self.logger.exception(
                "Gagal mengirim auto-reply rule=%s ke chat %s (message id=%s)",
                rule.rule_id,
                chat_id,
                getattr(event.message, "id", None),
            )
            return
        rule.last_reply[chat_id] = now
        self.logger.info(
            "Auto-reply terkirim rule=%s chat=%s msg_id=%s",
            rule.rule_id,
            chat_id,
            getattr(event.message, "id", None),
        )

    def _allow_send(self, rule: GuardRule, chat_id: int, now: float) -> bool:
        last = rule.last_reply.get(chat_id)
        if last is None:
            return True
        if now - last < self.rate_limit_seconds:
            self.logger.info(
                "Lewatkan auto-reply rule=%s chat=%s karena rate limit",
                rule.rule_id,
                chat_id,
            )
            return False
        return True

    def _is_target(self, rule: GuardRule, chat_id: int) -> bool:
        if rule.target_variants is None:
            return True
        variants = self._chat_id_variants(chat_id)
        return not rule.target_variants.isdisjoint(variants)

    def _match_rule(self, rule: GuardRule, text: str) -> bool:
        lower_text = text.lower()
        if rule.include and not all(keyword.lower() in lower_text for keyword in rule.include):
            return False
        if rule.exclude and any(keyword.lower() in lower_text for keyword in rule.exclude):
            return False
        if rule.compiled_regex:
            return any(pattern.search(text) for pattern in rule.compiled_regex)
        return True

    def _prepare_media_path(self, image_path: Optional[str]) -> Optional[str]:
        if not image_path:
            return None
        candidate = Path(image_path).expanduser().resolve()
        if not candidate.exists() or not candidate.is_file():
            raise ValueError(f"File gambar tidak ditemukan: {candidate}")
        self._media_dir.mkdir(parents=True, exist_ok=True)
        dest = self._media_dir / candidate.name
        if dest == candidate:
            return str(candidate)
        try:
            if dest.exists():
                dest.unlink()
            candidate.replace(dest)
            candidate = dest.resolve()
        except Exception:
            self.logger.debug("Gagal memindahkan file gambar ke direktori media", exc_info=True)
        return str(candidate)

    def _normalize_raw_targets(self, targets: Optional[Sequence[int]]) -> Optional[List[int]]:
        if targets is None:
            return None
        result: List[int] = []
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

    def _build_target_variants(self, targets: Iterable[int]) -> Set[int]:
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
            for handler in self.logger.handlers
        )
        if not already:
            handler = RotatingFileHandler(file_path, maxBytes=5 * 1024 * 1024, backupCount=2)
            handler.setFormatter(
                logging.Formatter(
                    "%(asctime)s | %(levelname)s | %(message)s",
                    datefmt="%Y-%m-%d %H:%M:%S",
                )
            )
            self.logger.addHandler(handler)
        self.logger.setLevel(logging.INFO)
        self.logger.propagate = False

    def _is_image_message(self, message) -> bool:
        photo = getattr(message, "photo", None)
        if photo is not None:
            return True
        document = getattr(message, "document", None)
        if document is None:
            return False
        mime = getattr(document, "mime_type", "") or ""
        return mime.startswith("image/")
