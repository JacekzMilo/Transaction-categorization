import functions_framework
import json
from google.cloud import storage
import xlsxwriter
import regex as re
import pandas as pd
import numpy as np
from google.cloud import bigquery


"""
Bank Data Processing.

This script is designed to process Bank transaction data stored in a Google Cloud Storage bucket.
The data is processed and loaded into a BigQuery table. The script contains functions for extracting
and transforming data, assigning categories to transactions, and loading the data into BigQuery.

Functions:
- worksheet_generator(): Initializes an Excel workbook for data storage.
- create_categories_mapping(): Creates a mapping of transaction categories based on predefined patterns.
- assign_category(description, category_mapping): Assigns a category to a transaction based on its description.
- load(df): Loads the DataFrame into a BigQuery table.
- extractor(file, filename, quantity, category_mapping): Extracts data from a JSON file, processes it,
  and returns a DataFrame.

The main function, function(data, context), processes multiple files, extracts data from them, assigns categories,
concatenates DataFrames, and loads the final DataFrame into a BigQuery table.

Note: The script assumes a specific structure of the JSON data and Excel workbook.

Args:
- data (dict): Cloud Function data representing the event that triggered the function.
- context (google.cloud.functions.Context): Cloud Function execution context.

Returns:
- None
"""


# Triggered by a change in a storage bucket
@functions_framework.cloud_event
def worksheet_generator():
    workbook = xlsxwriter.Workbook('Jacek.xlsx')
    worksheet = workbook.add_worksheet()

    worksheet.write('A1', 'date_time')
    worksheet.write('B1', 'currency')
    worksheet.write('C1', 'amount')
    worksheet.write('D1', 'descritpion')
    worksheet.write('E1', 'institution')

    return worksheet, workbook


def create_categories_mapping():
    category_mapping = {
        'Zakupy życiowe': ['Allegro', 'HERBALIFE', 'LIDL', 'CARREFOUR', 'ROSSMANN', 'ZABKA', 'PIWARIUM', 'Kancelaria',
                           'JMP', 'Top', 'BADYLARNIA'],
        'Subskrypcje': ['PAYPAL', 'GOOGLE', 'NETFLIX.COM', 'HEROKU*', 'DISNEY'],
        'Jedzenie/picie': ['PP*RESTAUMATIC.COM', 'WILCZA', 'RESTAURACJA', 'PIZZA', 'XIN', 'BUTCHERY', 'GREEN',
                           'PIJALNIA'],
        'Transport': ['BOLT', 'Stacja', 'CIRCLE', 'SPP', 'Parking'],
        'Zdrowie': ['MOKOT.FUND.WARSZAWIANKA', 'APTEKA', 'PORADNIA', 'CEFARM-WARSZAWA', 'OSIR', 'PSYCHIATRZY.WARSZAWA'],
        'Zakupy internetowe': ['PayPro', 'Elfi.pl', 'KUBUS', 'EVENTIM.PL-PL-ECOM', 'AVANS.PL', 'PAYPAL *ZALANDOSE'],
        'Inne': ['UBEZP.', 'SPŁATA', 'ZWROT', 'HB', 'ODSETKI']
    }

    return category_mapping


def assign_category(description, category_mapping):
    for category, patterns in category_mapping.items():
        for pattern in patterns:
            if re.search(pattern, description, flags=re.IGNORECASE):
                return category
    return 'Inne'


def load(df):
    client = bigquery.Client()
    project = client.project

    dataset_id = 'bankData'
    table_id = 'bank_data_table'
    dataset_ref = client.dataset(dataset_id)
    table_ref = dataset_ref.table(table_id)

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,  # lub inny format wspierany przez BigQuery
        write_disposition=bigquery.WriteDisposition.WRITE_TRUNCATE,
        autodetect=True
    )

    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)

    job.result()  # Czekaj na zakończenie ładowania danych

    print("Loaded {} rows.".format(job.output_rows))


def extractor(file, filename, quantity, category_mapping):
    worksheet, workbook = worksheet_generator()
    position = 0
    data = file[0]

    for position, key in enumerate(data['transactions']['transactions']['booked'][:]):
        for name in key.keys():

            if name == 'bookingDate':
                try:
                    __transaction_date = data['transactions']['transactions']['booked'][position][name]
                    worksheet.write(position + 1, 0, __transaction_date)
                except:
                    pass

            if name == 'transactionAmount':
                try:
                    __amount = data['transactions']['transactions']['booked'][position][name]['amount']
                    __currency = data['transactions']['transactions']['booked'][position][name]['currency']
                    worksheet.write(position + 1, 2, __amount)
                    worksheet.write(position + 1, 1, __currency)
                except:
                    pass

            if name == 'remittanceInformationUnstructured':
                try:
                    __counter_party_name = data['transactions']['transactions']['booked'][position][name]
                    worksheet.write(position + 1, 3, __counter_party_name)

                except:
                    pass
            if data['metadata']['institution_id'] == "PKO_BPKOPLPW":
                worksheet.write(position + 1, 4, "PKO_BPKOPLPW")
            else:
                worksheet.write(position + 1, 4, "MBANK_RETAIL_BREXPLPW")

    suma = position + 1
    print("This many transactions:", suma)
    print("This many files:", quantity)

    workbook.close()

    df = pd.read_excel('Jacek.xlsx', engine='openpyxl')

    df["labell"] = np.nan

    for possition, el in enumerate(df['descritpion']):
        df.loc[possition, 'labell'] = assign_category(el, category_mapping)
    try:
        df = df.drop('Unnamed: 0', axis=1)
    except:
        pass

    return df


def function(data, context):
    bucket_name = "bucket_name"
    file_names = ["file PKO_BPKOPLPW.json", "file MBANK_RETAIL_BREXPLPW.json"]
    client = storage.Client(project='gcp-project')

    dfs_to_concat = []
    bucket = client.get_bucket(bucket_name)
    for file in file_names:

        blob = bucket.blob(file)

        file_content = blob.download_as_text()

        data = json.loads(file_content)

        categories_mapping = create_categories_mapping()

        df = extractor(data, "Jacek", 1, category_mapping=categories_mapping)
        dfs_to_concat.append(df)
        df_final = pd.concat(dfs_to_concat, ignore_index=True)

        load(df_final)