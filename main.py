from fastapi import FastAPI, Query, HTTPException
from typing import Optional
from fastapi.middleware.cors import CORSMiddleware
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

# 🔹 Configuración de CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  
    allow_credentials=True,
    allow_methods=["*"],  
    allow_headers=["*"],  
)

@app.get("/documentos")
def get_documentos(
    f_tercero_id: Optional[str] = Query(None, description="NIT del proveedor para filtrar"),
    fecha: Optional[str] = Query(None, description="Fecha del comprobante (YYYY-MM-DD)"),
    limit: int = Query(3000, description="Número máximo de registros", ge=1, le=11115)
):
    """
    Endpoint para consultar comprobantes de egreso filtrados por NIT y fecha.
    Separa cada factura por su Número (f_docto_egreso).
    """
    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()

            # 🔹 Consulta SQL corregida para agrupar por Número de Comprobante de Egreso
            query = """
                SELECT TOP (?) 
                    t1.f_docto_egreso, 
                    t1.f_fecha_docto_egreso, 
                    t1.f_razon, 
                    t1.f_valor_docto, 
                    COALESCE(t1.f_vlr_bruto, 0) AS f_vlr_bruto, 
                    COALESCE(t1.f_iva, 0) AS f_iva, 
                    COALESCE(t1.f_vlr_cxp_alt, 0) AS rete_iva, 
                    COALESCE(t1.f_descuento_pp, 0) AS rete_ica, 
                    COALESCE(t1.f_valor_ret, 0) AS rete_fuente, 
                    COALESCE(t1.f_vlr_cxp, 0) AS valor_pagado,
                    STRING_AGG(t1.f_docto_sa, ' / ') AS d_cruce_m_pago,
                    t2.f_telefono,
                    t2.f_municipio_desc AS Ciudad,
                    t2.f_direccion AS Dirección,
                    t2.f_email AS Email,
                    t1.f_id_banco AS Codigo_Banco,
                    t1.f_desccta AS Cuenta_Bancaria,
                    t1.f_tipo_cta + ' - ' + t1.f_dato_cuenta AS Cuenta_Corriente
                FROM [UnoEE_Merkahorro_Real].[dbo].[BI_T363] t1
                LEFT JOIN [UnoEE_Merkahorro_Real].[dbo].[SE_T200] t2
                ON t1.f_beneficiario = t2.f_tercero
                WHERE t1.f_docto_egreso IS NOT NULL
            """
            params = [limit]

            if f_tercero_id:
                query += " AND t2.f_tercero_id = ?"
                params.append(f_tercero_id.strip())

            if fecha:
                query += " AND CONVERT(DATE, t1.f_fecha_docto_egreso) = ?"
                params.append(fecha.strip())

            query += """
                GROUP BY t1.f_docto_egreso, t1.f_fecha_docto_egreso, t1.f_razon, t1.f_valor_docto, 
                         t1.f_vlr_bruto, t1.f_iva, t1.f_vlr_cxp_alt, t1.f_descuento_pp, 
                         t1.f_valor_ret, t1.f_vlr_cxp, t2.f_telefono, t2.f_municipio_desc, 
                         t2.f_direccion, t2.f_email, t1.f_id_banco, t1.f_desccta, 
                         t1.f_tipo_cta, t1.f_dato_cuenta
                ORDER BY t1.f_docto_egreso DESC
            """

            cursor.execute(query, params)
            rows = fetch_rows_as_dict(cursor)

            if not rows:
                return {"mensaje": "No se encontraron comprobantes de egreso para este ID y fecha"}

            # 🔹 JSON garantizado con `Valores`
            documentos_ordenados = []
            for row in rows:
                documento = {
                    "Número": row["f_docto_egreso"],
                    "Fecha": row["f_fecha_docto_egreso"],
                    "Proveedor": row["f_razon"],
                    "Dirección": row["Dirección"],
                    "Ciudad": row["Ciudad"],
                    "Teléfono": row["f_telefono"],
                    "Email": row["Email"],
                    "Valor Consignado": row["f_valor_docto"],
                    "D.CRUCE/M.PAGO": row["d_cruce_m_pago"],
                    "Banco": f"{row['Codigo_Banco']} - {row['Cuenta_Bancaria']}",
                    "Código Banco": row["Codigo_Banco"],
                    "Cuenta Bancaria": row["Cuenta_Bancaria"],
                    "Cuenta Corriente": row["Cuenta_Corriente"],
                    "Valores": {
                        "Valor Bruto": row["f_vlr_bruto"],
                        "IVA": row["f_iva"],
                        "Rete IVA": row["rete_iva"],
                        "Rete ICA": row["rete_ica"],
                        "Rete Fuente": row["rete_fuente"],
                        "Valor Pagado": row["valor_pagado"],
                    }
                }
                documentos_ordenados.append(documento)

        return {"documentos": documentos_ordenados}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})




@app.get("/fechas")
def get_fechas_disponibles(f_tercero_id: str = Query(..., description="ID del tercero para obtener fechas")):
    """
    Endpoint para obtener todas las fechas disponibles para un ID de tercero.
    """
    try:
        with pyodbc.connect(conn_str) as conn:
            cursor = conn.cursor()

            # 🔹 Consulta SQL actualizada con JOIN para asegurar que encuentra el ID en ambas tablas
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

            # Convertir filas a lista de fechas
            fechas = [row[0] for row in rows]

            if not fechas:
                return {"mensaje": "No hay fechas disponibles para este ID"}

            return {"fechas": fechas}

    except Exception as e:
        return JSONResponse(status_code=500, content={"error": str(e)})


# 🔹 Función para convertir filas SQL en diccionarios de Python
def fetch_rows_as_dict(cursor):
    columns = [column[0] for column in cursor.description]
    return [dict(zip(columns, row)) for row in cursor.fetchall()]
