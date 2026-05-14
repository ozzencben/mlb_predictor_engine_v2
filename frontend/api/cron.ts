import type { VercelRequest, VercelResponse } from '@vercel/node';

export default async function handler(
  request: VercelRequest,
  response: VercelResponse,
) {
  // Vercel Cron jobs use GET by default
  if (request.method !== 'GET') {
    return response.status(405).json({ error: 'Method not allowed' });
  }

  // 1. Check Vercel Cron authorization
  const authHeader = request.headers.authorization;
  if (authHeader !== `Bearer ${process.env.CRON_SECRET}`) {
    return response.status(401).send('Geçersiz Vercel Yetkisi');
  }

  try {

    const renderUrl = `${process.env.VITE_API_URL}/api/v1/cron/refresh`;

    const renderResponse = await fetch(renderUrl, {
      method: 'GET',
      headers: {
        'Authorization': `Bearer ${process.env.CRON_SECRET}`,
      },
    });

    const data = await renderResponse.json();

    // Return the response from Render for Vercel logs
    return response.status(renderResponse.status).json(data);

  } catch (error) {
    console.error('Render tetiklenirken hata oluştu:', error);
    return response.status(500).json({ error: 'Backend (Render) ulaşılamaz durumda' });
  }
}
