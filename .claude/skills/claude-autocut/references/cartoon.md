# Cartoon mode: storyboard reference

The cartoon mode draws a paper-cutout scene in the top part of a 1080x1920 frame, a torn-paper divider, and
the speaker's video below. The scene follows the speech through `storyboard.json`, which you write after
reading `speech.md`. The drawing engine and its library use Portuguese key names (the engine's original
language): the glossary below gives the English meaning of each key and value.

## Coordinates and layout

- Times are seconds on the timeline of the project video (`assets/source.mp4`).
- The top canvas is 1200 logical units wide and about 1055 high (the default layout: 950 px of 1920).
  The host sits at about `x 520, y 905` (the edge of the desk); `x` grows to the right, `y` grows downwards.
- Keep large on-screen text below `y = 262 + 0.95 * tam` so it clears the top 230 px of Reels/TikTok.
- Layout lives in `config.json`: `top.height`, `divider.y`, `video.y`, `video.crop_y` (0-1, which part of a
  vertical source shows in the lower box) and `video.fit` (`window` for vertical sources, `cover` for horizontal).

## Storyboard schema

```json
{
  "subject": "what the video is about",
  "characters": {"criador": "the host", "ia": "a friendly laptop"},
  "blocks": ["... written by `cartoon init`, read-only ..."],
  "cenas": [
    {"id": "s01", "t0": 0.0, "t1": 4.5,
     "cenario": {"nome": "quarto"},
     "transicao": {"tipo": "rasgo", "dur": 0.5},
     "camera": [[0.0, 600, 527, 1.0], [4.5, 600, 515, 1.05]],
     "atores": [{"nome": "criador", "x": 520, "y": 905, "partes": true, "fala": true,
                 "chaves": [{"t": 0.0, "pose": "apresenta", "rosto": "feliz", "olhar": [0, 0]},
                            {"t": 2.7, "pose": "mesa", "rosto": "neutro"}]}],
     "objetos": [{"tipo": "celular_tripe", "x": 960, "y": 1000, "s": 0.85, "entra": 0.0, "efeito": "nenhum", "camada": "frente"}],
     "textos": [{"t": 0.1, "ate": 2.6, "txt": "HELLO|EVERYONE", "destaque": ["EVERYONE"], "x": 760, "y": 350, "tam": 88}]}
  ]
}
```

Rules checked by `cartoon check`:
- scenes are contiguous: the first starts at 0, each starts where the previous ends, the last ends at the
  video duration (no gaps, no overlaps);
- scenario, actor and object names exist in the library (or in `scenes/*.js` of the project);
- every word of an on-screen text is spoken within 1.5 s of it.

## Glossary

| Key | Meaning |
|---|---|
| `cenas` | scenes |
| `t0`, `t1` | scene start and end (s) |
| `cenario.nome` | background scenario |
| `transicao.tipo`, `dur` | transition into this scene: `rasgo` (torn page), `zoom`, `corte` (cut); duration in s |
| `camera` | list of `[t, center_x, center_y, zoom]` keys, interpolated |
| `atores` | actors: `nome` (name), `x`, `y`, `s` (scale), `partes: true` (hands drawn over the desk), `fala: true` (mouth follows the voice) |
| `chaves` | keyframes of an actor: `t`, `pose`, `rosto` (face), `olhar` ([dx, dy] gaze), `inclina` (tilt), `nega: true` (shakes the head) |
| `objetos` | objects: `tipo` (type), `x`, `y`, `s` (scale), `rot` (rotation), `entra` (enters at), `efeito` (entrance effect), `sai` (leaves at), `sai_efeito`, `flutua` (float, px), `camada` (layer: `fundo` back, `meio` middle, `frente` front) |
| `textos` | big on-screen words: `t`, `ate` (until), `txt` (`|` breaks the line), `destaque` (words in yellow), `tempos` (time of each word, optional), `x`, `y`, `tam` (size), `giro` (rotation) |

## Catalog

**Scenarios** (`cenario.nome`): `quarto` (bedroom studio: night window, ring light, shelves, wooden desk),
`sala` (living room: striped wall, lamp, frames, knitted sofa), `bancada` (craft bench: cork board with
notes, shelf, cutting mat with ruler and pencils).

**Actors** (`atores[].nome`):
- `criador`, the host behind the desk (half body). Poses: `mesa` (hands on desk), `maos_juntas` (hands
  together), `um` (one finger up), `aponta_si` (points at self), `ombros` (shrugs), `nao` (no gesture),
  `aponta_dir` (points right), `apresenta` (presents), `coca_cabeca` (scratches head), `explica` (explains),
  `joinha` (thumbs up). Faces (`rosto`): `neutro`, `feliz` (happy), `sem_graca` (embarrassed, sweat),
  `surpreso` (surprised), `confiante` (confident), `pensativo` (thoughtful).
  Appearance: `"cores": {"pele", "cabelo", "barba", "camiseta", "armacao", "com_barba": true, "com_oculos": true, "com_relogio": true}`
  (skin, hair, beard, shirt, glasses frame colors; beard, glasses and watch are off by default).
- `ia`, a laptop with a face. Keys: `ligado` 0-1 (screen on), `fones` 0-1 (headphones), `rosto`
  (`feliz`, `atenta` attentive, `ouvindo` listening, `foco` focused, `orgulho` proud, `dormindo` asleep), `olhar`.
- `mao_celular`, a hand holding a phone (close-up); `tela` = name of an object drawn on the screen.

**Objects** (`objetos[].tipo`): `celular_tripe` (phone on a tripod), `balao` (speech balloon), `interrogacao`
(question mark), `lixeira` (bin; `cheia` 0-1 fullness), `bola_papel` (paper ball), `ficha` (paper card,
`txt`), `circulo` (red marker circle), `tesoura` (scissors), `lupa` (magnifier), `fones` (headphones),
`ondas` (sound waves), `estrela` (star), `tela_video_limpo` (screen with a clean video), `take` (a recorded
take card, `rotulo` label; `amassa` time to crumple it).
Entrance effects (`efeito`): `pop`, `cai` (falls in), `sobe` (rises), `desliza_esq`, `desliza_dir` (slides),
`aparece` (fades in), `nenhum` (none). Exit: `sai` time with `sai_efeito: "cai"`.

## Writing a good storyboard

- One scene per idea of the speech (a block or two of `speech.md`), 2 to 8 seconds each.
- Change the pose at the words that carry the meaning (the time of the word in `transcript.json`).
- An object enters on the word it represents; on-screen text shows only words that are said, never
  uncertain words (marked in `speech.md`), and never drops a negation.
- Same room: use `corte` and continue the camera; new room: `rasgo`.
- Keep something moving in long pauses (a camera key, a gesture): the stage adds a slow idle drift, but a
  pause with no event at all looks frozen.
- Project-specific drawings go in `scenes/*.js` with the same API as the library
  (`Palco.cenario(name, {fundo, frente})`, `Palco.ator(name, fn)`, `Palco.objeto(type, fn)`).

## Credits

The paper engine (`engine/`) is from drawn-by-code by illodev (MIT, see `engine/LICENSE-drawn-by-code.txt`).
The library (`library/`), the stage and the characters are original to Claude AutoCut (MIT). Fonts: Anton and
Patrick Hand (SIL Open Font License 1.1, texts in `fonts/`). GSAP and HyperFrames are installed by npm/npx and
are not part of this repository.
