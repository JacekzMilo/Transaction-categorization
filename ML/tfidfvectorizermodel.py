from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.feature_extraction.text import CountVectorizer
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.neighbors import KNeighborsClassifier
from sklearn.pipeline import Pipeline
from sklearn.metrics import classification_report
from sklearn.ensemble import RandomForestClassifier
from sklearn.compose import ColumnTransformer
import spacy
import joblib
pd.set_option('display.max_rows', 50)
pd.set_option('display.max_columns', 5000)
pd.set_option('display.width', 10000)



corpus = pd.read_csv("data.csv")
corpus2 = pd.read_csv('data2.csv')
corpus2.dropna(inplace=True)
corpus2.drop(columns=['institution', 'currency'], inplace=True)
corpus2.rename(columns={'descritpion': 'counter_party_name', 'labell': 'label'}, inplace=True)
# print(corpus.shape)
# print(corpus2.shape)
merged_df = pd.concat([corpus, corpus2])
# print(merged_df.head())

merged_df.dropna(inplace=True)

# text = merged_df.counter_party_name
# text = merged_df.drop(columns=['label', 'date_time'])

v = TfidfVectorizer()
# transormed_output = v.fit_transform(text)
# print('v.vocabulary_', v.vocabulary_)


# features = v.get_feature_names_out()
# print(features)

# for word in features:
#     for x in word:
#         indx = v.vocabulary_.get(x)
#         print(f'{x} {v.idf_[indx]}')

# print(text[:2])
#
# print(transormed_output.toarray()[:2])
#
# print(corpus.shape)
# print(corpus.head())
# print(corpus.label.value_counts())

merged_df['label_num'] = merged_df.label.map({
    'Other': 0,
    'Food and drinks': 1,
    'Entertainment': 2,
    'Transportation': 3,
    'Cash': 4,
    'General merchandise': 5,
    'Loans': 6,
    'Returned payments': 7,
    'Bank fees': 8,
    'Personal and healthcare': 9,
    'Rent and utilities': 10,
    'Income': 11,
    'Services': 12,
    'Savings and investments': 13,
    'Government and nonprofit organisations': 14,
    'Travel': 15,
    'Debt collection': 16,
    'Cash transfer': 17
})

nlp = spacy.load("pl_core_news_md")
def preprocess(text):
    # remove stop words and lemmatize the text
    doc = nlp(text)
    filtered_tokens = []
    for token in doc:
        if token.is_stop or token.is_punct:
            continue
        filtered_tokens.append(token.lemma_)
    return " ".join(filtered_tokens)

merged_df['preprocessed_text'] = merged_df['counter_party_name'].apply(preprocess)

df2 = merged_df[['date_time','preprocessed_text', 'amount', 'label_num']]


# Ekstrakcja składników daty
df2['date_time'] = pd.to_datetime(df2['date_time'])
df2.loc[:, 'day'] = df2['date_time'].dt.day
df2['month'] = df2['date_time'].dt.month
df2['year'] = df2['date_time'].dt.year
df2['day_of_week'] = df2['date_time'].dt.dayofweek

print('df2', df2.head())

selected_columns = ['day', 'month', 'year', 'day_of_week', 'preprocessed_text', 'amount']


# print("shape of X_train", X_train.shape)
# print("shape of X_test", X_test.shape)
# print("shape of y_train", y_train.shape)

# print(y_train.value_counts())
# print(y_test.value_counts())

from sklearn.preprocessing import StandardScaler

# Definiowanie przekształceń dla poszczególnych kolumn
preprocessor = ColumnTransformer(
    transformers=[
        ('text', CountVectorizer(), 'preprocessed_text'),
        ('numeric', StandardScaler(), ['amount'])
    ])


# 1. Create a pipeline object
clf = Pipeline([
    ('preprocessor', preprocessor),
    ('classifier', RandomForestClassifier())
])

# Podział danych na zbiór treningowy i testowy
X_train, X_test, y_train, y_test = train_test_split(
    df2[selected_columns], df2.label_num, test_size=0.2,
    random_state=2024, stratify=df2.label_num)

# 2. fit with X_train and y_train
clf.fit(X_train, y_train)

# 3. get the predictions for X_test and store it in y_pred
y_pred = clf.predict(X_test)

# 4. print the classification report
print(classification_report(y_test, y_pred))
print('X_test', X_test[:5])
print('y_test', y_test[:5])
print('y_pred', y_pred[:5])



# Zapisz model do pliku
# joblib.dump(clf, 'random_forest_TFIvectorizer.joblib')
