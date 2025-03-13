from fastapi import FastAPI, Query, HTTPException
from typing import Optional
import pyodbc
from fastapi.responses import JSONResponse

app = FastAPI()

# 🔹 Conexión a la base de datos
conn_str = (
    r'DRIVER={ODBC Driver 17 for SQL Server};'
    r'SERVER=db02.siesacloud.local;'  
    r'DATABASE=UnoEE_Merkahorro_Real;'  
    r'UID=merkahorroapp;'  
    r'PWD=Merkahorro$21$%;'  
    r'TrustServerCertificate=yes;'
)

@app.get("/documentoss")
def get_documentos(
    f_tercero_id: Optional[str] = Query(None, description="NIT del proveedor para filtrar"),
    limit: int = Query(3000, description="Número máximo de registros", ge=1, le=11115)
):
    """
    Endpoint para consultar comprobantes de egreso agrupados por número de comprobante,
    mostrando cada valor y sumando al final.
    """
    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()

            # Consulta SQL
            query = """
                SELECT TOP (?) 
                    t1.f_docto_egreso, 
                    MAX(t1.f_fecha_docto_egreso) AS f_fecha_docto_egreso, 
                    MAX(t1.f_razon) AS f_razon, 
                    MAX(t1.f_valor_docto) AS f_valor_docto, 
                    t1.f_vlr_bruto, 
                    t1.f_iva, 
                    t1.f_vlr_cxp_alt AS rete_iva, 
                    t1.f_descuento_pp AS rete_ica, 
                    t1.f_valor_ret AS rete_fuente, 
                    t1.f_vlr_cxp AS valor_pagado,
                    SUM(t1.f_vlr_bruto) AS total_vlr_bruto, 
                    SUM(t1.f_vlr_cxp_alt) AS total_rete_iva, 
                    SUM(t1.f_descuento_pp) AS total_rete_ica, 
                    SUM(t1.f_valor_ret) AS total_rete_fuente, 
                    SUM(t1.f_vlr_cxp) AS total_valor_pagado,
                    STRING_AGG(t1.f_docto_sa, ' / ') AS d_cruce_m_pago,
                    MAX(t2.f_telefono) AS f_telefono,
                    MAX(t2.f_municipio_desc) AS f_municipio_desc,
                    MAX(t2.f_direccion) AS f_direccion,
                    MAX(t2.f_email) AS f_email,
                    MAX(t1.f_id_banco) + ' - ' + MAX(t1.f_desc_banco) AS banco,
                    MAX(t1.f_tipo_cta) + ' - ' + MAX(t1.f_dato_cuenta) AS cuenta_corriente
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
            query += " GROUP BY t1.f_docto_egreso, t1.f_vlr_bruto, t1.f_iva, t1.f_vlr_cxp_alt, t1.f_descuento_pp, t1.f_valor_ret, t1.f_vlr_cxp"
            query += " ORDER BY MAX(t1.f_fecha_docto_egreso) DESC"

            print(f"📌 SQL Query: {query}")
            print(f"📌 Parámetros: {params}")

            # Ejecutar consulta
            cursor.execute(query, params)
            rows = fetch_rows_as_dict(cursor)

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
                    "D.CRUCE/M.PAGO": row["d_cruce_m_pago"],  # 🔹 Nueva columna
                    "Valores": {
                        "Valor Bruto": row["f_vlr_bruto"],
                        "IVA": row["f_iva"],
                        "Rete IVA": row["rete_iva"],
                        "Rete ICA": row["rete_ica"],
                        "Rete Fuente": row["rete_fuente"],
                        "Valor Pagado": row["valor_pagado"],
                    },
                    "Totales": {
                        "Total Valor Bruto": row["total_vlr_bruto"],
                        "Total Rete IVA": row["total_rete_iva"],
                        "Total Rete ICA": row["total_rete_ica"],
                        "Total Rete Fuente": row["total_rete_fuente"],
                        "Total Valor Pagado": row["total_valor_pagado"],
                    },
                    "Banco": row["banco"],
                    "Cuenta Corriente": row["cuenta_corriente"],
                }
                documentos_ordenados.append(documento)

        return {"documentos": documentos_ordenados}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})
    
def fetch_rows_as_dict(cursor):
    """ Convierte las filas del cursor en una lista de diccionarios """
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
