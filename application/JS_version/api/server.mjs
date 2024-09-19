import dotenv from 'dotenv';
import express from 'express';
import fetch from 'node-fetch';
import fetchData from './fetchData.mjs'; // Importowanie modułu

dotenv.config();

const app = express();

// Użycie fetchData jako middleware lub route
app.post('/api/fetch-data', fetchData);

// Funkcja do generowania nowego Bearer Tokena
async function generateNewToken(secretId, secretKey) {
    const response = await fetch('https://bankaccountdata.gocardless.com/api/v2/token/new/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({ secret_id: secretId, secret_key: secretKey })
    });

    const data = await response.json();

    if (response.status !== 200) {
        console.error('Failed to generate token:', data);
        throw new Error('Failed to generate token');
    }

    return data.access; // Zwracamy Bearer Token
}

// Funkcja do pobierania daty utworzenia req_id
async function getReqIdCreationDate(token, reqId) {
    console.log('Fetching creation date for reqId:', reqId);
//     console.log('Fetching creation date for token:', token);

    const response = await fetch(`https://bankaccountdata.gocardless.com/api/v2/requisitions/${reqId}/`, {
        headers: { 'Authorization': `Bearer ${token}` }
    });

    const data = await response.json();
    console.log('API Response:', data);
    if (data.created) {
        return data.created;
    } else {
        console.error('Creation date not found in API response:', data);
        return null;
    }
}

// Funkcja do uzyskania ID instytucji bankowej na podstawie nazwy banku
function getInstitutionId(bankName) {
    const bankIdentifiers = {
        mbank: 'MBANK_RETAIL_BREXPLPW',
        pko: 'PKO_BPKOPLPW'
    };
    return bankIdentifiers[bankName.toLowerCase()];
}

// Funkcja do tworzenia nowej umowy dla użytkownika końcowego
async function createEndUserAgreement(token, institutionId) {
    const response = await fetch('https://bankaccountdata.gocardless.com/api/v2/agreements/enduser/', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            institution_id: institutionId,
            access_valid_for_days: 180
        })
    });

    const data = await response.json();
    return data.id;
}

// Funkcja do tworzenia requisition i uzyskania linku autoryzacyjnego
async function createRequisition(token, agreementId, redirectUrl) {
    const response = await fetch('https://bankaccountdata.gocardless.com/api/v2/requisitions/', {
        method: 'POST',
        headers: {
            'Authorization': `Bearer ${token}`,
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            agreement: agreementId,
            redirect: redirectUrl  // URL na który użytkownik ma zostać przekierowany po autoryzacji
        })
    });

    const data = await response.json();
    return data.link;  // Zwróć link do autoryzacji
}

app.post('/api/refresh-req-id', async (req, res) => {
    try {
        const secretId = process.env.SECRET_ID;
        const secretKey = process.env.SECRET_KEY;
        const redirectUrl = process.env.REDIRECT_URL;
        const bankName = req.body.bankName;

        const token = await generateNewToken(secretId, secretKey);
        const institutionId = getInstitutionId(bankName);

        if (!institutionId) {
            throw new Error('Nieznana nazwa banku');
        }

        const agreementId = await createEndUserAgreement(token, institutionId);
        const requisitionLink = await createRequisition(token, agreementId, redirectUrl);

        // Zwróć link do autoryzacji, który należy otworzyć w przeglądarce
        res.json({ requisitionLink });

    } catch (error) {
        console.error('Błąd podczas odświeżania req_id:', error);
        res.status(500).json({ error: 'Błąd podczas odświeżania req_id' });
    }
});

app.get('/api/req-id-status', async (req, res) => {
    try {
        const secretId = process.env.SECRET_ID;
        const secretKey = process.env.SECRET_KEY;
        const reqIdMBank = process.env.COOKIE_NAME_MBANK;
        const reqIdPKO = process.env.COOKIE_NAME_PKO;

        const token = await generateNewToken(secretId, secretKey);

        const mbankCreationDate = await getReqIdCreationDate(token, reqIdMBank);
        const pkoCreationDate = await getReqIdCreationDate(token, reqIdPKO);

        const mbankDaysRemaining = calculateDaysRemaining(mbankCreationDate);
        const pkoDaysRemaining = calculateDaysRemaining(pkoCreationDate);

        res.json({ mbankDaysRemaining, pkoDaysRemaining });
        } catch (error) {
            console.error('Błąd podczas pobierania statusu req_id:', error);
            res.status(500).json({ error: 'Failed to retrieve req_id status' });
        }
});

function calculateDaysRemaining(creationDate) {
    const createdDate = new Date(creationDate);
    console.log(`Server createdDate ${createdDate}`);
    const currentDate = new Date();
    console.log(`Server currentDate ${currentDate}`);
    const timeDifference = currentDate - createdDate;
    console.log(`Server timeDifference ${timeDifference}`);
    console.log(`Server timeDifference ${timeDifference}`);
    const delta = 90 - Math.floor(timeDifference / (1000 * 60 * 60 * 24))
    console.log(`Server delta ${delta}`);


    return 90 - Math.floor(timeDifference / (1000 * 60 * 60 * 24));
}

// Export app for use in other files or server setup
export default app;

// Uruchomienie serwera
const PORT = process.env.PORT || 3000;
app.listen(PORT, () => {
    console.log(`Server is running on port ${PORT}`);
});
