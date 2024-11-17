import pandas as pd
from cs50 import SQL
from flask import Flask, flash, redirect, render_template, request
import Levenshtein
import re


# import lines flask and cs50 and app = Flask(__name__) and db = SQL("sqlite:///rapprochement.db") and probably @app.route("/")def index(): return render_template("index.html") got it from finance pset
app = Flask(__name__)

db = SQL("sqlite:///rapprochement.db")

@app.route("/")
def index():
    return render_template("index.html")


@app.route("/rapprocher", methods=["GET", "POST"])
def intial():
    if request.method == "POST":
        db.execute("DELETE FROM GL")
        db.execute("DELETE FROM BS")
        db.execute("DELETE FROM PER")
        db.execute("DELETE FROM MAN")
        # ai helped either poe or chatgpt with request.files

        gl = request.files.get("general_ledger")
        bs = request.files.get("bank_statement")

        # read excel files
        try :
            gl = pd.read_excel(gl)
            bs = pd.read_excel(bs)
        except:
            return render_template("index.html")

        gl["Description"]=gl["Description"].str.strip()
        bs["Description"]=bs["Description"].str.strip()


        #chatgpt gave this
        gl.insert(0, 'ligne', range(1, len(gl) + 1))
        bs.insert(0, 'ligne', range(1, len(bs) + 1))



        gl.insert(1, 'Jour', gl['Date'].dt.strftime('%d'))
        bs.insert(1, 'Jour', bs['Date'].dt.strftime('%d'))

        gl.insert(2, 'Mois', gl['Date'].dt.strftime('%m'))
        bs.insert(2, 'Mois', bs['Date'].dt.strftime('%m'))

        #chatgpt corrected the format below

        gl.insert(3, 'Annee', gl['Date'].dt.strftime('%Y'))
        bs.insert(3, 'Annee', bs['Date'].dt.strftime('%Y'))

        gl=gl.drop(columns=['Date'])
        bs=bs.drop(columns=['Date'])

        gl.fillna("", inplace=True)
        bs.fillna("", inplace=True)



        gl['Position'] = gl['Debit'].apply(lambda x: 'Debit' if x!= 0 else 'Credit')
        bs['Position'] = bs['Debit'].apply(lambda x: 'Debit' if x!= 0 else 'Credit')



        # chatgpt helped with len(gl)  gl.iloc[i] and reminded me of the structure of INSERT INTO

        # write each row in SQL TABLE
        for i in range(len(gl)):
            row_gl = list(gl.iloc[i])
            db.execute("INSERT INTO GL (Ligne,Jour,Mois,Annee,Libelle,Debit,Credit,Position) VALUES(?,?,?,?,?,?,?,?)",
                       int(row_gl[0]), row_gl[1], row_gl[2], row_gl[3], row_gl[4], float(row_gl[5]), float(row_gl[6]),row_gl[7])

        for i in range(len(bs)):
            row_bs = list(bs.iloc[i])
            db.execute("INSERT INTO BS (Ligne,Jour,Mois,Annee,Libelle,Debit,Credit,Position) VALUES(?,?,?,?,?,?,?,?)",
                       int(row_bs[0]), row_bs[1], row_bs[2], row_bs[3], row_bs[4], float(row_bs[5]), float(row_bs[6]),row_bs[7])


        #ai duck advised me to use left join and union which was what i did saw 3WS how they implemented left join and union
        # union between count_gl  and count_bs to figure out the correct recorded transactions with same number of perfect repetition in both GL and BS

        transactions = db.execute("SELECT count_gl.Jour,count_gl.Mois,count_gl.Annee, count_gl.Libelle,count_gl.Debit,count_gl.Credit , count_bs.COUNTBS, count_gl.COUNTGL FROM (SELECT Jour,Mois,Annee, Libelle,Debit,Credit ,COUNT()AS COUNTGL FROM GL GROUP BY Jour,Mois,Annee,Libelle,Credit,Debit)AS count_gl LEFT JOIN (SELECT Jour,Mois,Annee, Libelle,Debit,Credit ,COUNT()AS COUNTBS FROM BS GROUP BY Jour,Mois,Annee,Libelle,Credit,Debit)AS count_bs ON count_bs.Jour=count_gl.Jour AND count_bs.Mois=count_gl.Mois AND count_bs.Annee=count_gl.Annee AND count_bs.Libelle=count_gl.Libelle AND count_bs.Credit=count_gl.Debit AND count_bs.Debit=count_gl.Credit ")

        perfect(transactions)


        BS=db.execute("SELECT * FROM BS")
        GL=db.execute("SELECT * FROM GL")
        green_transactions=list()
        yellow_transactions=list()

    return render_template("manuelle.html",GL=GL,BS=BS, green=green_transactions, yellow=yellow_transactions)



@app.route("/manuelle", methods=["GET", "POST"])
def manuelle():
    if request.method == "POST":
        #chatgpt told me about request.form.getlist
        if 'rapprocher' in request.form:
            GL_id_list=request.form.getlist("GL")
            BS_id_list=request.form.getlist("BS")
            problems=request.form.getlist("problem")



            #adding transactions with problems encountered into manually reconciled table
            for i in range(len(GL_id_list)):
                db.execute("INSERT INTO MAN (id, Ligne,Jour,Mois,Annee,Libelle,Debit,Credit,Position) SELECT id, Ligne,Jour,Mois,Annee,Libelle,Debit,Credit,Position FROM GL WHERE id=?", GL_id_list[i])
                db.execute("UPDATE  MAN SET Source='GL' WHERE id=?",GL_id_list[i])
                if "amount" in problems :
                    db.execute("UPDATE MAN SET Amount_p='yes' WHERE id=?",GL_id_list[i])
                if "libelle" in problems :
                    db.execute("UPDATE MAN SET Libelle_p='yes' WHERE id=?",GL_id_list[i])
                if "date" in problems :
                    db.execute("UPDATE MAN SET Date_p='yes' WHERE id=?",GL_id_list[i])

                db.execute("DELETE FROM GL WHERE id=?", GL_id_list[i])

            for i in range(len(BS_id_list)):
                db.execute("INSERT INTO MAN (id, Ligne,Jour,Mois,Annee,Libelle,Debit,Credit,Position) SELECT id, Ligne,Jour,Mois,Annee,Libelle,Debit,Credit,Position FROM BS WHERE id=?",BS_id_list[i] )
                db.execute("UPDATE MAN SET Source='RB' WHERE id=?",BS_id_list[i])

                if "amount" in problems :
                    db.execute("UPDATE MAN SET Amount_p='yes' WHERE id=?",BS_id_list[i])
                if "libelle" in problems :
                    db.execute("UPDATE MAN SET Libelle_p='yes' WHERE id=?",BS_id_list[i])
                if "date" in problems :
                    db.execute("UPDATE MAN SET Date_p='yes' WHERE id=?",BS_id_list[i])

                db.execute("DELETE FROM BS WHERE id=?", BS_id_list[i])


            BS=db.execute("SELECT * FROM BS")
            GL=db.execute("SELECT * FROM GL")

            #remove effect of generate
            green_transactions=list()
            yellow_transactions=list()
        #recherche des transactions similaires
        elif 'generate' in request.form :
            id=request.form["generate"]
            transaction=db.execute("SELECT * FROM GL WHERE id=?",id)
            green_transactions,yellow_transactions=color(transaction)
            GL=db.execute("SELECT * FROM GL" )
            BS=db.execute("SELECT * FROM BS" )


            return render_template("manuelle.html",GL=GL,BS=BS,green=green_transactions,yellow=yellow_transactions)

    return render_template("manuelle.html",GL=GL,BS=BS,green=green_transactions,yellow=yellow_transactions)


@app.route("/rapport", methods=["GET", "POST"])
def rapport():
    MAN=db.execute("SELECT * FROM MAN")
    BS=db.execute("SELECT * FROM BS")
    GL=db.execute("SELECT * FROM GL")
    PER=db.execute("SELECT * FROM PER")
    return render_template("rapport.html",GL=GL,BS=BS,MAN=MAN, PER=PER)



def perfect(x):
    perfect_transactions_GL=[]
    perfect_transactions_BS=[]

    for item in x  :
        #table was outputting None values so this was a quick fix.
        if item["COUNTBS"] is None:
            item["COUNTBS"]=0
        if item["COUNTGL"] is None:
            item["COUNTGL"]=0
        #outputting perfect transactions and deleteing them from db
        if item["COUNTBS"] == item["COUNTGL"] or item["COUNTBS"] < item["COUNTGL"]  :
            perfect_transactions_id_GL=db.execute("SELECT id FROM GL WHERE Jour=? AND Mois=? AND Annee=? AND Libelle=? AND Debit=? AND Credit=?", item["Jour"], item["Mois"], item["Annee"],item["Libelle"],item["Debit"],item["Credit"])
            perfect_transactions_id_BS=db.execute("SELECT id FROM BS WHERE Jour=? AND Mois=? AND Annee=? AND Libelle=? AND Debit=? AND Credit=?", item["Jour"], item["Mois"], item["Annee"],item["Libelle"],item["Credit"],item["Debit"])
            for j in range(item["COUNTBS"]) :
                perfect_transactions_GL.append(db.execute("SELECT Ligne,Jour,Mois,Annee,Libelle,Debit,Credit FROM GL WHERE id=?",perfect_transactions_id_GL[j]["id"]))
                perfect_transactions_BS.append(db.execute("SELECT Ligne,Jour,Mois,Annee,Libelle,Debit,Credit FROM BS WHERE id=?",perfect_transactions_id_BS[j]["id"]))

                #adding the transaction to the table and precising it's from GL// the
                db.execute("INSERT INTO PER (id,Ligne,Jour,Mois,Annee,Libelle,Debit,Credit,Position) SELECT id,Ligne,Jour,Mois,Annee,Libelle,Debit,Credit,Position FROM GL WHERE id=?",perfect_transactions_id_GL[j]["id"])
                #duck helped with structure
                db.execute("UPDATE PER SET Source='GL' WHERE id=?",perfect_transactions_id_GL[j]["id"])



                #deleting perfect transactions from BS and GL
                db.execute("DELETE FROM BS WHERE id=?", perfect_transactions_id_BS[j]["id"])
                db.execute("DELETE FROM GL WHERE id=?", perfect_transactions_id_GL[j]["id"])
    return perfect_transactions_GL, perfect_transactions_BS



def color(x):

    yellow_transactions=[]
    green_transactions=[]
    #duck helped with strutcure
    db.execute("INSERT INTO bs_rate (id) SELECT id FROM BS")

    list=db.execute("SELECT * FROM BS")

    for item in list :
        #reset// chatgpt helped i was lazy i put it all in one line and got an error and fixed it one in a line
        day_rate = 0
        month_rate = 0
        year_rate = 0
        Libelle_match = 0
        amount_match = 0
        #amount of searched gl transaction turned to string for compariasions
        if x[0]["Position"]=="Debit":
                gl_amount=str(item["Debit"])
        else :
            gl_amount=str(item["Credit"])
        #score for day/month/year 1 or 0 or None

        if item["Jour"]==x[0]["Jour"] :
            day_rate=1
            db.execute("UPDATE BS_rate SET Jour = ? WHERE id = ?",day_rate,item["id"])



        if item["Mois"]==x[0]["Mois"] :
            month_rate=1
            db.execute("UPDATE BS_rate SET Mois = ? WHERE id = ?",month_rate,item["id"])



        if item["Annee"]==x[0]["Annee"] :
            #from W3S structure below.
            year_rate=1
            db.execute("UPDATE BS_rate SET Annee = ? WHERE id = ?",year_rate,item["id"])
      

        # score of similarity for amount

        if item["Position"]=="Debit":
            bs_amount=str(item["Debit"])
        else :
            bs_amount=str(item["Credit"])

        amount_match=Levenshtein.ratio(gl_amount, bs_amount)

        db.execute("UPDATE BS_rate SET Amount = ? WHERE id = ?",amount_match,item["id"])

        #score for similarity of libelle
        if item["Libelle"] is not None :

            #https://stackoverflow.com/questions/5843518/remove-all-special-characters-punctuation-and-spaces-from-string
            gl_word=re.sub('[^A-Za-z0-9 ]+', '', x[0]["Libelle"])
            #https://stackoverflow.com/questions/1546226/is-there-a-simple-way-to-remove-multiple-spaces-in-a-string
            gl_word=re.sub(' +', ' ',gl_word)

            gl_word=gl_word.lower()
            bs_word=item["Libelle"].lower()


            if len(gl_word.replace(' ', ''))>=3:
                if ' ' not in gl_word :
                    #chatgpt helped with the ..replace(' ', '') and how i am supposed to write everything.
                    bs_word=bs_word.replace(' ', '')
                    Libelle_match=Levenshtein.ratio(gl_word,bs_word)
                else :
                    #comparing first words
                    index_space_bs = bs_word.find(" ")
                    index_space_gl = gl_word.find(" ")
                    first_word_match=Levenshtein.ratio(gl_word[:index_space_gl],bs_word[:index_space_bs])

                    if len(gl_word[index_space_gl:])>=3 :

                        gl_rest_word=gl_word[index_space_gl:].replace(' ', '')
                        bs_rest_word=bs_word[index_space_bs:].replace(' ', '')

                        Rest_word_match=Levenshtein.ratio(gl_rest_word,bs_rest_word)

                        #if word has same number id and different first_word definelt green that's why Rest_word_match higher.
                        Libelle_match= first_word_match*0.40+Rest_word_match*0.60
                    else :
                        Libelle_match=first_word_match
            else :

                Libelle_match=1
        else :
            Libelle_match=1

        db.execute("UPDATE BS_rate SET Libelle = ? WHERE id = ?",Libelle_match,item["id"])


        coef_list=[0.0445,0.0629,0.51,0.1482,0.2336]
        rate_list=[day_rate,month_rate,year_rate,Libelle_match,amount_match]


        Final=0

        for i in range(len(rate_list)):
            if rate_list[i] is not None:
                Final+=coef_list[i]*rate_list[i]


        db.execute("UPDATE BS_rate SET Final = ? WHERE id = ?", Final, item["id"])
        print(db.execute("SELECT * FROM BS_rate"))


        if Final>=0.80 :
            green_transactions.append(item['id'])
        elif Final>=0.65 :
            yellow_transactions.append(item['id'])

        db.execute("DELETE FROM BS_rate")
    return green_transactions, yellow_transactions




































    #same day/same month/same year/ same amount /same position/ low rate description [ this needs more detail not just low match rate suggest me somethings]
    #(same day /month /year)/same amount/not same position/high match rate (green)
    #(same day /month /year)/not same amount/same position/high match rate (yellow)
    #not same day/same month/same year/same amount /same position/high match rate (green)
    #same day/not same month/same year/same amount /same position/high match rate (yellow)
    #same day/ame month/not same year/same amount /same position/high match rate (red)



    #year is the most important (determines if green or red)
    #if month is not same and all other are good then yellow.


    #year
    #month/#amount idk who's first
    #match rate yellow and all good then green / match rate red and all good yellow leaning more to red
    #day







    #  rate dicription extremy important

    #posiiton is a kind of back up.(least important) (we can just delete it because it doesnt affect anything.)







    return green_transactions, yellow_transactions



















