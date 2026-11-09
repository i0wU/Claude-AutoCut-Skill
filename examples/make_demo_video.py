#!/usr/bin/env python3
"""Make a synthetic demo video for trying Claude AutoCut without a real recording.

    python examples/make_demo_video.py demo.mp4 [--vertical] [--lang en|pt]

The speech comes from the text-to-speech engine of your system (Windows SAPI, macOS `say` or Linux
`espeak-ng`) and the picture is FFmpeg's test pattern. The script contains a redone take, long pauses, a
filler word and a negation, so every part of the editor has something to do. Nothing here is a real person.
"""
import argparse
import platform
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

LINES = {
    'en': [('Hello everyone.', 1.8), ('Today I will show you', 0.6), ('Today I will show you how to edit a video automatically.', 1.6),
           ('Um,', 0.4), ('this is not magic.', 0.8), ('It is a simple process that anyone can follow.', 1.2), ('Thanks for watching.', 0.6)],
    'pt': [('Olá pessoal.', 1.8), ('Hoje eu vou mostrar', 0.6), ('Hoje eu vou mostrar como editar um vídeo automaticamente.', 1.6),
           ('Hum,', 0.4), ('isso não é mágica.', 0.8), ('É um processo simples que qualquer pessoa consegue seguir.', 1.2), ('Obrigado por assistir.', 0.6)],
}


def tts_windows(text_breaks, lang, wav):
    culture = 'pt-BR' if lang == 'pt' else 'en-US'
    ssml = (f'<speak version="1.0" xmlns="http://www.w3.org/2001/10/synthesis" xml:lang="{culture}">' +
            ''.join(f'{t}<break time="{int(b * 1000)}ms"/>' for t, b in text_breaks) + '</speak>')
    ps = ('Add-Type -AssemblyName System.Speech; $s = New-Object System.Speech.Synthesis.SpeechSynthesizer; '
          f"$v = $s.GetInstalledVoices() | Where-Object {{ $_.VoiceInfo.Culture.Name -eq '{culture}' }} | Select-Object -First 1; "
          'if ($v) { $s.SelectVoice($v.VoiceInfo.Name) }; '
          f"$s.SetOutputToWaveFile('{wav}'); $s.SpeakSsml([Console]::In.ReadToEnd()); $s.Dispose()")
    subprocess.run(['powershell.exe', '-NoProfile', '-Command', ps], input=ssml, text=True, encoding='utf-8', check=True)


def tts_other(text_breaks, lang, wav, tmp):
    parts = []
    for k, (t, b) in enumerate(text_breaks):
        p = Path(tmp) / f'p{k}.wav'
        if platform.system() == 'Darwin':
            aiff = p.with_suffix('.aiff')
            subprocess.run(['say', '-o', str(aiff), t], check=True)
            subprocess.run(['ffmpeg', '-v', 'error', '-y', '-i', str(aiff), str(p)], check=True)
        else:
            exe = shutil.which('espeak-ng') or shutil.which('espeak')
            if not exe:
                sys.exit('no text-to-speech engine found (install espeak-ng)')
            subprocess.run([exe, '-v', 'pt-br' if lang == 'pt' else 'en-us', '-w', str(p), t], check=True)
        s = Path(tmp) / f's{k}.wav'
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'anullsrc=r=22050:cl=mono', '-t', str(b), str(s)], check=True)
        parts += [p, s]
    lst = Path(tmp) / 'list.txt'
    lst.write_text(''.join(f"file '{x.as_posix()}'\n" for x in parts), encoding='utf-8')
    subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'concat', '-safe', '0', '-i', str(lst), '-ar', '22050', '-ac', '1', str(wav)], check=True)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('out')
    ap.add_argument('--vertical', action='store_true')
    ap.add_argument('--lang', default='en', choices=sorted(LINES))
    a = ap.parse_args()
    with tempfile.TemporaryDirectory() as tmp:
        wav = str(Path(tmp) / 'speech.wav')
        if platform.system() == 'Windows':
            tts_windows(LINES[a.lang], a.lang, wav)
        else:
            tts_other(LINES[a.lang], a.lang, wav, tmp)
        size = '1080x1920' if a.vertical else '1280x720'
        # 0.8 s of silence before the first word, so the editor has a lead-in to trim
        subprocess.run(['ffmpeg', '-v', 'error', '-y', '-f', 'lavfi', '-i', f'testsrc2=size={size}:rate=30',
                        '-i', wav, '-filter_complex', '[1:a]adelay=800|800,apad=pad_dur=0.6,aresample=48000[a]',
                        '-map', '0:v', '-map', '[a]', '-shortest', '-c:v', 'libx264', '-pix_fmt', 'yuv420p', '-crf', '23',
                        '-c:a', 'aac', '-b:a', '128k', '-map_metadata', '-1', a.out], check=True)
    print(a.out)


if __name__ == '__main__':
    main()
