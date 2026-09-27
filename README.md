# Magic Landing Pages

A Multimodal AI Orchestration System for Generating Targeted Frontend Landing Pages. CM3070 final project.

Speak or type a request. The system builds and edits a landing page.

Demo: [mlp.feathy.com](https://mlp.feathy.com/) (Google sign-in, any account).

## Architecture

```
Next.js builder --voice/text--> FastAPI orchestrator
                                  |- speech:  faster-whisper | Groq | OpenAI
                                  |- LLM:     Ollama | OpenRouter
                                  |- images:  CLIP over a Pexels library
                                  '- MongoDB <-- Next.js reads published pages
```

## Source

| Path | Content |
|---|---|
| `frontend/` | Next.js builder, preview, published pages. See its [README](frontend/README.md). |
| `orchestrator/` | FastAPI app, pipeline, LLM and speech clients |
| `orchestrator/tatl/` | Evaluation harness. See its [README](orchestrator/tatl/README.md). |
| `orchestrator/suite/`, `orchestrator/test_data/` | TATL cases and data |
| `orchestrator/tests/` | pytest tests |
| `orchestrator/reports/` | Benchmark reports used in the report |
| `orchestrator/scripts/` | Asset, benchmark and migration scripts |
| `stt-experiment/` | Speech-to-text experiment |

## Assessment copy limits

- Credentials and cloud deployment config are removed. The copy runs locally only.
- **Photos are not included.** Only `orchestrator/image_library/metadata.json` (478 Pexels records) is in git. Photo files, the CLIP index and embeddings are not.
- Without them the app uses fixed images. CLIP retrieval and its reported Recall@k cannot be reproduced from the clone alone.

Rebuild the library (needs a free `PEXELS_API_KEY` in `orchestrator/.env` and CLIP packages):

```
orchestrator/venv/bin/pip install torch torchvision open_clip_torch pillow
make images-restore
```

`make images-restore` downloads the same 478 photos by Pexels ID, then embeds them. `make images` builds a new library from a fresh search instead.

## Run the checks

Needs Python 3.12 and Node 22+. No keys, no model, no database.

```
make install              # venv, packages, icons
make test                 # orchestrator tests
make suite-deterministic  # TATL suite with a scripted model
make test-web             # frontend tests (run npm ci in frontend/ first)
```

Full TATL suite against a live model:

```
make suite                                              # local Ollama
make suite LLM=openrouter MODEL=qwen/qwen3.5-27b        # needs OPENROUTER_API_KEY
```

## Quick start

Open [localhost:3000](http://localhost:3000) after either route.

**Ollama, no key.** Slow on CPU.

```
docker compose up -d --build
docker compose exec ollama ollama pull qwen3.5
```

**OpenRouter, no GPU.** The key is required. The backend refuses to start without it.

```
export OPENROUTER_API_KEY=sk-or-...
docker compose -f docker-compose.yml -f docker-compose.openrouter.yml up -d --build
```

**Without Docker.** Needs MongoDB on `localhost:27017` and Ollama.

```
cp orchestrator/.env.example orchestrator/.env
ollama pull qwen3.5
make dev-api   # and in another shell:
make dev-web
```

## Config

All options are in `orchestrator/.env.example`. Main ones:

| Variable | Values |
|---|---|
| `MLP_LLM` | `ollama` (default), `openrouter`, `stub` |
| `MLP_LLM_MODEL` | Default model. Empty: `qwen3.5:latest` or `qwen/qwen3.5-27b` |
| `MLP_LLM_MODELS` | Extra `provider:model` entries in the chat menu |
| `MLP_LLM_FALLBACKS` | OpenRouter models to try when the chosen one fails |
| `MLP_STT` | `local` (default), `groq`, `openai` |
| `MLP_IMAGES` | `clip`, `stub`. Empty: CLIP if the library exists |

OpenRouter models must support `response_format`. `:free` models are rate-limited (one page is about 40 calls).

## License

PolyForm Noncommercial 1.0.0. Free for research, learning and non-commercial use. Commercial use needs the author's permission. See [LICENSE](LICENSE) and [NOTICE](NOTICE).
