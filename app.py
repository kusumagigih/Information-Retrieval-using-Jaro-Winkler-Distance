import nltk, string, re, math
from Sastrawi.Stemmer.StemmerFactory import StemmerFactory
factory = StemmerFactory()
stemmer = factory.create_stemmer()
from nltk.corpus import stopwords
listStopword = set(stopwords.words('indonesian'))
from flask import Flask, render_template, request, session
from flask_mysqldb import MySQL
from nltk.corpus import wordnet
import textdistance
# import mysql.connector

app = Flask(__name__)
app.config["SECRET_KEY"] = "kepo"
app.config['MYSQL_HOST'] = 'localhost'
app.config['MYSQL_USER'] = 'root'
app.config['MYSQL_PASSWORD'] = ''
app.config['MYSQL_DB'] = 'skripsi'

mysql = MySQL(app)

@app.route("/")
def index():
    return render_template("main_layout.html")

def preprocess(tanya):
    tanya = tanya.lower()
    tanya = tanya.translate(str.maketrans("", "", string.punctuation))
    tanya = re.sub(r"\d+", "", tanya)
    tanya = stemmer.stem(tanya)
    return tanya


def tokenize(tanya):
    tokens = nltk.tokenize.word_tokenize(tanya)
    # tokens2 = [x for x in tokens if x not in listStopword]
    tokens = nltk.FreqDist(tokens)
    return dict(tokens)

def loaddoc(tokens, ctg):
    cur = mysql.connection.cursor()
    cur.execute('''
  SELECT id,buku,bab,bagian,paragraf,pasal,ayat FROM dokumen WHERE id IN
(SELECT DISTINCT id_dok FROM dok_kata, kata WHERE 
dok_kata.category = %s AND
dok_kata.kata = kata.id AND kata.teks IN (''' 
    + ', '.join(['%s'] * len(tokens)) +
    '))', (ctg, *tokens))
   
    docs = list(cur.fetchall())
    results = []
    for doc in docs:
        results.append({
            'id': doc[0],
            'buku': doc[1],
            'bab': doc[2],
            'bagian': doc[3],
            'paragraf': doc[4],
            'pasal': doc[5],
            'ayat': doc[6],
        })
    return results

def getscore(doks, tanya, ctg):
    scores = {}
    for dok in doks:
        scores[dok['id']] = textdistance.jaro_winkler(tanya, dok[ctg])
    return scores


def loaddocuments(docids, scores):
    cur = mysql.connection.cursor()
    cur.execute('''
    SELECT id,buku,bab,bagian,paragraf,pasal,ayat 
    FROM dokumen WHERE id IN (''' 
    + ', '.join(['%s'] * len(docids)) +
    ''')''', tuple(docids))
    results = []
    docs = list(cur.fetchall())
    for docid in docids:
        for doc in docs:
            if docid == doc[0]:
                results.append({
                    'id': doc[0],
                    'buku': doc[1],
                    'bab': doc[2],
                    'bagian': doc[3],
                    'paragraf': doc[4],
                    'pasal': doc[5],
                    'ayat': doc[6],
                    'score': scores[docid]
                })
                break
    jumlah_dokumen = len(results)
    print("Jumlah dokumen terpanggil:", jumlah_dokumen)
    return results


@app.route("/result")
def result():
    tanya = (request.args['query'])
    tanyapred = preprocess(tanya)
    scores_all = {}
    for ctg_i, ctg_name in enumerate("Ayat".split(",")):
        doks = loaddoc(set(tokenize(tanyapred)), ctg_name)
        scores = getscore(doks, tanyapred, ctg_name.lower())
        for docid, score in scores.items():
            if docid not in scores_all:
                scores_all[docid] = [0] * 1
            scores_all[docid][ctg_i] = score
    for docid, s in scores_all.items():
        scores_all[docid] = s[0]
    docids = sorted(scores_all, key=scores_all.get, reverse=True)
    results = loaddocuments(docids, scores_all) if len(docids) > 0 else []
    return render_template("result.html", takok = tanya, results = results )

if __name__ == "__main__":
    app.run(debug=True)