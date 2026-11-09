# Privacy

## What the skill does with your media

- Everything runs on your computer. Your video, audio and transcripts are not sent anywhere.
- The source video is only read. Outputs go to the project folder you choose (`-o`).
- Network access happens only to download public dependencies: Python packages (pip), the Whisper model
  (Hugging Face), HyperFrames and its headless browser (npx), GSAP (npm). No account or API key is used.
- Project folders contain your transcript and renders. Treat them as private and keep them out of public
  repositories (the `.gitignore` here ignores media and render folders).

## What this repository contains

Only code, documentation, tests, two open fonts with their licenses and the four MIT engine files listed in
`THIRD_PARTY_NOTICES.md`. No video, audio, image, transcript of a real person, credential, token, cookie,
database, log or local configuration. The tests generate their media on the fly (a test pattern and tones);
the demo script generates speech with your own system's text-to-speech.

## How the repository is audited

`tools/audit_public_tree.py` runs locally and in CI over every tracked file and fails on:

- secrets: private key blocks, AWS, GitHub, Slack, Google, OpenAI/Anthropic and Hugging Face token formats,
  JWTs, bearer headers, assigned passwords/tokens/API keys, URLs with embedded credentials;
- personal data: e-mail addresses (except GitHub noreply addresses, example domains and the font author's
  notice required by the OFL), phone numbers, CPF numbers, Windows and Unix home-folder paths;
- files: media of any kind, `.env`, keys, certificates, cookies, databases, credentials files, symlinks,
  binaries other than fonts, files larger than 5 MB;
- an optional local deny list (`--deny-file`, never committed) for names and terms that must not appear.

Commits use the GitHub `noreply` e-mail address of the account.
