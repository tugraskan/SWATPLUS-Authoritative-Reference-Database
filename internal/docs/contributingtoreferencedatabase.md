# Contributing to the reference database from the editor

The SWAT+ Editor can propose changes to the
[SWATPLUS-Authoritative-Reference-Database](https://github.com/tugraskan/SWATPLUS-Authoritative-Reference-Database)
directly from your project, without touching git. This document covers that
path. For the manual branch and pull-request workflow, see that repository's
own `CONTRIBUTING.md`.

## What it does

You pick records from your project's database, a plant you added, a
fertilizer value you tuned, and the editor formats them exactly as the
reference database stores them, checks them, and opens a pull request. You
never write a git command or touch the reference repository directly.

## Before you start

Sign in to GitHub once, from inside the dialog. Two ways:

- **Device flow**: click "Sign in with GitHub", approve a short code in
  your browser. Only available if this build has an OAuth app configured.
- **Personal access token**: paste one with the `public_repo` scope.

## Step by step

1. **Help &rarr; Contribute Records to the Reference Database.**

   ![Help page with the Contribute Records to the Reference Database link](images/help-page-contribute-link.png)

2. **Pick a table, then records.** The table dropdown only lists tables
   that actually have something changed, with a count next to each, for
   example `Urban (4)`. Pick one or more records and select **Add** to
   stage them. Repeat across as many tables as you like, they can all go
   out together.

   This filtered view is the default because most of a project is stock
   data nobody touched. It compares against the editor's own bundled
   defaults, not the live reference database, so it can occasionally miss
   something or flag something you never meant to change. Use the
   "Browse everything instead" link if you want to see every record in a
   table regardless.

   ![Table dropdown scoped to changed tables, each with a record count](images/table-picker-with-counts.png)

3. **Review.** Each staged record shows what it will do:

   - **New**: the name doesn't exist in the reference database yet.
   - **Update**: the name exists there with different values. The current
     line is shown above the proposed one so you can see exactly what
     changes.

   Anything invalid, a blank name, a non-numeric value in a numeric
   column, a name already staged twice, is flagged here, before anything
   is sent anywhere.

   ![Review screen showing a New record and an Update record, with the before/after diff and the pull request title that will be used](images/review-screen.png)

4. **Add context.** Reason, source, and notes are all optional, and shown
   to whoever reviews the pull request.

5. **Submit.** One pull request opens per file touched, not one combined
   PR. A change to `plants.plt` and a change to `fertilizer.frt` become
   two separate, independently reviewable pull requests, even if you
   staged them in the same sitting.

## After you submit

You get a link to each pull request that opened. A reviewer on the
reference database decides whether to merge; opening the PR doesn't change
anything upstream by itself. If you don't have push access to the
reference database, the editor pushes to your own fork automatically and
opens the PR from there. That's the normal path for a contribution, not an
error.

If several pull requests were involved and one failed to open, for
example because the file changed upstream while you were reviewing, the
result screen still shows you which ones succeeded and which didn't,
rather than losing track of a partial submission.

## A caution on values

The editor's record forms show a "Recommended Range" next to each field,
but that's informational only. The forms don't stop you from saving
something outside it, or something with the wrong sign entirely:

![Fertilizer edit form with a Recommended Range column that is purely informational, not enforced](images/recommended-range-column.png)

The submission dialog only checks that a value is numeric, not that it's
plausible. Sanity-check anything you're about to submit: a value like
`bm_e = -2` (recommended range 10 to 90) currently goes through without a
warning at either stage.

![Plants grid showing a record with bm_e set to -2, saved without any warning](images/out-of-range-value-saved.png)
