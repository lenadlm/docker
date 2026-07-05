# Pointers to the two-job update pattern

The old "deliver-before-restart" pattern using `hermes send` has been replaced by the **two-job architecture**.

See `references/hermes-update-two-job-pattern.md` for:

- The two-job design (00:00 update + 00:15 report)
- Why `hermes update --yes` must never share a cron job with its report delivery
- SHA tracking via `hermes_version_track.json`
- The report script detection logic