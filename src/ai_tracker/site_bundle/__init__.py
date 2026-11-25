"""The data contract between Python and the new website (docs/steg3/datakontrakt.md): a versioned, schema-validated
bundle of static JSON files.

    python -m ai_tracker.site_bundle build [--out web-data] [--today YYYY-MM-DD] [--history-from YYYY-MM]
                                           [--skip-checks] [--series KEY ...] [--no-budgets]
    python -m ai_tracker.site_bundle fixtures [--out web-data-fixtures]   # synthetic bundle (committed)
    python -m ai_tracker.site_bundle validate DIR                          # schema + licence scan + versions
    python -m ai_tracker.site_bundle sizes DIR                             # size report from the manifest
    python -m ai_tracker.site_bundle scan-build web/build [--src web/src]  # licence scan of the built site

Layout of the bundle (one JSON Schema per document type in schema/, copied into the bundle):

    manifest.json            version, build time, git sha, snapshot status (live/reconstructed), files with sizes
    overview.json            record, headline facts, branch tiles, state stripes (branch x month), calendar, regime
    flow.json                L1-L9 with branch states, key series, nowcasts, reconciliations
    branch/G1.json ...       one branch: index and state, counted / not counted / withheld series, history
    series/index.json        every publishable series (search, filters)
    series/<key>.json        one publishable series: metadata, licence and attribution, levels, measures, measure
                             history per month of the record, versions (time travel, encoding versions-v1)
    nowcast/n1.json ...      N1-N6: live files, intervals, scorecard, coverage, backtest calibration
    nowcast/d2.json          D2 horizons 1-8 (shadow)
    regime.json              C4 regime section from the live snapshots
    method.json              register summary: rules, core series per branch, leads, nowcast variants, sources
    withheld.json            withheld series: names and reasons only
    story/<YYYY-MM>.json     the monthly story: cards selected by the pre-registered rule (W13, site_bundle.story)
    story/index.json         every month of the story with its card counts
    letters.json             index of the monthly letters and quarterly reports
    letters/<YYYY-MM>.json, reports/<YYYYQn>.json   the Markdown of each

Python owns all data and the licence gate (site_bundle.gate, which reuses site.data.publishable). The front end reads
only this bundle, never the observation table.
"""

VERSION = "1.2.0"
