def operate_columns(df, lambda_func, new_col_name):
    """
    Operar sobre múltiples columnas usando una función lambda.

    Parameters:
        lambda_func (callable): Función lambda que accede directamente a las columnas del DataFrame por nombre.
        new_col_name (str): Nombre de la nueva columna que se creará con el resultado.

    Returns:
        pandas.DataFrame: DataFrame con la nueva columna añadida.
    """
    # Aplicar la función lambda directamente accediendo a las columnas del DataFrame
    df[new_col_name] = lambda_func(df)

    return df


def filter_values(df, lambda_func, cols):
    """
    Filtrar valores en el DataFrame basándose en una función lambda.

    Parameters:
        lambda_func (callable): Función lambda que devuelve True o False para cada fila.
        cols (list): Lista de nombres de las columnas a involucrar en la operación de filtrado.

    Returns:
        pandas.DataFrame: DataFrame filtrado.
    """
    df = df[df.apply(lambda row: lambda_func(*[row[col] for col in cols]), axis=1)]
    return df
