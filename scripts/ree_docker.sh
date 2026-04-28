#!/usr/bin/env bash
set -euo pipefail

MODEL_NAME=""
PROMPT_FILE=""
MAX_NEW_TOKENS="300"
CPU_ONLY=0

while [[ $# -gt 0 ]]; do
  case "$1" in
    --model-name)
      MODEL_NAME="${2:-}"
      shift 2
      ;;
    --prompt-file)
      PROMPT_FILE="${2:-}"
      shift 2
      ;;
    --max-new-tokens)
      MAX_NEW_TOKENS="${2:-300}"
      shift 2
      ;;
    --cpu-only)
      CPU_ONLY=1
      shift
      ;;
    *)
      echo "Unsupported REE wrapper argument: $1" >&2
      exit 2
      ;;
  esac
done

if [[ -z "${MODEL_NAME}" || -z "${PROMPT_FILE}" ]]; then
  echo "Usage: $0 --model-name <model> --prompt-file <path> [--max-new-tokens n] [--cpu-only]" >&2
  exit 2
fi

if [[ ! -f "${PROMPT_FILE}" ]]; then
  echo "Prompt file does not exist: ${PROMPT_FILE}" >&2
  exit 2
fi

PROMPT_DIR="$(cd "$(dirname "${PROMPT_FILE}")" && pwd)"
PROMPT_BASENAME="$(basename "${PROMPT_FILE}")"
GENSYN_CACHE="${GENSYN_CACHE_DIR:-${HOME}/.cache/gensyn}"
REE_IMAGE="${REE_IMAGE:-ree}"
MODEL_SLUG="${MODEL_NAME//\//--}"

mkdir -p "${GENSYN_CACHE}"
chmod 0777 "${GENSYN_CACHE}"

if ! docker image inspect "${REE_IMAGE}" >/dev/null 2>&1; then
  if docker image inspect "gensynai/ree:v0.2.0" >/dev/null 2>&1; then
    docker tag "gensynai/ree:v0.2.0" "${REE_IMAGE}"
  else
    docker pull "gensynai/ree:v0.2.0"
    docker tag "gensynai/ree:v0.2.0" "${REE_IMAGE}"
  fi
fi

EXISTING_TASK_DIR=""
if [[ -d "${GENSYN_CACHE}/${MODEL_SLUG}" ]]; then
  EXISTING_TASK_DIR="$(find "${GENSYN_CACHE}/${MODEL_SLUG}" -mindepth 1 -maxdepth 1 -type d | sort | head -n 1)"
fi

ARGS=(run-all)
if [[ -n "${EXISTING_TASK_DIR}" ]]; then
  ARGS+=(--task-dir "/home/gensyn/.cache/gensyn/${MODEL_SLUG}/$(basename "${EXISTING_TASK_DIR}")")
else
  ARGS+=(--tasks-root /home/gensyn/.cache/gensyn)
fi

ARGS+=(
  --model-name "${MODEL_NAME}"
  --prompt-file "/prompt/${PROMPT_BASENAME}"
  --max-new-tokens "${MAX_NEW_TOKENS}"
  --operation-set reproducible
)

if [[ "${CPU_ONLY}" == "1" ]]; then
  ARGS+=(--cpu-only)
fi

exec docker run --rm \
  -v "${PROMPT_DIR}:/prompt:ro" \
  -v "${GENSYN_CACHE}:/home/gensyn/.cache/gensyn" \
  "${REE_IMAGE}" \
  "${ARGS[@]}"
