import functions_framework
import json
from google.cloud import storage
import xlsxwriter
import regex as re
import pandas as pd
import numpy as np
from io import BytesIO
import openpyxl
from google.cloud import bigquery
import pyarrow
import joblib
from datetime import datetime, timedelta, timezone
from google.cloud import bigquery


# Triggered by a change in a storage bucket
@functions_framework.cloud_event
def bank_millenium():
    workbook = xlsxwriter.Workbook('Jacek.xlsx')
    worksheet = workbook.add_worksheet()

    worksheet.write('A1', 'date_time')
    worksheet.write('B1', 'currency')
    worksheet.write('C1', 'amount')
    worksheet.write('D1', 'description')
    worksheet.write('E1', 'institution')

    return worksheet, workbook


def create_categories_mapping():
    """
    Function to create a mapping of categories based on patterns.
    Patterns are defined as a dictionary, where the key is the category name,
    and the value is a list of patterns matching that category.

    You can customize this function to load rules from an external configuration
    file or from some data source.
    """
    # category_mapping = {
    #     'Zakupy życiowe': ['Allegro', 'HERBALIFE', 'LIDL', 'CARREFOUR', 'ROSSMANN', 'ZABKA', 'PIWARIUM', 'Kancelaria', 'JMP', 'Top', 'BADYLARNIA', 'Leroy', 'ABUD'],
    #     'Subskrypcje': ['PAYPAL', 'GOOGLE', 'NETFLIX.COM', 'HEROKU*', 'DISNEY'],
    #     'Jedzenie/picie': ['PP*RESTAUMATIC.COM', 'WILCZA', 'RESTAURACJA', 'PIZZA', 'XIN', 'BUTCHERY', 'GREEN', 'PIJALNIA', 'WARMUT', 'ARENA'],
    #     'Transport': ['BOLT', 'Stacja', 'CIRCLE', 'SPP', 'Parking'],
    #     'Zdrowie': ['MOKOT', 'APTEKA', 'PORADNIA', 'CEFARM-WARSZAWA', 'OSIR', 'PSYCHIATRZY.WARSZAWA'],
    #     'Zakupy internetowe': ['PayPro', 'Elfi.pl', 'KUBUS', 'EVENTIM.PL-PL-ECOM', 'AVANS.PL', 'PAYPAL *ZALANDOSE'],
    #     'Inne': ['UBEZP.', 'SPŁATA', 'ZWROT', 'HB', 'ODSETKI']
    # }
    category_mapping = {
        0: 'Other',
        1: 'Food and drinks',
        2: 'Entertainment',
        3: 'Transportation',
        4: 'Cash',
        5: 'General merchandise',
        6: 'Loans',
        7: 'Returned payments',
        8: 'Bank fees',
        9: 'Personal and healthcare',
        10: 'Rent and utilities',
        11: 'Income',
        12: 'Services',
        13: 'Savings and investments',
        14: 'Government and nonprofit organisations',
        15: 'Travel',
        16: 'Debt collection',
        17: 'Cash transfer'}

    return category_mapping


def assign_category(df, category_mapping):
    # print('description', description)
    """
    Function to assign a category label to each transaction based on the transaction description
    and the provided category mapping.

    This function downloads a pre-trained machine learning model from Cloud Storage
    and uses it to predict the category label for each transaction description.

    Args:
        df (pandas.DataFrame): DataFrame containing transaction data, including the description
            of each transaction.
        category_mapping (dict): A dictionary mapping category labels to patterns.

    Returns:
        pandas.DataFrame: DataFrame with the original transaction data and an additional column
            containing the predicted category labels.

    Note:
        The model expects the DataFrame to have the following columns: 'date_time', 'preprocessed_text',
        'amount', 'day', 'month', 'year', 'day_of_week'.

        If the 'description' column is not named 'preprocessed_text', it will be renamed accordingly
        to match the model's input format.
    """
    bucket_name = "bank_data_milo"
    file_name = "random_forest.joblib"
    client = storage.Client(project='bank-account-analysis-412412')

    bucket = client.get_bucket(bucket_name)
    # Utworzenie obiektu Blob (pliku) w GCS
    blob = bucket.blob(file_name)

    # Download the model file from Cloud Storage
    blob.download_to_filename("/tmp/random_forest_TFIvectorizer.joblib")

    loaded_model = joblib.load('/tmp/random_forest_TFIvectorizer.joblib')
    # Użyj modelu do dokonania predykcji
    df.rename(columns={'description': 'preprocessed_text'}, inplace=True)

    predictions = loaded_model.predict(
        df[['date_time', 'preprocessed_text', 'amount', 'day', 'month', 'year', 'day_of_week']])

    df['label'] = predictions
    df['label'] = df['label'].map(category_mapping)

    # Wybierz tylko interesujące kolumny
    df_result = df[['date_time', 'amount', 'currency', 'institution', 'preprocessed_text', 'label']]

    # Zaktualizuj nazwy kolumn
    df = df_result.rename(columns={'preprocessed_text': 'description'})

    print(df.columns)
    return df


def load(df, table, load_mode='truncate'):
    client = bigquery.Client()
    project = client.project

    dataset_id = 'bankData'
    table_id = table
    dataset_ref = client.dataset(dataset_id)
    table_ref = dataset_ref.table(table_id)

    if load_mode == 'truncate':
        write_disposition = bigquery.WriteDisposition.WRITE_TRUNCATE
    elif load_mode == 'append':
        write_disposition = bigquery.WriteDisposition.WRITE_APPEND
    else:
        raise ValueError("Invalid load_mode. Supported values are 'truncate' or 'append'.")

    job_config = bigquery.LoadJobConfig(
        source_format=bigquery.SourceFormat.PARQUET,  # lub inny format wspierany przez BigQuery
        write_disposition=write_disposition,
        autodetect=True
    )

    job = client.load_table_from_dataframe(df, table_ref, job_config=job_config)

    job.result()  # Czekaj na zakończenie ładowania danych

    print("Loaded {} rows.".format(job.output_rows))


def extractor(file, filename, quantity):
    """
        Function to extract transaction data from a file.

        Args:
            file (dict): The file containing transaction data.
            filename (str): The name of the file.
            quantity (int): The quantity of files.

        Returns:
            pandas.DataFrame: DataFrame containing the extracted transaction data.
    """
    worksheet, workbook = bank_millenium()
    print(type(file))

    position = 0

    data = file[0]

    print(type(data))
    # print(data)

    for position, key in enumerate(data['transactions']['transactions']['booked'][:]):
        for name in key.keys():
            # print("keys", name)

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

    # df["labell"] = np.nan

    # for possition, el in enumerate(df['description']):
    #     df.loc[possition, 'labell'] = assign_category(el, category_mapping)

    try:
        df = df.drop('Unnamed: 0', axis=1)
    except:
        pass

    df['date_time'] = pd.to_datetime(df['date_time'])
    df.loc[:, 'day'] = df['date_time'].dt.day
    df['month'] = df['date_time'].dt.month
    df['year'] = df['date_time'].dt.year
    df['day_of_week'] = df['date_time'].dt.dayofweek

    return df


def trend(data):
    data.drop(columns=['currency', 'institution', 'description'], inplace=True)
    print(data.head())
    result = data.groupby('label').agg({'amount': 'sum', 'date_time': 'max'}).reset_index()
    return result


def get_last_table_load_time(client, dataset_id, table_id):
    dataset_ref = client.dataset(dataset_id)
    table_ref = dataset_ref.table(table_id)

    table = client.get_table(table_ref)
    return table.modified


def get_blob_updated_time(bucket_name, file_name):
    client = storage.Client(project='bank-account-analysis-412412')
    bucket = client.bucket(bucket_name)
    blob = bucket.get_blob(file_name)
    print('blob w funkcji', blob)

    if blob.exists():
        return blob.updated

    return None


def function(data, context):
    """
       Function to process data from multiple files, assign category labels to transactions,
       and load the processed data into a BigQuery table.

       Args:
           data: Input data, usually from Cloud Storage triggers.
           context: Metadata about the triggering event.

       Note:
           This function assumes that the data parameter contains information about multiple files,
           and each file represents a batch of transactions.

           It iterates over each file, extracts transaction data, assigns category labels using
           a pre-trained machine learning model, and concatenates the processed dataframes.

           The concatenated dataframe is then loaded into a BigQuery table named 'bank_data_table'
           with the load mode set to 'truncate'.

           It also checks the last load time of another table named 'bank_data_trends' and,
           if the conditions are met, performs additional processing and loads the result into
           'bank_data_trends' table.

       """
    bucket_name = "bank_data_milo"
    file_names = ["Jacek Milo PKO_BPKOPLPW.json", "Jacek Milo MBANK_RETAIL_BREXPLPW.json"]

    client = storage.Client(project='bank-account-analysis-412412')

    dfs_to_concat = []
    bucket = client.get_bucket(bucket_name)
    # Utworzenie obiektu Blob (pliku) w GCS
    for file in file_names:
        blob = bucket.blob(file)

        # Pobranie zawartości pliku
        file_content = blob.download_as_text()

        # Deserializacja zawartości JSON
        data = json.loads(file_content)

        categories_mapping = create_categories_mapping()

        df = extractor(data, "Jacek", 1)
        df = assign_category(df, category_mapping=categories_mapping)
        dfs_to_concat.append(df)
        df_final = pd.concat(dfs_to_concat, ignore_index=True)

    print('df_final', df_final.head())

    load(df_final, 'bank_data_table', load_mode='truncate')

    bigquery_client = bigquery.Client()
    dataset_id = 'bankData'
    table_id = 'bank_data_trends'
    current_time = datetime.now()

    last_load_time = get_last_table_load_time(bigquery_client, dataset_id, table_id)
    print("last_load_time to bank_data_trends:{}".format(last_load_time))
    for file_name in file_names:
        blob_time = get_blob_updated_time(bucket_name, file_name)
        print("wszedl do pierwszej petli, blob_time:{}".format(blob_time))
        print("blob_time", blob_time)

        if blob_time and blob_time.date() == current_time.date():
            last_load_time = get_last_table_load_time(bigquery_client, dataset_id, table_id)
            print("last_load_time to bank_data_trends:{}".format(last_load_time))
            current_time = datetime.now(timezone.utc)
            print("current_time", current_time)

            # Sprawdź czy ostatni load był nie wcześniej niż 1 dni temu
            if last_load_time and (current_time - last_load_time).days >= 1:
                result = trend(df_final)  # Załóżmy, że df_final jest zdefiniowane gdzieś wcześniej
                result['date_time'] = result['date_time'].astype(str)

                load(result, table_id, load_mode='append')
                print('loaded to bank_data_trends')
