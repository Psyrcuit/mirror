// Mirror — vision API endpoint.
// Direct fetch to Anthropic + OpenAI (no SDKs) to keep the Pages Function
// bundle small and the runtime surface predictable.

const DAILY_CAP = 40;
const PER_IP_HOURLY_CAP = 5;
const MAX_BODY_BYTES = 2 * 1024 * 1024; // 2MB
const REQUEST_TIMEOUT_MS = 30_000;

const ANTHROPIC_MODEL = 'claude-opus-4-7';
const OPENAI_MODEL = 'gpt-4o';
const MAX_OUTPUT_TOKENS = 600;

const SYSTEM_PROMPT = `You are an expert at reading personality and aesthetic signals from visual environments. You will be shown a photo of someone's bookshelf, desk, or workspace. Return a playful but insightful personality identikit based ONLY on visible objects.

CRITICAL constraints:
- Never identify a real person by name, even if you see one in the photo
- Never infer or comment on race, gender, age, religion, sexuality, health conditions, or socioeconomic status
- Never reference any specific text on visible documents/mail/screens
- Stay observational and playful — this is entertainment, not assessment
- If the photo doesn't contain enough signal (blurry, empty room, or shows a person prominently), return a graceful refusal in the same schema

Return JSON in exactly this schema, with no additional prose, no markdown fences, no preamble:
{
  "traits": ["trait 1 (3-5 words)", "trait 2", "trait 3", "trait 4", "trait 5"],
  "synthesis": "one paragraph (3-4 sentences) weaving the traits into a coherent reading",
  "vibe": "one short line capturing the overall energy"
}`;

const STRICT_RETRY_NOTE = 'Your previous response did not match the required JSON schema. Return ONLY a valid JSON object matching the schema exactly. No preamble, no markdown fences, no commentary. Five traits, one synthesis paragraph, one vibe line.';

// ────────────────────────────────────────────────────────────
// Main handler
// ────────────────────────────────────────────────────────────

export async function onRequestPost(context) {
  const { request, env } = context;

  // 1. Body size pre-check via Content-Length
  const contentLength = parseInt(request.headers.get('content-length') || '0', 10);
  if (contentLength > MAX_BODY_BYTES) {
    return jsonResponse({ error: 'Image too large. Resize and try again.' }, 413);
  }

  // 2. Parse body
  let body;
  try {
    body = await request.json();
  } catch {
    return jsonResponse({ error: 'Invalid request body.' }, 400);
  }
  const { image_base64, mime_type } = body || {};
  if (!image_base64 || !mime_type) {
    return jsonResponse({ error: 'Missing image data.' }, 400);
  }
  if (!/^image\/(jpeg|png|webp)$/i.test(mime_type)) {
    return jsonResponse({ error: 'Unsupported image type.' }, 400);
  }

  // KV may be unbound during local dev or if binding is misconfigured —
  // fail open with a console warning rather than 500ing the whole request.
  if (!env.RATE_LIMIT_KV) {
    console.warn('RATE_LIMIT_KV not bound; rate limits skipped.');
  }

  // 3. Daily-cap check (global)
  const today = new Date().toISOString().slice(0, 10); // YYYY-MM-DD
  const dailyKey = `daily:${today}`;
  let dailyCount = 0;
  if (env.RATE_LIMIT_KV) {
    dailyCount = parseInt((await env.RATE_LIMIT_KV.get(dailyKey)) || '0', 10);
    if (dailyCount >= DAILY_CAP) {
      return jsonResponse({
        error: 'Demo paused for the day, resets midnight UTC.',
        reset: 'midnight UTC',
      }, 503);
    }
  }

  // 4. Per-IP-hour rate limit check
  const ip = request.headers.get('cf-connecting-ip') || 'unknown';
  const ipHashed = await hashIP(ip);
  const hourBucket = new Date().toISOString().slice(0, 13); // YYYY-MM-DDTHH
  const ipKey = `ip:${ipHashed}:${hourBucket}`;
  let ipCount = 0;
  if (env.RATE_LIMIT_KV) {
    ipCount = parseInt((await env.RATE_LIMIT_KV.get(ipKey)) || '0', 10);
    if (ipCount >= PER_IP_HOURLY_CAP) {
      return jsonResponse({
        error: 'You\'ve used your hourly limit. Try again later.',
        retry_after_minutes: 60,
      }, 429);
    }
  }

  // 5. Increment counters BEFORE the API call (fail-closed for cost safety)
  if (env.RATE_LIMIT_KV) {
    await Promise.all([
      env.RATE_LIMIT_KV.put(dailyKey, String(dailyCount + 1), { expirationTtl: 86400 }),
      env.RATE_LIMIT_KV.put(ipKey, String(ipCount + 1), { expirationTtl: 3600 }),
    ]);
  }

  // 6. Call Anthropic primary, OpenAI fallback
  let raw;
  try {
    raw = await callAnthropic(image_base64, mime_type, env.ANTHROPIC_API_KEY, false);
  } catch (err) {
    console.error('Anthropic call failed:', err && err.message);
    if (!env.OPENAI_API_KEY) {
      return jsonResponse({ error: 'Vision provider unavailable.' }, 503);
    }
    try {
      raw = await callOpenAI(image_base64, mime_type, env.OPENAI_API_KEY);
    } catch (err2) {
      console.error('OpenAI fallback also failed:', err2 && err2.message);
      return jsonResponse({ error: 'Both vision providers unavailable. Try again in a few minutes.' }, 503);
    }
  }

  // 7. Parse + validate schema
  let validated = parseAndValidate(raw);

  // 7b. One stricter retry on schema fail (Anthropic only — fallback path
  // already retried via try/catch above).
  if (!validated) {
    try {
      const retryRaw = await callAnthropic(image_base64, mime_type, env.ANTHROPIC_API_KEY, true);
      validated = parseAndValidate(retryRaw);
    } catch (err) {
      console.error('Schema retry failed:', err && err.message);
    }
  }

  if (!validated) {
    return jsonResponse({ error: 'Reading came back malformed. Try a different photo.' }, 502);
  }

  // 8. Post-process: strip likely real-person names as belt-and-suspenders defense
  const cleaned = stripPotentialNames(validated);

  return jsonResponse(cleaned, 200);
}

// ────────────────────────────────────────────────────────────
// Vision provider calls
// ────────────────────────────────────────────────────────────

async function callAnthropic(imageBase64, mimeType, apiKey, strict) {
  if (!apiKey) throw new Error('Missing ANTHROPIC_API_KEY');

  const userContent = [
    {
      type: 'image',
      source: {
        type: 'base64',
        media_type: mimeType,
        data: imageBase64,
      },
    },
  ];
  if (strict) {
    userContent.push({ type: 'text', text: STRICT_RETRY_NOTE });
  }

  const res = await fetchWithTimeout('https://api.anthropic.com/v1/messages', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      'x-api-key': apiKey,
      'anthropic-version': '2023-06-01',
    },
    body: JSON.stringify({
      model: ANTHROPIC_MODEL,
      max_tokens: MAX_OUTPUT_TOKENS,
      system: SYSTEM_PROMPT,
      messages: [{ role: 'user', content: userContent }],
    }),
  });

  if (!res.ok) {
    const errBody = await res.text().catch(() => '');
    throw new Error(`Anthropic ${res.status}: ${errBody.slice(0, 200)}`);
  }

  const data = await res.json();
  const block = (data.content || []).find((b) => b.type === 'text');
  return block ? block.text : '';
}

async function callOpenAI(imageBase64, mimeType, apiKey) {
  if (!apiKey) throw new Error('Missing OPENAI_API_KEY');

  const res = await fetchWithTimeout('https://api.openai.com/v1/chat/completions', {
    method: 'POST',
    headers: {
      'content-type': 'application/json',
      authorization: `Bearer ${apiKey}`,
    },
    body: JSON.stringify({
      model: OPENAI_MODEL,
      max_tokens: MAX_OUTPUT_TOKENS,
      response_format: { type: 'json_object' },
      messages: [
        { role: 'system', content: SYSTEM_PROMPT },
        {
          role: 'user',
          content: [
            {
              type: 'image_url',
              image_url: { url: `data:${mimeType};base64,${imageBase64}` },
            },
          ],
        },
      ],
    }),
  });

  if (!res.ok) {
    const errBody = await res.text().catch(() => '');
    throw new Error(`OpenAI ${res.status}: ${errBody.slice(0, 200)}`);
  }

  const data = await res.json();
  return data.choices?.[0]?.message?.content || '';
}

async function fetchWithTimeout(url, options) {
  const controller = new AbortController();
  const timeoutId = setTimeout(() => controller.abort(), REQUEST_TIMEOUT_MS);
  try {
    return await fetch(url, { ...options, signal: controller.signal });
  } finally {
    clearTimeout(timeoutId);
  }
}

// ────────────────────────────────────────────────────────────
// Schema validation + post-process
// ────────────────────────────────────────────────────────────

function parseAndValidate(raw) {
  if (!raw) return null;
  let text = String(raw).trim();
  text = text.replace(/^```(?:json)?\s*/i, '').replace(/\s*```$/, '').trim();

  if (!text.startsWith('{')) {
    const m = text.match(/\{[\s\S]*\}/);
    if (m) text = m[0];
  }

  let parsed;
  try {
    parsed = JSON.parse(text);
  } catch {
    return null;
  }

  if (!parsed || typeof parsed !== 'object') return null;
  if (!Array.isArray(parsed.traits) || parsed.traits.length !== 5) return null;
  if (parsed.traits.some((t) => typeof t !== 'string' || !t.trim())) return null;
  if (typeof parsed.synthesis !== 'string' || !parsed.synthesis.trim()) return null;
  if (typeof parsed.vibe !== 'string' || !parsed.vibe.trim()) return null;

  return {
    traits: parsed.traits.map((t) => t.trim()),
    synthesis: parsed.synthesis.trim(),
    vibe: parsed.vibe.trim(),
  };
}

const NAME_PATTERN = /\b[A-Z][a-z]+\s+[A-Z][a-z]+\b/g;
function stripPotentialNames(obj) {
  return {
    traits: obj.traits.map((t) => t.replace(NAME_PATTERN, '[name redacted]')),
    synthesis: obj.synthesis.replace(NAME_PATTERN, '[name redacted]'),
    vibe: obj.vibe.replace(NAME_PATTERN, '[name redacted]'),
  };
}

// ────────────────────────────────────────────────────────────
// Utilities
// ────────────────────────────────────────────────────────────

async function hashIP(ip) {
  const data = new TextEncoder().encode(ip);
  const digest = await crypto.subtle.digest('SHA-256', data);
  const hex = Array.from(new Uint8Array(digest))
    .map((b) => b.toString(16).padStart(2, '0'))
    .join('');
  return hex.slice(0, 16);
}

function jsonResponse(payload, status) {
  return new Response(JSON.stringify(payload), {
    status,
    headers: {
      'content-type': 'application/json; charset=utf-8',
      'cache-control': 'no-store',
    },
  });
}
