# WeScripture corpus pipeline.
# DAG: fetch -> normalize -> jst_weave -> donaldson -> upsert -> embed -> connect -> audit
#
# All artifacts land under $(BUILD). Each stage is a pure function of its input
# stamps, so `make <target>` is incremental.

PY       ?= python3
BUILD    ?= build
STAMPS   := $(BUILD)/stamps

$(shell mkdir -p $(STAMPS))

.PHONY: all fetch normalize clean help

all: audit ## Run the full DAG end to end

help: ## List targets
	@awk 'BEGIN{FS=":.*##"; printf "\nTargets:\n"} /^[a-zA-Z_-]+:.*##/ {printf "  %-14s %s\n", $$1, $$2}' $(MAKEFILE_LIST)

clean: ## Wipe build artifacts (keeps source inputs)
	rm -rf $(BUILD)

# ── Stage 1: fetch ──────────────────────────────────────────────────────────
# Download raw canonical sources (OpenScriptures OSIS, BoMC HTML, Donaldson).
# Idempotent; honors ETag / If-Modified-Since where supported.
fetch: $(STAMPS)/fetch ## Pull raw canonical sources into build/raw/
$(STAMPS)/fetch:
	$(PY) -m pipeline.fetch.run --out $(BUILD)/raw
	@touch $@

# ── Stage 2: normalize ──────────────────────────────────────────────────────
# Raw HTML/XML → canonical verse JSON keyed by {book}.{ch}.{v}.
normalize: $(STAMPS)/normalize ## HTML/XML -> canonical verse JSON
$(STAMPS)/normalize: $(STAMPS)/fetch
	$(PY) -m pipeline.normalize.run --in $(BUILD)/raw --out $(BUILD)/verses
	@touch $@
