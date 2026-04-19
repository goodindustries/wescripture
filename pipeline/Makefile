# WeScripture corpus pipeline.
# DAG: fetch -> normalize -> jst_weave -> donaldson -> upsert -> embed -> connect -> audit
#
# All artifacts land under $(BUILD). Each stage is a pure function of its input
# stamps, so `make <target>` is incremental.

PY       ?= python3
BUILD    ?= build
STAMPS   := $(BUILD)/stamps

$(shell mkdir -p $(STAMPS))

.PHONY: all fetch normalize jst_weave donaldson upsert embed connect audit clean help

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

# ── Stage 3: jst_weave ──────────────────────────────────────────────────────
# Merge JST variants inline as verse_variant rows. Deterministic: emits
# (verse_id, variant_kind, text) tuples; never mutates base verses.
jst_weave: $(STAMPS)/jst_weave ## Merge JST variants as verse_variant rows
$(STAMPS)/jst_weave: $(STAMPS)/normalize
	$(PY) -m pipeline.weave.run --verses $(BUILD)/verses --out $(BUILD)/variants
	@touch $@

# ── Stage 4: donaldson ──────────────────────────────────────────────────────
# Ingest Donaldson commentary, segment into paragraphs, map to verse ranges.
donaldson: $(STAMPS)/donaldson ## Donaldson commentary -> commentary_para rows
$(STAMPS)/donaldson: $(STAMPS)/normalize
	$(PY) -m pipeline.donaldson.run --verses $(BUILD)/verses --out $(BUILD)/commentary
	@touch $@

# ── Stage 5: upsert ─────────────────────────────────────────────────────────
# Push verse / verse_variant / commentary_para rows into Supabase.
# Requires SUPABASE_URL + SUPABASE_SERVICE_ROLE_KEY in env.
upsert: $(STAMPS)/upsert ## Push normalized rows into Supabase
$(STAMPS)/upsert: $(STAMPS)/jst_weave $(STAMPS)/donaldson
	$(PY) -m pipeline.db.upsert --verses $(BUILD)/verses \
		--variants $(BUILD)/variants --commentary $(BUILD)/commentary
	@touch $@

# ── Stage 6: embed ──────────────────────────────────────────────────────────
# Compute + store embeddings for verses and commentary paragraphs in pgvector.
embed: $(STAMPS)/embed ## Verse + commentary embeddings -> pgvector
$(STAMPS)/embed: $(STAMPS)/upsert
	$(PY) -m pipeline.embed.run
	@touch $@

# ── Stage 7: connect ────────────────────────────────────────────────────────
# Build connection table: top-K=40 cosine neighbors, threshold >= 0.28.
connect: $(STAMPS)/connect ## Build connection table from embeddings
$(STAMPS)/connect: $(STAMPS)/embed
	$(PY) -m pipeline.connect.run --top-k 40 --min-cosine 0.28
	@touch $@

# ── Stage 8: audit ──────────────────────────────────────────────────────────
# Strict audit: row counts per book/chapter, orphan FK checks, license provenance.
# Non-zero exit fails CI.
audit: $(STAMPS)/connect ## Strict audit (row counts, orphans, licenses)
	$(PY) -m pipeline.audit.run --strict
