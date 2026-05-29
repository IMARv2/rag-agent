import logging
from pathlib import Path
from watchdog.observers import Observer
from watchdog.events import FileSystemEventHandler
import sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from indexer.indexer import index_file, delete_file, SUPPORTED_EXTS
from config import settings

log = logging.getLogger("watcher")

class DocHandler(FileSystemEventHandler):
    def _should_handle(self, path):
        return Path(path).suffix.lower() in SUPPORTED_EXTS

    def _rel(self, path):
        return str(Path(path).relative_to(settings.docs_path))

    def on_created(self, event):
        if not event.is_directory and self._should_handle(event.src_path):
            log.info("New file: %s", event.src_path)
            try:
                log.info("Indexed: %s", index_file(event.src_path))
            except Exception as e:
                log.error("Index error: %s", e)

    def on_modified(self, event):
        if not event.is_directory and self._should_handle(event.src_path):
            log.info("File modified: %s", event.src_path)
            try:
                log.info("Re-indexed: %s", index_file(event.src_path))
            except Exception as e:
                log.error("Index error: %s", e)

    def on_deleted(self, event):
        if not event.is_directory and self._should_handle(event.src_path):
            log.info("File deleted: %s", event.src_path)
            try:
                log.info("Removed from index: %s", delete_file(self._rel(event.src_path)))
            except Exception as e:
                log.error("Delete error: %s", e)

    def on_moved(self, event):
        if not event.is_directory:
            if self._should_handle(event.src_path):
                try:
                    log.info("Moved old removed: %s", delete_file(self._rel(event.src_path)))
                except Exception as e:
                    log.error("Move-delete error: %s", e)
            if self._should_handle(event.dest_path):
                try:
                    log.info("Moved new indexed: %s", index_file(event.dest_path))
                except Exception as e:
                    log.error("Move-index error: %s", e)

def start_watcher():
    observer = Observer()
    observer.schedule(DocHandler(), settings.docs_path, recursive=True)
    observer.start()
    log.info("Watching: %s", settings.docs_path)
    return observer
