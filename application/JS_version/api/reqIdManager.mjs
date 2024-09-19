// Funkcja do generowania nowego tokena
export async function generateNewToken(secretId, secretKey) {
    const url = 'https://bankaccountdata.gocardless.com/api/v2/token/new/';
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json'
        },
        body: JSON.stringify({
            secret_id: secretId,
            secret_key: secretKey
        })
    });

    const data = await response.json();
    return data.token;  // Zwróć nowy token
}

// Funkcja do uzyskania ID instytucji bankowej na podstawie nazwy banku
export function getInstitutionId(bankName) {
    const bankIdentifiers = {
        mbank: 'MBANK_RETAIL_BREXPLPW',
        pko: 'PKO_BPKOPLPW'
    };

    return bankIdentifiers[bankName.toLowerCase()];
}

// Funkcja do tworzenia nowej umowy dla użytkownika końcowego
export async function createEndUserAgreement(token, institutionId) {
    const url = 'https://bankaccountdata.gocardless.com/api/v2/agreements/enduser/';
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            institution_id: institutionId,
            access_valid_for_days: 180
        })
    });

    const data = await response.json();
    return data.id;  // Zwróć id nowej umowy
}

// Funkcja do tworzenia requisition i uzyskania linku autoryzacyjnego
export async function createRequisition(token, agreementId, redirectUrl) {
    const url = 'https://bankaccountdata.gocardless.com/api/v2/requisitions/';
    const response = await fetch(url, {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'Authorization': `Bearer ${token}`
        },
        body: JSON.stringify({
            agreement: agreementId,
            redirect: redirectUrl  // URL na który użytkownik ma zostać przekierowany po autoryzacji
        })
    });

    const data = await response.json();
    return data.link;  // Zwróć link do autoryzacji
}

// Główna funkcja odświeżania req_id
export async function refreshReqId(secretId, secretKey, bankName, redirectUrl) {
    try {
        const token = await generateNewToken(secretId, secretKey);
        const institutionId = getInstitutionId(bankName);

        if (!institutionId) {
            throw new Error('Nieznana nazwa banku');
        }

        const agreementId = await createEndUserAgreement(token, institutionId);
        const requisitionLink = await createRequisition(token, agreementId, redirectUrl);

        // Zwróć link do autoryzacji, który należy otworzyć w przeglądarce
        return requisitionLink;

    } catch (error) {
        console.error('Błąd podczas odświeżania req_id:', error);
        throw error;
    }
}
