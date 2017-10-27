from flask import render_template, request
from app import app
import pymysql as mdb
#from weave_match import user_data2features
from app.weave_match import matches

#db = mdb.connect(user="root", host="localhost", db="weave_pair", charset='utf8', unix_socket="/tmp/mysql.sock")
cdb = mdb.connect(user="insight", host="alfred-prod.cbyff1yl1xje.us-west-2.rds.amazonaws.com", db="alfred_prod", password="YWRt9fxYzx1PqHy")

@app.route('/')
@app.route('/index')
def index():
    return render_template("index.html",
                title = 'Home', user = { 'nickname': 'Miguel' },)
    
@app.route('/db')
def cities_page():
    with cdb:
        cur = cdb.cursor()
        cur.execute("SELECT title,company,profile_url FROM user_profiles LIMIT 15;")
        query_results = cur.fetchall()
    cities = ""
    for result in query_results:
        cities += result[0]
        cities += result[1]
        cities += "<br>"
    return cities

@app.route("/db_fancy")

def cities_page_fancy():
    with cdb:
        cur = cdb.cursor()
        cur.execute("SELECT title,company,profile_url FROM user_profiles LIMIT 15;")
        query_results = cur.fetchall()
    users = []
    for result in query_results:
        users.append(dict(title=result[0], company=result[1], profile_url=result[2]))
    return render_template('users.html', users=users) 

@app.route('/input')
def cities_input():
    return render_template('input.html')

@app.route('/output')
def cities_output():
    #pull 'ID' from input field and store it
    looking_for = request.args.get('looking_for')
    user_name = request.args.get('name')
    user_degree = request.args.get('degree')
    user_start_yr = request.args.get('graduation_year')
    #return 3 user_id
    match_user_id = matches(user_name, user_degree, user_start_yr, looking_for)
    
    with cdb:
        cur = cdb.cursor()
        #just select the city from the world_innodb that the user inputs
        cur.execute("SELECT title,company,profile_url FROM user_profiles WHERE user_id IN ('%d', '%d', '%d', '%d', '%d');" % match_user_id)
        query_results = cur.fetchall()

    users = []
    for result in query_results:
        users.append(dict(title=result[0], company=result[1], profile_url=result[2]))
    the_result = ''
    return render_template("output.html", users = users, the_result = the_result)
