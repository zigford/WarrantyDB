""" Module for managing Dell Warranty Code """

import sqlite3, urllib.request, json
from flask import Flask
from flask import jsonify
from pathlib import Path
from datetime import datetime

dbFile = 'wd.db'
apiKey = 'f62a62238c194ce78fd124607b2e4c2c'

def build_app():
    """ build the webapp """
    app = Flask(__name__)

    @app.route("/")
    def hello():
        # do something
        return "Please use /warranty/ServiceTag URL to get a warranty data."

    @app.route("/warranty/<servicetag>")
    def warrantyEndDate(servicetag):
        warrantyInfo = get_warrantydata(servicetag)
        return warrantyInfo

    return app

def convertDellDatetime(dellDatetime):
    splitStr = dellDatetime.split('-')
    yearStr = splitStr[2].split('T')
    return datetime(int(splitStr[0]), int(splitStr[1]), int(yearStr[0]))

def get_warrantydata(servicetag):
    # first we check if it's in cache:
    Tried = 0
    warrantyData = get_warrantydata_from_sql(servicetag)
    while warrantyData is None and (Tried < 2):
        Tried = Tried + 1
        tryUpdateCache(servicetag)
        warrantyData = get_warrantydata_from_sql(servicetag)
    if warrantyData is not None:
        return warrantyData
    else:
        return jsonify({
                'ComputerName' : 'undefined',
                'WarrantyData' : 'undefined',
                'Model'        : 'undefined'})

def tryUpdateCache(servicetag):
    baseURL='https://sandbox.api.dell.com/support/assetinfo/v4/getassetwarranty/'
    serviceTagURL = baseURL + servicetag
    apiURL = serviceTagURL + '?apikey=' + apiKey
    with urllib.request.urlopen(apiURL) as url:
        data = json.loads(url.read().decode())
    newestEndDate = datetime(1970, 1, 1)
    for entitlement in data["AssetWarrantyResponse"][0]["AssetEntitlementData"]:
        if entitlement['ServiceLevelDescription'] is not None:
            endDate = entitlement['EndDate']
            if convertDellDatetime(endDate) > newestEndDate:
                newestEndDate = convertDellDatetime(endDate) 
    model = data ["AssetWarrantyResponse"][0]["AssetHeaderData"]['MachineDescription']           
    wd = {
            'ComputerName' : servicetag,
            'WarrantyData' : newestEndDate,
            'Model'        : model}
    updateSql(wd)

def get_warrantydata_from_sql(servictag):
    """Get warranty data from sqlite"""
    conn = initSqlCursor()
    sqlc = conn.cursor()
    # create table
    sqlc.execute('SELECT * FROM warrantydata WHERE ComputerName=?', (servictag,))
    sqlResult = sqlc.fetchone()
    if sqlResult is not None:
        sql_as_dict = {
                'ComputerName' : sqlResult[1],
                'WarrantyData' : sqlResult[2],
                'Model'        : sqlResult[3]}
        return jsonify(sql_as_dict)
    else:
        return None
    conn.close()

def updateSql(wd):
    conn = initSqlCursor()
    sqlc = conn.cursor()
    sqlstr = """ INSERT INTO warrantydata(ComputerName,WarrantyData,Model)
                 VALUES(?,?,?) """
    sqlc.execute(sqlstr,(wd['ComputerName'],wd['WarrantyData'],wd['Model']))
    conn.commit()
    conn.close()
    
def initSqlCursor():
    dbFilePath = Path(dbFile)
    # database file exists
    conn = sqlite3.connect(dbFile)
    cursor = conn.cursor()
    try:
        # has the database been initialized?
        cursor.execute("""SELECT name FROM sqlite_master WHERE type='table' AND name='warrantydata'""")
        if cursor.fetchone() is not None:
            return conn
        else:
            # time to initialize the database
            cursor.execute('''CREATE TABLE warrantydata (id integer PRIMARY KEY,ComputerName text, WarrantyData text,Model text)''')
            conn.commit()
            return conn
    except Error as e:
        print(e)
        return -1

app = build_app()
app.run()
