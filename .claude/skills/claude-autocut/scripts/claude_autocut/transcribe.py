"""Word-level transcription with faster-whisper (local, no API key)."""
from __future__ import annotations

from pathlib import Path

from .common import AutoCutError, probe, read_json, sha256, write_json

DEFAULT_MODEL = 'small'


def transcribe(media, out_json, model: str = DEFAULT_MODEL, language: str | None = None, device: str = 'cpu',
               compute_type: str = 'int8', prompt: str | None = None, reuse: bool = True) -> dict:
    """Transcribe `media` into `out_json`: {"language", "duration", "words": [{text, start, end, prob}], ...}.

    A transcript of the same file (same SHA-256) with the same model is reused.
    """
    media, out_json = Path(media), Path(out_json)
    info = probe(media)
    if not info['audio']:
        raise AutoCutError(f'{media.name} has no audio track: there is no speech to transcribe')
    digest = sha256(media)
    if reuse and out_json.exists():
        old = read_json(out_json)
        if old.get('source_sha256') == digest and old.get('model') == model:
            return old
    try:
        from faster_whisper import WhisperModel
    except ImportError as e:  # pragma: no cover - depends on the environment
        raise AutoCutError('faster-whisper is not installed. Run: pip install -r requirements.txt') from e
    wm = WhisperModel(model, device=device, compute_type=compute_type)
    segments, tinfo = wm.transcribe(str(media), language=language, word_timestamps=True, initial_prompt=prompt,
                                    vad_filter=False, condition_on_previous_text=False, beam_size=5)
    words, segs = [], []
    for s in segments:
        segs.append({'start': round(s.start, 3), 'end': round(s.end, 3), 'text': s.text.strip()})
        for w in s.words or []:
            text = w.word.strip()
            if text:
                words.append({'text': text, 'start': round(w.start, 3), 'end': round(w.end, 3),
                              'prob': round(float(w.probability), 3)})
    data = {'engine': 'faster-whisper', 'model': model, 'language': tinfo.language,
            'language_probability': round(float(tinfo.language_probability), 3), 'duration': round(info['duration'], 3),
            'source': media.name, 'source_sha256': digest, 'words': words, 'segments': segs}
    write_json(out_json, data)
    return data
