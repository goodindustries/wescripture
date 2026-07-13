# Bible Translations: Licensing & Schema

## 1. Licensing Constraints

**Proprietary translations are not recommended for free use.** The English Standard Version (ESV) and New International Version (NIV) are under restrictive commercial licenses. Crossway's ESV license and Biblica's NIV license both require explicit licensing agreements and per-request fees for digital distribution. APIs offering these (BibleAPI, Faithlife, etc.) either charge per-request or restrict access to premium tiers. Even nonprofit and educational use typically requires formal permission. These barriers make them unsuitable for a free public scripture platform without significant licensing investment.

## 2. Public-Domain Options (Immediately Usable)

WeScripture can add multiple public-domain translations without licensing barriers:

- **King James Version (KJV):** Already used as base text in `library/chapters/`; public domain. No additional sourcing needed.
- **World English Bible (WEB):** Modern, readable public-domain translation (2002 version and later). Structured JSON per-verse available via [Bible API](https://api.bible/api) (free tier; search for WEB translation) or static files from [unfoldingWord](https://github.com/unfoldingWord/uw-web) repository.
- **American Standard Version (ASV):** 1901 public-domain translation. Per-verse JSON available via [Bible API](https://api.bible/api) or local sourcing from [Project Gutenberg](https://www.gutenberg.org) (plaintext; requires parsing).
- **Darby Bible Translation:** 1890 public-domain translation, valued for literal precision. Per-verse JSON available via [Bible API](https://api.bible/api) or [Open Bible](https://github.com/scrollmapper/bible_databases) repository.
- **Young's Literal Translation (YLT):** 1898 public-domain translation, known for word-for-word rendering. Per-verse JSON available via [Bible API](https://api.bible/api) or [FreeBibleAPI](https://rapidapi.com/fayimora/api/free-bible-api).

**Data sourcing path:** [Bible API](https://api.bible/api) (free tier) is the quickest path — it serves all five translations as JSON with verse-level granularity. No authentication required for free tier; rate-limited to reasonable limits for development/staging. For production scale or offline use, clone structured JSON from [unfoldingWord repositories](https://github.com/unfoldingWord) or [Open Bible](https://github.com/scrollmapper/bible_databases) and version-control locally in `library/assets/translations/`.

## 3. Recommended Schema for `verse.translations`

**Recommended approach:** Array of translation objects, matching the pattern used in `library/donaldson/` (array-of-objects design scales better than flat key-value):

```json
{
  "translations": [
    {
      "slug": "kjv",
      "name": "King James Version",
      "year": 1611,
      "text": "ADAM, Sheth, Enosh,"
    },
    {
      "slug": "web",
      "name": "World English Bible",
      "year": 2002,
      "text": "Adam, Seth, Enosh,"
    },
    {
      "slug": "asv",
      "name": "American Standard Version",
      "year": 1901,
      "text": "Adam, Seth, Enosh,"
    }
  ]
}
```

**Alternative (simpler, flat):** Add each translation as a top-level key:

```json
{
  "text": "ADAM, Sheth, Enosh,",
  "web": "Adam, Seth, Enosh,",
  "asv": "Adam, Seth, Enosh,",
  "darby": "Adam, Seth, Enosh,"
}
```

**Recommendation:** Adopt the array approach. It is more flexible (metadata per translation: year, license, language), scales to 10+ translations without schema churn, and mirrors the structure of related fields like `excerpts` in entity JSON. It also makes filtering and UI presentation cleaner (e.g., "show WEB + KJV" = `filter(t => ['web', 'kjv'].includes(t.slug))`).

## 4. Implementation Roadmap

**Phase 1 (MVP):** Add KJV (already present) + WEB. Fetch WEB from Bible API (free, no setup) or static clone from unfoldingWord. Enrich chapter HTML to include a `translations` array field in verse objects.

**Phase 2:** Add ASV + Darby as optional secondary translations. Implement a "compare translations" view in the reader (tab or split-pane showing verse in multiple versions).

**Phase 3:** Add YLT and explore other public-domain scholarly translations (e.g., Webby Bible, Jubilee Bible). Implement translation preference caching in reader UI (user selects default view).

**Rationale:** Start narrow (KJV + WEB) to prove the schema works in production and measure reader engagement before populating secondary translations. WEB is the highest-leverage choice — most readable modern public-domain version, widest adoption, best data availability. KJV provides the familiar "King James" anchor many users expect.

**Licensing note:** All chosen translations are public domain, pre-1923 (US) or explicitly declared public domain. No licensing review needed. Document each translation's status in a comment or metadata field for future maintainers.
