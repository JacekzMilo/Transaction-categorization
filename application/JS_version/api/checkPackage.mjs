// api/checkPackage.mjs
import { google } from 'googleapis';

export default async (req, res) => {
  try {
    if (google) {
      res.status(200).json({ message: 'Package googleapis is installed.' });
    }
  } catch (error) {
    res.status(500).json({ message: 'Package googleapis is not installed.', error: error.message });
  }
};
