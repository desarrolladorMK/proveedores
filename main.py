from fastapi import FastAPI, Query, HTTPException
from typing import Optional
import pyodbc
from fastapi.responses import JSONResponse

app = FastAPI()

# Cadena de conexión a la base de datos
conn_str = "DRIVER={ODBC Driver 17 for SQL Server};SERVER=tu_servidor;DATABASE=UnoEE_Merkahorro_Real;UID=tu_usuario;PWD=tu_contraseña"
@app.get("/hello")
def hello_world():
    return {"message": "Hello World"}
@app.get("/documentos")
def get_documentos(
    f_tercero_id: Optional[str] = Query(None, description="NIT del proveedor para filtrar"),
   limit: int = Query(1115, description="Número máximo de registros", ge=1, le=11115)
):
    """
    Endpoint para consultar comprobantes de egreso agrupados por número de comprobante,
    sumando los valores numéricos correspondientes.
    """
    try:
        with pyodbc.connect(conn_str) as conn:  # Asegúrate de que conn_str esté definido
            cursor = conn.cursor()

            # Consulta SQL con agrupación por número de comprobante
            query = """
                SELECT TOP (?) 
                    t1.f_docto_egreso, 
                    MAX(t1.f_fecha_docto_egreso) AS f_fecha_docto_egreso, 
                    MAX(t1.f_razon) AS f_razon, 
                    MAX(t1.f_valor_docto) AS f_valor_docto, 
                    SUM(t1.f_vlr_bruto) AS f_vlr_bruto, 
                    SUM(t1.f_iva) AS f_iva, 
                    SUM(t1.f_vlr_cxp_alt) AS rete_iva, 
                    SUM(t1.f_descuento_pp) AS rete_ica, 
                    SUM(t1.f_valor_ret) AS rete_fuente, 
                    SUM(t1.f_vlr_cxp) AS valor_pagado,
                    MAX(t2.f_telefono) AS f_telefono,
                    MAX(t2.f_municipio_desc) AS f_municipio_desc,
                    MAX(t2.f_direccion) AS f_direccion,
                    MAX(t2.f_email) AS f_email
                FROM [UnoEE_Merkahorro_Real].[dbo].[BI_T363] t1
                LEFT JOIN [UnoEE_Merkahorro_Real].[dbo].[SE_T200] t2
                ON t1.f_beneficiario = t2.f_tercero
                WHERE t1.f_docto_egreso IS NOT NULL
            """
            params = [limit]

            # Filtro opcional por NIT del proveedor
            if f_tercero_id:
                query += " AND t2.f_tercero_id = ?"
                params.append(f_tercero_id.strip())

            # Agrupar por número de comprobante y ordenar por fecha descendente
            query += " GROUP BY t1.f_docto_egreso ORDER BY MAX(t1.f_fecha_docto_egreso) DESC"

            print(f"📌 SQL Query: {query}")
            print(f"📌 Parámetros: {params}")

            # Ejecutar consulta
            cursor.execute(query, params)
            rows = fetch_rows_as_dict(cursor)  # Asegúrate de que esta función esté definida

            if not rows:
                return {"mensaje": "No se encontraron comprobantes de egreso para este NIT"}

            # Estructurar los datos en un formato legible
            documentos_ordenados = []
            for row in rows:
                documento = {
                    "Número": row["f_docto_egreso"],
                    "Fecha": row["f_fecha_docto_egreso"],
                    "Proveedor": row["f_razon"],
                    "Valor Consignado": row["f_valor_docto"],
                    "Valor Bruto": row["f_vlr_bruto"],
                    "IVA": row["f_iva"],
                    "Rete IVA": row["rete_iva"],
                    "Rete ICA": row["rete_ica"],
                    "Rete Fuente": row["rete_fuente"],
                    "Valor Pagado": row["valor_pagado"],
                    "Teléfono": row["f_telefono"],
                    "Ciudad": row["f_municipio_desc"],
                    "Dirección": row["f_direccion"],
                    "Email": row["f_email"],
                }
                documentos_ordenados.append(documento)

        return {"documentos": documentos_ordenados}

    except pyodbc.Error as e:
        print(f"❌ Error en la base de datos: {e}")
        raise HTTPException(status_code=500, detail=f"Error en la base de datos: {str(e)}")
    except Exception as e:
        print(f"❌ Error en la API: {e}")
        return JSONResponse(status_code=500, content={"error": str(e)})

# Asegúrate de tener esta función definida si no está en tu código original
def fetch_rows_as_dict(cursor):
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]