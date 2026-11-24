"""Public static website (GitHub Pages): the neutral tracking of the AI rollout, branch by branch.

    python -m ai_tracker.site build [--out site] [--history-from 2023-01] [--skip-checks]

Builds site/ (gitignored) from the observation table, the committed snapshots/ and forecasts/:

    index.html            what changed in pace this month: nine branch tiles (state, index, series, change)
    gren-g1.html ...      one page per branch: core series with pace and change-in-pace charts, latest period,
                          known_from, and why uncounted series are not counted
    prognoser.html        N1-N6 live forecasts and the scorecard (champion and shadows)
    metod.html            framing, register, immutable files in git, sources and licences, not investment advice
    manadsbrev.html       the monthly letters (docs/manadsbrev/*.md, ai_tracker.letter), newest first, and one page
                          per letter (manadsbrev-<YYYY-MM>.html) rendered from its Markdown
    data/*.json           the data each page draws its charts from
    assets/style.css, assets/app.js   no external hosts: charts are inline SVG drawn by app.js

Record. Live snapshots (snapshots/<YYYY-MM>.json, written by the monthly routine) are the record once they exist.
Before the first one, and for the months before it, the state is reconstructed with the same code at each month end
(as_of the month end, today's table) and labelled "rekonstruerad historik, inte ett skarpt underlag".

Licences. Only series with Spec.publish=True (a derived series: every component) are shown with values. A withheld
series (publish=False) still counts in its branch's index, as registered; the site then shows the branch-level
aggregates only and names the withheld series and why. Nothing else about them reaches the output.

The build fails (exit 1, nothing written) if the warehouse checks fail.
"""
