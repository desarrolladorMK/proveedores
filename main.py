from fastapi import FastAPI, HTTPException,Query
from fastapi.responses import HTMLResponse
import pyodbc
from collections import defaultdict

app = FastAPI()

# Cadena de conexión
conn_str = (
    r'DRIVER={ODBC Driver 17 for SQL Server};'
    r'SERVER=db02.siesacloud.local;'  # Nombre del servidor
    r'DATABASE=master;'  # Cambia a tu base de datos específica si la tienes
    r'UID=merkahorroapp;'  # Usuario
    r'PWD=Merkahorro$21$%;'  # Contraseña
    r'TrustServerCertificate=yes;'  # Si es necesario para omitir la verificación del certificado
)

# Función para establecer la conexión
def get_db_connection():
    try:
        connection = pyodbc.connect(conn_str)
        return connection
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Error al conectar a la base de datos: {e}")

# Función para convertir las filas a diccionarios
def fetch_rows_as_dict(cursor):
    columns = [column[0] for column in cursor.description]
    rows = cursor.fetchall()
    return [dict(zip(columns, row)) for row in rows]

# Endpoint para probar la conexión
@app.get("/test-connection")
def test_connection():
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT 1")
    result = cursor.fetchone()
    conn.close()
    return {"message": "Conexión exitosa", "result": result}

# Endpoint para obtener datos de la base de datos

@app.get("/", response_class=HTMLResponse)
def get_index():
    with open("index.html", "r") as file:
        return HTMLResponse(content=file.read())

def fetch_rows_as_dict(cursor):
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]

@app.get("/empleados")
def get_empleados(descripcion: str = Query(None)):
    conn = get_db_connection()
    cursor = conn.cursor()

    if descripcion:
        query = """SELECT [f281_id_cia], [f281_id], [f281_descripcion], [f281_ts] 
                   FROM [UnoEE_Merkahorro_Real].[dbo].[t281_co_unidades_negocio] 
                   WHERE f281_descripcion LIKE ?"""
        cursor.execute(query, ('%' + descripcion + '%',))
    else:
        cursor.execute("SELECT [f281_id_cia], [f281_id], [f281_descripcion], [f281_ts] FROM [UnoEE_Merkahorro_Real].[dbo].[t281_co_unidades_negocio]")

    rows = fetch_rows_as_dict(cursor)
    conn.close()
    return {"empleados": rows}