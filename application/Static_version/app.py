import os
from uuid import uuid4
import json
from dotenv import load_dotenv
from flask import Flask, jsonify, redirect, render_template, session, url_for, request
from nordigen import NordigenClient
from google.cloud import storage
from google.oauth2.service_account import Credentials


"""
Bank Data Extraction Application

This Flask application interacts with the Nordigen API to retrieve and process banking data. 
It provides a web interface for users to authorize access to their bank accounts and view transaction details. 
Processed data is stored in Google Cloud Storage (GCS) and can be used for further analysis.

Prerequisites:
- Nordigen API credentials (SECRET_ID, SECRET_KEY) are required and should be stored as environment variables.
- Google Cloud Storage bucket (bucket_name) for storing processed data.
- Google Cloud credentials for authentication.

Endpoints:
- `/`: Landing page displaying a list of available institutions for account authorization.
- `/agreements/<institution_id>`: Handles the authorization process for a specific institution.
- `/results`: Displays transaction results after successful authorization.

Functionality:
1. **Authorization**: Users select an institution on the landing page and authorize access to their bank accounts.
2. **Data Retrieval**: Transactions, account details, balances, and metadata are retrieved using the Nordigen API.
3. **Data Processing**: Retrieved data is processed and stored in a JSON file.
4. **Google Cloud Storage**: Processed data is uploaded to GCS for storage.

Usage:
1. Run the Flask application locally or deploy it to a hosting platform.
2. Users access the application, authorize their bank accounts, and view transaction details.
3. Processed data is stored in GCS for further analysis.

Note: Ensure to set up environment variables, API keys, and other configurations as needed before running the application.

"""


app = Flask(__name__, static_url_path='/static', static_folder="./static")
app.config["SECRET_KEY"] = os.urandom(24)

app.config['STATIC_FOLDER'] = 'static'
COUNTRY = "PL"
REDIRECT_URI = "your-url"
# REDIRECT_URI = 'https://127.0.0.1:5000/results'

# Load secrets from .env file
load_dotenv()

# Init Nordigen client pass secret_id and secret_key generated from OB portal
# In this example we will load secrets from .env file
client = NordigenClient(
    secret_id=os.environ.get("SECRET_ID"),
    secret_key=os.environ.get("SECRET_KEY")
)
# @app.route("/")
# def form():
#     return render_template("user_contact_data.html")

# @app.route("/", methods=["POST"])
# def form_post():
#     global user
#     user = {}
#     if request.method == 'POST':
#         session['user_name'] = request.form['User_name']
#         session['user_last_name'] = request.form['User_last_name']
#         session['user_email'] = request.form['User_email']
#         session["user_full_name"] = session['user_name'] + " " + session['user_last_name']
#         user["user_name"] = session['user_name']
#         user["user_last_name"] = session['user_last_name']
#         user["user_email"] = session['user_email']
#         # session["user_full_name_and_email"] = user
#         # session['user_name'] + " " + session['user_last_name'] + " " + session['user_email']
#         if (session.get('user_name') == "" or session.get('user_last_name') == "" or session.get('user_email') == ""):
#             return redirect(request.url)
#         else:
#             return redirect(url_for("home"))

# Generate access & refresh token
client.generate_token()


@app.route("/", methods=["GET"])
def home():
    # Get list of institutions
    institution_list = client.institution.get_institutions(country=COUNTRY)

    return render_template("index.html", institutions=institution_list)


@app.route("/agreements/<institution_id>", methods=["GET"])
def agreements(institution_id):

    if institution_id:

        init = client.initialize_session(
            institution_id=institution_id,
            redirect_uri=REDIRECT_URI,
            reference_id=str(uuid4())
        )

        redirect_url = init.link
        session["req_id"] = init.requisition_id
        req_id = init.requisition_id
        print("TO req_id w agreements", req_id)
        print("redirect_url", redirect_url)
        session["institution_id"] = institution_id
        redirected = redirect(redirect_url)
        redirected.set_cookie('req_id', session["req_id"])
        return redirected

    return redirect(url_for("home"))



@app.route("/results", methods=["GET"])
def results():
    institution_id = session.get('institution_id', None)
    print("institution_id", institution_id)
    cookie_name = request.cookies.get('req_id')
    print("cookie_name", cookie_name)
    print("session['req_id']=", cookie_name)

    global user
    user = {}
    user["user_name"] = 'name'
    user["user_last_name"] = 'surname'
    user["user_email"] = 'email'
    user["user_full_name"] = user['user_name'] + " " + user['user_last_name']
    user["institution"] = f'{institution_id}' if institution_id else 'default_value'


    if cookie_name != None:
        print("session['req_id']=", cookie_name)
        # global accounts
        accounts = client.requisition.get_requisition_by_id(requisition_id = cookie_name)["accounts"]
        accounts_data = []
        for id in accounts:
            account = client.account_api(id)
            metadata = account.get_metadata()
            transactions = account.get_transactions()
            details = account.get_details()
            balances = account.get_balances()

            accounts_data.append(
                {
                    "metadata": metadata,
                    "details": details,
                    "balances": balances,
                    "transactions": transactions,
                }
            )
            accounts_data.append(user)

        print("accounts_data", accounts_data)

        # with open(f"{user['user_full_name']+' '+user['institution']}.json", "w") as outfile:
        #     json.dump(accounts_data, outfile)

        bucket_name = "bank_data_milo"
        # Ustawienie ścieżki w GCS, gdzie plik ma być umieszczony
        blob_name = f"{user['user_full_name']+' '+user['institution']}.json"


        # The ID of your GCS object

        credentials_dict = {
            'type': 'service_account',
            'client_id': os.environ['CLIENT_ID'],
            'client_email': os.environ['CLIENT_EMAIL'],
            'private_key': os.environ['PRIVATE_KEY'],
            'token_uri': os.environ['TOKEN_URI'],
        }

        credentials = Credentials.from_service_account_info(
            credentials_dict
        )
        client2 = storage.Client(credentials=credentials, project='project')
        bucket = client2.get_bucket(bucket_name)

        blob = bucket.blob(blob_name)
        contents_enc = json.dumps(accounts_data, ensure_ascii=False).encode('utf8')
        blob.upload_from_string(data=contents_enc, content_type='application/json')
        print("user", user.values())

        print(f"Plik {blob_name} został pomyślnie przesłany do GCS.")

        # with open(f"{session['user_full_name']}.json", "a") as outfile:
        #     json.dump(user, outfile)

        # return redirect('/')
        return render_template("thanks.html")

    raise Exception(
        "Requisition ID is not found. Please complete authorization with your bank"
    )
