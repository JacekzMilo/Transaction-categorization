import { google } from 'googleapis';
import { Storage } from '@google-cloud/storage';
import fetch from 'node-fetch';
import { getNordigenToken } from './nordigenAuth.mjs';

export default async (req, res) => {
  try {
    console.log("Received request:", req.method, req.url);
    console.log("Request headers:", req.headers);
    console.log("Request body:", req.body);

    const { action, bank } = req.body;
    const bucketName = "bank_data_milo";
    const credentials = JSON.parse(process.env.SERVICE_ACCOUNT_JSON);
    const storage = new Storage({ credentials });
    const bucket = storage.bucket(bucketName);
    const bankIdentifiers = {
      mbank: 'MBANK_RETAIL_BREXPLPW',
      pko: 'PKO_BPKOPLPW'
    };

    if (!req.body) {
      return res.status(400).json({ error: 'No request body provided' });
    }

    if (!action || (action !== 'sync_all' && !bank)) {
      return res.status(400).json({ error: 'Invalid "action" or "bank" specified' });
    }

    if (action === 'sync_all') {
      const banks = Object.keys(bankIdentifiers);
      const results = await Promise.allSettled(banks.map(bank => processBank(bank, bankIdentifiers[bank], bucket)));
      const messages = results.map(result => result.status === 'fulfilled' ? result.value : `Error: ${result.reason}`);
      res.status(200).json({ message: messages });
    } else if (action === 'results' && bank && bankIdentifiers[bank]) {
      console.log(`Processing bank: ${bank}`);
      try {
        const result = await processBank(bank, bankIdentifiers[bank], bucket);
        res.status(200).json({ message: result });
      } catch (error) {
        res.status(500).json({ error: `Error processing bank ${bank}: ${error.message}` });
      }
    } else {
      res.status(400).json({ error: 'Invalid action or bank specified' });
    }
  } catch (error) {
    console.error("Error processing request:", error);
    res.status(500).json({ error: 'Internal Server Error' });
  }
};

const processBank = async (bank, institutionId, bucket) => {
  try {
    const reqId = process.env[`COOKIE_NAME_${bank.toUpperCase()}`];
    if (!reqId) {
      console.warn(`No requisition ID found for ${bank}`);
      return `No requisition ID found for ${bank}`;
    }

    const nordigenAccessToken = await getNordigenToken();

    const accountsResponse = await fetch(`https://ob.nordigen.com/api/v2/requisitions/${reqId}/`, {
      headers: {
        'Authorization': `Bearer ${nordigenAccessToken}`,
        'Accept': 'application/json'
      }
    });

    if (!accountsResponse.ok) {
      console.error(`Failed to fetch accounts for ${bank}:`, accountsResponse.status, accountsResponse.statusText);
      return `Failed to fetch accounts for ${bank}: ${accountsResponse.statusText}`;
    }

    const accountsData = await accountsResponse.json();
    console.log(`accountsData for ${bank}:`, accountsData);

    // Sprawdzenie, czy req_id wygasło
    if (accountsResponse.status === 400 && accountsData.error === 'Requisition ID has expired') {
      console.warn('req_id has expired');
      return 'Twoja autoryzacja wygasła. Proszę ponownie autoryzować, aby kontynuować.';
    }

    if (!accountsData.accounts) {
      console.warn(`No accounts found for requisition ID ${reqId}`);
      return `No accounts found for ${bank}`;
    }

    const accounts = accountsData.accounts;
    const bankData = [];

    for (const id of accounts) {
      console.log(`Fetching account details, transactions, and balances for ${id}`);

      const [accountData, transactions, balances, details] = await Promise.all([
        fetch(`https://ob.nordigen.com/api/v2/accounts/${id}/`, {
          headers: {
            'Authorization': `Bearer ${nordigenAccessToken}`,
            'Accept': 'application/json'
          }
        }).then(response => response.json()),
        fetch(`https://ob.nordigen.com/api/v2/accounts/${id}/transactions/`, {
          headers: {
            'Authorization': `Bearer ${nordigenAccessToken}`,
            'Accept': 'application/json'
          }
        }).then(response => response.json()),
        fetch(`https://ob.nordigen.com/api/v2/accounts/${id}/balances/`, {
          headers: {
            'Authorization': `Bearer ${nordigenAccessToken}`,
            'Accept': 'application/json'
          }
        }).then(response => response.json()),
        fetch(`https://ob.nordigen.com/api/v2/accounts/${id}/details/`, {
          headers: {
            'Authorization': `Bearer ${nordigenAccessToken}`,
            'Accept': 'application/json'
          }
        }).then(response => response.json())
      ]);

      if (!accountData || !transactions || !balances || !details) {
        console.warn(`Incomplete data for account ${id}`);
        continue;
      }

      console.log(`Fetched account details for ${id}:`, accountData);
      console.log(`Fetched transactions for ${id}:`, transactions);
      console.log(`Fetched balances for ${id}:`, balances);
      console.log(`Fetched account details for ${id}:`, details);

      if (transactions.transactions && transactions.transactions.booked && transactions.transactions.booked.length > 0) {
        bankData.push({
          metadata: {
            id: accountData.id,
            created: accountData.created,
            last_accessed: accountData.last_accessed,
            iban: accountData.iban,
            institution_id: accountData.institution_id,
            status: accountData.status,
            owner_name: accountData.owner_name
          },
          details: details || {},
          balances: balances || {},
          transactions: {
            transactions: {
              booked: transactions.transactions.booked || []
            }
          }
        });
      } else {
        console.warn(`No booked transactions found for account ${id}`);
      }
    }

    if (bankData.length > 0) {
      const user = {
        user_name: 'Jacek',
        user_last_name: 'Milo',
        user_email: 'majlojacek@gmail.com',
        user_full_name: 'Jacek Milo',
        institution: institutionId || 'default_value'
      };

      bankData.push(user);

      const blobName = `${user.user_full_name} ${institutionId}.json`;
      const file = bucket.file(blobName);

      await file.save(JSON.stringify(bankData, null, 2), {
        contentType: 'application/json',
      });

      console.log(`File ${blobName} uploaded successfully.`);
      return `Data for ${bank} uploaded successfully.`;
    } else {
      console.warn(`No data to upload for bank ${bank}.`);
      return `No data to upload for ${bank}. Possible reason: no booked transactions available.`;
    }
  } catch (error) {
    console.error(`Error processing bank ${bank}:`, error);
    return `Error processing bank ${bank}: ${error.message}`;
  }
};
