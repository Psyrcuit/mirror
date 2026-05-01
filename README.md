# Mirror

> A vision-model personality identikit. Upload a photo of your bookshelf, desk, or workspace; get back a playful reading of who you might be based on what's visible.

**Live demo:** https://mirror.psyrcuit.com

## What it does

You drag in a photo. A vision model (Claude Opus 4.7, with GPT-4o as fallback) examines the visible objects — books, desk items, posters, the general aesthetic — and returns:

- 5 personality traits inferred from the scene
- A 3-4 sentence synthesis weaving them together
- A one-line "vibe" summary

It's entertainment, not assessment. The output is meant to be playful and shareable, not diagnostic.

## Why this exists

Built as Build 1 of 7 in a 90-day public AI demo portfolio focused on AI legibility and personal-corpus tooling. Mirror is the cheap, shareable opener — it demonstrates vision-API competence in something other than the usual "object detection" demo, and the output is screenshot-bait by design.

## How to run it locally

The project is pure static HTML + a single Cloudflare Pages Function — no build step, no `package.json`, no bundler.

```bash
git clone https://github.com/psyrcuit/mirror
cd mirror
cp .dev.vars.example .dev.vars
# Add your ANTHROPIC_API_KEY and OPENAI_API_KEY to .dev.vars
npx wrangler@latest pages dev .
# Open http://localhost:8788
```

`npx wrangler` will fetch a one-shot copy of Wrangler at run time — nothing gets installed into the repo. If you don't want any Node tooling at all, you can deploy the repo to Cloudflare Pages via the Git integration and skip the local dev server entirely.

You'll need:
- An Anthropic API key (for the primary vision call)
- An OpenAI API key (for the fallback path)
- Node.js (only if you want `npx wrangler` for local dev — not required for deploy)

## Architecture (one-line summary)

Single static HTML page served from Cloudflare Pages. Browser uploads image, hits a Pages Function, function calls vision API with a structured-output personality prompt, returns JSON, browser renders the card. Nothing stored server-side. Two-layer rate limiting (per-IP + global daily cap) via Cloudflare Workers KV.

## Honest limitations

- **It's not actually reading your personality.** It's reading the scene and producing a playful inference. Don't make life decisions based on it.
- **Output quality varies wildly with image quality.** Blurry, empty, or person-dominated photos produce weak readings. Bookshelf-with-many-books works best.
- **Anglocentric bias.** The vision model recognizes Western book covers and aesthetic markers more reliably than non-Western ones. Working on it.
- **Single-language output.** English only in v1.
- **Rate limited per IP.** 5 requests per IP per hour. If the demo is getting hammered, you'll see a 429.
- **Globally rate limited.** Total 100 requests/day across all visitors. If the daily cap is hit, the demo returns a friendly 503 until midnight UTC. Cost discipline > availability for a demo.
- **No image storage.** This is intentional (privacy), but it means there's no "share this specific reading" URL — you have to screenshot/PNG-export the card to share.
- **Costs money to run.** Each call hits the Anthropic API. Self-hosting will burn through your API credits if you make Mirror public without rate limits in place. The daily cap protects you from runaway spend; don't disable it without thinking through the consequences.

## Privacy

- Your image is sent to Anthropic's API (or OpenAI's, on fallback). Subject to those providers' data policies.
- Nothing is stored on the Mirror server. No database, no logs of image content.
- Cloudflare's standard request logs may temporarily retain IP + timestamp for rate limiting purposes.
- The IP-based rate limiter uses Cloudflare Workers KV with a 1-hour TTL. The daily cap counter has a 24-hour TTL.
- IPs are stored hashed (not raw) in the KV namespace to reduce identifiability of the audit trail.

## Self-hosting cost (if you fork and deploy your own)

- Cloudflare Pages: free (unlimited bandwidth, unlimited static-asset requests)
- Cloudflare Workers KV: free at this scale (well under the 100k reads/day, 1k writes/day free tier)
- Custom subdomain via Cloudflare DNS: free if you already have a domain on Cloudflare
- API spend: bounded by your daily cap configuration. Default is 100 Opus 4.7 calls/day at ~$0.024/call ≈ $2.40/day max (worst case ~$4.80 if every call also triggers the strict-retry path). Adjust `DAILY_CAP` in `functions/api/analyze.js` if you want a different ceiling.

Total fixed cost: $0/month plus your API spend.

## License

MIT. Build derivative versions, fork, run your own. Pull requests welcome but no commitment to merge.

## What's next

Possible v2 directions (not committed):
- Side-by-side comparison mode (your bookshelf vs. someone else's)
- Custom prompts ("make it brutally honest" / "make it generous")
- Multi-image upload (multiple angles of the same room)
- Self-hosted OSS deployment guide
- Cloudflare AI Gateway integration for additional spend visibility

If any of these would be useful to you, open an issue and tell me why — that's how the priorities get set.

---

Built with [Claude Code](https://www.claude.com/code). Part of [Chase Lance's 90-day AI demo portfolio](https://psyrcuit.com/portfolio).
