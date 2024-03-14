# Transaction insight

The goal was to gain insight into spending divided into categories. Final Data Studio dashboard shows data separately for each bank and combined into one plot. The flow is using two python scripts - application (app.py) and Cloud Function code. Cloud Function code is designed to process Bank data stored in a Google Cloud Storage bucket. It reacts to changes in the bucket, triggering the function whenever a file is overwritten. Works on multiple files from various banks. Application script is a user friendly frontend used to extract data from account.  

## GCP Cloud Function - Bank Data Processing

The main functionality of the Cloud Function includes:

1. **Data Extraction and Transformation**: The function extracts transaction data from JSON files, processes it, and stores it in an Excel workbook.

2. **Category Assignment**: Transactions are categorized based on predefined patterns. The `assign_category` function determines the category of each transaction.

3. **BigQuery Integration**: Processed data is loaded into a BigQuery table. The `load` function takes care of this step.

4. **Data Studio Integration**: After loading data into BigQuery, Data Studio dashboard is automatically updated. This provides real-time insights into the processed bank data.

## Application - Bank Data Uploader

The bank data is delivered to Google Cloud Storage using the `app.py` application. Here are key points about the application:

- **Hosted on Vercel**: The application is hosted on Vercel (vercel.com), a platform for hosting web applications.

- **Integration with Nordigen**: The application uses the Nordigen connector as a mediator to access banking APIs. It leverages Nordigen's template code and APIs for interacting with various banks.

- **HTML Pages**: The application includes HTML pages for user interaction and data presentation. These pages are designed to provide a user-friendly experience for uploading bank data.

## Folder Structure

- **application**: Contains frontend code, including `app.py` for uploading bank data.
- **cloud_function**: Contains code for the Cloud Function responsible for data processing and loading into BigQuery.
- **ML**: Contains code for training the ML model used in the Cloud Function for categorizing transactions.

## Deployment

- **Cloud Function Deployment**: Deploy the Cloud Function on Google Cloud Platform. The function is triggered on bucket changes.

- **Vercel Deployment**: The application is deployed on Vercel. Ensure that the application's environment variables and configurations are set appropriately.

## Usage

1. **Uploading Bank Data**: Use the application to upload bank data. The data is delivered to the Cloud Storage bucket.

2. **Automated Processing**: The Cloud Function automatically triggers when data changes in the bucket. It processes the data, assigns categories, and loads it into BigQuery.

3. **Real-time Visualization**: The Data Studio dashboard provides real-time visualizations of the processed bank data.

## Prerequisites

- Google Cloud Platform account and project.
- Vercel account for hosting the application.
- Nordigen API key for banking data access.

## Configuration

Ensure to configure environment variables, API keys, and connection details in both the Cloud Function and the Vercel-hosted application.

## License

This project is licensed under the MIT License - see the [LICENSE](LICENSE) file for details.
