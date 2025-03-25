from fastapi import FastAPI, Query, HTTPException
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
import pyodbc
from fastapi.responses import JSONResponse

app = FastAPI()

# Conexión a la base de datos
conn_str = (
    r'DRIVER={ODBC Driver 17 for SQL Server};'
    r'SERVER=siesa-pdn-sqlsw-db2.cw4fp6bllyds.us-east-1.rds.amazonaws.com;'
    r'DATABASE=UnoEE_Merkahorro_Real;'
    r'UID=merkahorroapp;'
    r'PWD=Merkahorro$21$%;'
    r'TrustServerCertificate=yes;'
)

# Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

@app.get("/")
def read_root():
    return {"mensaje": "API en funcionamiento. Usa /documentosfnd para obtener documentos."}

@app.get("/documentosfnd")
def get_documentos(
    nit_tercero_docto: Optional[str] = Query(None, description="NIT del proveedor para filtrar"),
    fecha: Optional[str] = Query(None, description="Fecha del comprobante (YYYY-MM-DD)"),
    limit: int = Query(3000, description="Número máximo de registros", ge=1, le=11115)
):
    """
    Endpoint para consultar comprobantes FND sin duplicados.
    """
    try:
        with pyodbc.connect(conn_str, timeout=10) as conn:
            cursor = conn.cursor()

            query = f"""
                SELECT TOP {limit}  
                    t1.fecha_docto,
                    t1.tipo_docto,
                    t1.id_moneda_docto,
                    t1.razon_social_tercero_docto,
                    t1.tasa_conv,
                    t1.id_servicio,
                    t1.vlr_bruto,
                    t1.vlr_dscto,
                    t1.vlr_imp,
                    t1.vlr_neto,
                    t1.notas,
                    t2.f_fe_descripcion,
                    t2.f_docto_causacion,
                    t200.f_direccion
                FROM [UnoEE_Merkahorro_Real].[dbo].[BI_T320_2] t1
                OUTER APPLY (
                    SELECT TOP 1 f_docto_causacion, f_fe_descripcion, f_fecha_docto_causacion
                    FROM [UnoEE_Merkahorro_Real].[dbo].[BI_T363]
                    WHERE f_notas = t1.notas
                    ORDER BY f_docto_causacion DESC
                ) t2
                OUTER APPLY (
                    SELECT TOP 1 f_direccion
                    FROM [UnoEE_Merkahorro_Real].[dbo].[SE_T200]
                    WHERE f_tercero_id = t1.nit_tercero_docto
                ) t200
                WHERE t2.f_docto_causacion IS NOT NULL
            """
            params = []

            if nit_tercero_docto:
                query += " AND t1.nit_tercero_docto = ?"
                params.append(nit_tercero_docto.strip())

            if fecha:
                query += " AND CONVERT(DATE, t2.f_fecha_docto_causacion) = ?"
                params.append(fecha.strip())

            query += " ORDER BY t1.fecha_docto DESC, t2.f_docto_causacion DESC"

            cursor.execute(query, params)
            rows = fetch_rows_as_dict(cursor)

            if not rows:
                return {"mensaje": "No se encontraron comprobantes para este ID y fecha"}

            documentos_ordenados = [
                {
                    "Número": row["f_docto_causacion"],
                    "Fecha": row["fecha_docto"],
                    "Proveedor": row["razon_social_tercero_docto"],
                    "Tipo": row["tipo_docto"],
                    "Moneda": row["id_moneda_docto"],
                    "Cantidad": row["tasa_conv"],
                    "Servicio": row["id_servicio"],
                    "Valor Bruto": row["vlr_bruto"],
                    "Valor Descuento": row["vlr_dscto"],
                    "Valor Impuesto": row["vlr_imp"],
                    "Valor Neto": row["vlr_neto"],
                    "Notas": row["notas"],
                    "Tipo Cliente": row["f_fe_descripcion"],
                    "Dirección": row["f_direccion"]
                }
                for row in rows
            ]

        return {"documentos": documentos_ordenados}

    except pyodbc.OperationalError as db_err:
        return JSONResponse(status_code=500, content={"error": "Error de conexión a la base de datos", "detalle": str(db_err)})
    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

@app.get("/fechasfnd")
def get_fechas_disponibles(f_tercero_id: str = Query(..., description="ID del tercero para obtener fechas")):
    """
    Endpoint para obtener todas las fechas disponibles para un ID de tercero.
    """
    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()

            query = """
                SELECT DISTINCT CONVERT(VARCHAR, t1.f_fecha_docto_egreso, 23) AS fecha
                FROM [UnoEE_Merkahorro_Real].[dbo].[BI_T363] t1
                LEFT JOIN [UnoEE_Merkahorro_Real].[dbo].[SE_T200] t2 
                    ON t1.f_beneficiario = t2.f_tercero
                WHERE t2.f_tercero_id = ?
                ORDER BY fecha DESC
            """
            cursor.execute(query, (f_tercero_id,))
            rows = cursor.fetchall()

            fechas = [row[0] for row in rows]

            if not fechas:
                return {"mensaje": "No hay fechas disponibles para este ID"}

            return {"fechas": fechas}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})

def fetch_rows_as_dict(cursor):
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
