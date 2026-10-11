"""Playback through pygame.mixer (no MIDI devices or external drivers)."""

import queue
import threading
import time
from typing import Iterator, Optional

from .synth import SAMPLE_RATE


class AudioPlayer:
    def __init__(self, sr: int = SAMPLE_RATE):
        self.sr = sr
        self._ready = False
        self._started_at: Optional[float] = None

    def ensure_init(self):
        if self._ready:
            return
        import pygame
        # allowedchanges=0 forces the requested mono format and sample rate; if the mixer
        # opened in stereo, raw mono PCM would play at double speed.
        pygame.mixer.init(frequency=self.sr, size=-16, channels=1, buffer=512, allowedchanges=0)
        self._ready = True

    def stop_all(self):
        self._started_at = None
        if not self._ready:
            return
        try:
            import pygame
            pygame.mixer.stop()
        except Exception:
            pass

    def position(self) -> Optional[float]:
        """Seconds elapsed since playback started (None when not playing)."""
        started = self._started_at
        return None if started is None else time.perf_counter() - started

    def play_pcm(self, chunks: Iterator[bytes], stop_flag: threading.Event):
        """Play PCM chunks (blocking; call from a thread). `stop_flag` interrupts it.

        A producer thread synthesizes ahead while this one queues the chunks on a single
        channel, so the tempo does not depend on how long synthesis takes.
        """
        self.ensure_init()
        import pygame

        self._session = session = getattr(self, "_session", 0) + 1
        self._started_at = None
        ready: "queue.Queue" = queue.Queue(maxsize=16)

        def produce():
            def put(item) -> bool:
                while not stop_flag.is_set():
                    try:
                        ready.put(item, timeout=0.05)
                        return True
                    except queue.Full:
                        pass
                return False
            try:
                for pcm in chunks:
                    if not put(pcm):
                        return
                put(None)
            except Exception as error:  # re-raised in the playback thread
                put(error)

        threading.Thread(target=produce, daemon=True).start()

        def wait_while(condition) -> bool:
            """Wait while `condition()` holds; return False if a stop was requested."""
            while condition():
                if stop_flag.is_set():
                    return False
                time.sleep(0.005)
            return not stop_flag.is_set()

        channel = None
        try:
            while True:
                try:
                    item = ready.get(timeout=0.05)
                except queue.Empty:
                    if stop_flag.is_set():
                        return
                    continue
                if item is None:
                    break
                if isinstance(item, Exception):
                    raise item
                sound = pygame.mixer.Sound(buffer=item)
                # the channel queue holds a single sound: wait for the previous one to start
                if channel is not None and not wait_while(lambda: channel.get_queue() is not None):
                    return
                if channel is not None and channel.get_busy():
                    channel.queue(sound)
                else:
                    channel = sound.play()
                    if channel is None:
                        raise RuntimeError("No audio channel available.")
                    if self._started_at is None:
                        self._started_at = time.perf_counter()
            if channel is not None:
                wait_while(channel.get_busy)
        finally:
            stop_flag.set()  # releases the producer
            if self._session == session:  # do not cut off a newer playback
                self.stop_all()
