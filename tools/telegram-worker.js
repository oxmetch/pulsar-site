// Cloudflare Worker: receives the contact form from pulsar-ai.co and posts it to Telegram.
// The bot token never reaches the browser — it lives in the Worker's secrets.
//
// Worker settings → Variables and Secrets:
//   BOT_TOKEN  (secret)  token from @BotFather
//   CHAT_ID    (text)    chat to post to; several allowed, comma-separated
//
// Paste this file into the Worker editor (Cloudflare dashboard → Workers → Edit code) and Deploy.

const ALLOWED_ORIGINS = [
  'https://pulsar-ai.co',
  'https://www.pulsar-ai.co',
  'http://localhost:8080',
];

const LIMITS = { name: 120, company: 160, contact: 160, language: 8, message: 3000 };

export default {
  async fetch(request, env) {
    const origin = request.headers.get('Origin') || '';
    const cors = {
      'Access-Control-Allow-Origin': ALLOWED_ORIGINS.includes(origin) ? origin : ALLOWED_ORIGINS[0],
      'Access-Control-Allow-Methods': 'POST, OPTIONS',
      'Access-Control-Allow-Headers': 'Content-Type',
      Vary: 'Origin',
    };
    const reply = (status, body) =>
      new Response(JSON.stringify(body), { status, headers: { ...cors, 'Content-Type': 'application/json' } });

    if (request.method === 'OPTIONS') return new Response(null, { status: 204, headers: cors });
    if (request.method !== 'POST') return reply(405, { success: false, message: 'Method not allowed' });
    if (!ALLOWED_ORIGINS.includes(origin)) return reply(403, { success: false, message: 'Forbidden' });

    let data;
    try {
      data = await request.json();
    } catch {
      return reply(400, { success: false, message: 'Bad request' });
    }
    if (data._gotcha) return reply(200, { success: true }); // honeypot: pretend it worked

    const field = (key) => String(data[key] ?? '').trim().slice(0, LIMITS[key]);
    const lead = Object.fromEntries(Object.keys(LIMITS).map((key) => [key, field(key)]));
    if (!lead.name || !lead.contact) return reply(400, { success: false, message: 'Name and contact are required' });

    const esc = (s) => s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
    const text = [
      '<b>New request from pulsar-ai.co</b>',
      '',
      `<b>Name:</b> ${esc(lead.name)}`,
      `<b>Company:</b> ${esc(lead.company || '—')}`,
      `<b>Contact:</b> ${esc(lead.contact)}`,
      `<b>Language:</b> ${esc(lead.language || '—')}`,
      '',
      esc(lead.message || '—'),
    ].join('\n');

    const chats = String(env.CHAT_ID || '').split(',').map((id) => id.trim()).filter(Boolean);
    if (!env.BOT_TOKEN || !chats.length) return reply(500, { success: false, message: 'Worker is not configured' });

    const results = await Promise.all(
      chats.map((chat_id) =>
        fetch(`https://api.telegram.org/bot${env.BOT_TOKEN}/sendMessage`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ chat_id, text, parse_mode: 'HTML', disable_web_page_preview: true }),
        }).then((res) => res.ok)
      )
    );
    return results.some(Boolean)
      ? reply(200, { success: true })
      : reply(502, { success: false, message: 'Telegram did not accept the message' });
  },
};
