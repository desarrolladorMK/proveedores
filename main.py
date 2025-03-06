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

@app.get("/documentos")
def get_documentos():
    """
    Endpoint para obtener TODOS los documentos sin filtros.
    """
    conn = get_db_connection()
    cursor = conn.cursor()

    query = """SELECT TOP (1115) 
         
           t1.*, 
        t2.f_telefono,
        t2.f_municipio_desc,
        t2.f_direccion,
		t2.f_email,
        t3.f350_fecha,
        t3.f350_total_db,
        t3.f350_usuario_creacion
    FROM [UnoEE_Merkahorro_Real].[dbo].[BI_T363] t1
    LEFT JOIN [UnoEE_Merkahorro_Real].[dbo].[SE_T200] t2 
        ON t1.f_beneficiario = t2.f_tercero
    LEFT JOIN [UnoEE_Merkahorro_Real].[dbo].[t350_co_docto_contable] t3
        ON t1.f_perido = t3.f350_id_periodo
        WHERE t1.f_docto_egreso = '001-FCE-00101229'
		AND t3.f350_fecha = '2025/02/28'
		AND t3.f350_total_db = 100

"""

    cursor.execute(query)
    
    rows = fetch_rows_as_dict(cursor)
    conn.close()
    
    return {"documentos": rows}