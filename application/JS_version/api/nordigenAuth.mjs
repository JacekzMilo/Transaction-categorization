import fetch from 'node-fetch';

async function getNordigenToken() {
  const clientId = process.env.NORDIGEN_CLIENT_ID;
  const clientSecret = process.env.NORDIGEN_CLIENT_SECRET;
  const tokenUrl = 'https://ob.nordigen.com/api/v2/token/new/';

  console.log("Requesting Nordigen token with clientId:", clientId);

  try {
    const response = await fetch(tokenUrl, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/x-www-form-urlencoded'
      },
      body: new URLSearchParams({
        secret_id: clientId,
        secret_key: clientSecret
      })
    });

    if (!response.ok) {
      const errorText = await response.text();
      console.error("Error response from Nordigen:", errorText);
      throw new Error('Failed to fetch Nordigen token');
    }

    const data = await response.json();
    console.log("Received token data:", data);
    return data.access;
  } catch (error) {
    console.error("Error while fetching Nordigen token:", error);
    throw error;
  }
}

export { getNordigenToken };
