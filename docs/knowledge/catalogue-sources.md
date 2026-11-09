# Catalogue source findings

## Verified public pages

- Official catalogue: https://www.tkkg.de/produkte/hoerspiele
- Official catalogue pagination uses a page query parameter, for example https://www.tkkg.de/produkte/hoerspiele?page=3.
- The official page exposes numbered episode headings, synopses, cover image references, speaker lists, and production credits for many releases. Metadata coverage varies by episode.
- TKKG-Site historical index: https://www.tkkg-site.de/de/hoeren/hoerspiele/serie.html
- The historical index links episodes 1 to 206 to individual archive pages and links episodes 207 to 217 to posts on audio.tkkg-site.de.
- Example historical detail page: https://www.tkkg-site.de/de/hoeren/hoerspiele/serie/folge-001/inhalt.html. It exposes synopsis, release medium, label, release information, EANs, track points, cast, production credits, and ratings.
- Example newer episode page: https://audio.tkkg-site.de/post/175481640949/folge207. It exposes synopsis, EAN, publication date, cast, tracks, and production credits.

## Data quality cautions

- Do not assume all metadata fields are present for every episode.
- The official listing includes a live album using an existing episode number. Exclude obvious live album and box set products from the regular episode list.
- The official page text can contain repeated or conflicting episode numbers and titles. Preserve conflicts in the scrape report and do not silently treat every product card as a distinct regular episode.
- The historical archive is the preferred title source for episodes it explicitly indexes. The official catalogue is needed to discover later releases beyond the historical index.
- robots.txt was checked by the runtime scraper. The archive and official catalogue were accessible; audio.tkkg-site.de returned HTTP 403 for robots.txt, so its posts are not fetched and no access control is bypassed. Site terms were not independently reviewed; keep access checks in place.

## Extraction strategy

Use independent source adapters and saved HTML fixtures for tests. Store source URLs and retrieval timestamps with each record. Treat numbering gaps and conflicting titles as review warnings unless a documented rule establishes that a record is invalid.

## Verified live-fetch findings (18 October 2026)

- The historical archive index lists episodes 1–206 at https://www.tkkg-site.de/de/hoeren/hoerspiele/serie.html. Some index hrefs are directory-relative without a leading slash (de/hoeren/...). Resolve them against the origin root or normalize the duplicated /de/hoeren/hoerspiele/ prefix; do not change the audio.tkkg-site.de host for episodes 207–217.
- The official listing's episode detail data is already embedded in the initial HTML inside collapsed div elements with IDs such as detail57142. The adjacent teaser contains the title and cover, and its arrow link uses data-modal="#detail57142". Pair the detail panel with that sibling teaser. No browser automation or guessed XHR endpoint is needed for the fields inspected.
- The listing currently omits main-series episodes 222, 223, and 234 even though verified official detail pages exist: https://www.tkkg.de/produkte/details/roter-drache-222, https://www.tkkg.de/produkte/details/betruger-super-sauber, and https://www.tkkg.de/produkte/details/im-auftrag-des-bosen. These are explicit supplemental sources and should be fetched only when the listing has no record for the number. Keep the catalogue completeness guard enabled if a fallback fails.
- The official listing also includes "Jede Legende hat Ihren Anfang (Hörspiel zum Kinofilm)" labelled as episode 500. Its title identifies it as a film tie-in, not a regular main-series episode. Exclude it by the product title evidence, not by an arbitrary maximum episode number. Also exclude the Adventskalender products, the 209 Neuaufnahme, the Live-Album, and Die Weihnachtsgeiseln, which is a separate unnumbered product despite the listing's misleading 239 heading.
- Requests' guessed text encoding produced mojibake in historical titles. Cache and parse response.content bytes so BeautifulSoup can honor the document's charset. Add a regression test for UTF-8 text when response.text is misdecoded.
- The CSV schema must include the series field because the JSON schema requires it; otherwise the live refresh can validate JSON and still fail while writing CSV.
- The official catalogue listing omits episodes 222, 223, and 234, but their verified individual product pages are available. Fetch those explicit URLs only when the listing has no record for the number.
- The 18 October live diagnostic succeeded with 243 unique records numbered 1–243, no gaps, and no schema errors. It fetched 206 archive detail pages and used 3 official detail-page fallbacks. Eleven audio-subdomain posts were skipped due to HTTP 403 on robots.txt; the official catalogue covers their episode metadata. JSON and CSV both contain 243 rows. The branch diagnostic uploads artifacts only and does not commit or deploy generated data.


## Archive release metadata markup (verified 18 October 2026)

- Live episode 001 and 002 pages expose the release fields in this order: Medium, Label, Erscheinungstermin, EAN. The values appear in the same order after the labels in the page's rendered text.
- Episode 001 displays medium `LP / MC / CD`, label `EUROPA`, release information `1981 (LP / MC) / 12. Mai 2003 (CD)`, and EANs `743219895943 (MC) / 743219895929 (CD)`. Episode 002 uses the same layout and gives its own release information and EANs.
- Do not parse these fields by matching each label to the next line in flattened page text. Associate the label and value columns/blocks structurally and preserve their order. Do not assume every episode has every field.
- A release entry can describe multiple media editions and dates. Preserve the archive's full release text in the physical-release record. The top-level `release_year` may use a year explicitly present in that text; the top-level `release_date` remains null unless a single complete date can be represented without ambiguity.
- Catalogue validation should reject field labels stored as values and an EAN field that contains no plausible digit identifier. This is intended to prevent malformed extraction from publishing even when it passes the JSON schema.


## Official episode listening links (verified 18 October 2026)

- The official listing at https://www.tkkg.de/produkte/hoerspiele exposes a separate “Jetzt anhören” destination for individual episode cards. For example, the link for episode 243 resolves to https://tkkg.lnk.to/-243AW, whose landing page is titled “TKKG - Folge 243: Die Fährte des Hehlers”.
- The landing page is an episode-specific official listening hub. It is safe to label it as an official episode listening page, but platform availability should not be inferred merely from the hub URL.
- The official universal page https://tkkg.lnk.to/alle-hoerspiele and the official playlists page are series-wide destinations, not per-episode links. Do not assign the generic URL to every episode as if it were a direct episode destination.
- When parsing the official listing, associate each “Jetzt anhören” link only with the adjacent episode detail panel and stop at the next product teaser. Validate the destination as HTTPS on the exact tkkg.lnk.to hostname. Do not synthesize Linkfire aliases from episode numbers.
- Service-specific searches (Spotify, Apple Music, Amazon Music, Deezer, YouTube Music, YouTube) may be offered as clearly labelled search shortcuts. They are not evidence that a particular release is available on that service.


## Source precedence for merged cast and listening-link validation (18 October 2026)

- The archive and official catalogue format cast lists differently: the archive may combine multiple character names for one performer, while the official page often lists separate character entries. Do not concatenate these lists. The archive is preferred for episodes with archive detail records; use the official cast only when the preferred record has no cast entries. This preserves the richer archive representation and avoids duplicate performers/roles.
- DNS hostnames are case-insensitive. Official Linkfire URLs may be emitted with an uppercase hostname; normalize stored hostnames to lowercase and validate the schema without rejecting an otherwise valid destination.
- The post-merge scrape report showed 34 official listening hubs and 34 schema failures caused by uppercase `TKKG.lnk.to` hostnames. Those failures prevented catalogue publication; they were validation failures, not evidence that the destinations were invalid.
