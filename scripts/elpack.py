import pandas as pd
from scipy.sparse import csr_matrix
import numpy as np

# Указываем путь к вашему CSV файлу
file_path = r"C:\MISIS\Attractions_recommendation_system\user_ratings.csv"

# Считываем данные из CSV с разделителем ;
df = pd.read_csv(file_path, sep=';')

# Проверим, что считано из файла
print("Данные, считанные из файла:")
print(df.head())

# Убираем первый столбец (ID достопримечательностей) и строки с ID пользователей, если они есть
df_numeric = df.iloc[:, 1:].apply(pd.to_numeric, errors='coerce')

# Если данные пустые, выводим сообщение
if df_numeric.empty:
    print("Таблица пустая или не удается считать данные.")
else:
    # Преобразуем таблицу в разреженную матрицу формата CSR (ELPACK)
    matrix_data = df_numeric.values
    sparse_matrix = csr_matrix(matrix_data)

    # Получаем индексы ненулевых элементов
    row, col = sparse_matrix.nonzero()  # Получаем индексы строк и столбцов
    ratings = sparse_matrix.data  # Получаем значения (оценки)

    # Создаем DataFrame для сохранения в базу данных
    ratings_df = pd.DataFrame({
        'attraction_id': row + 1,  # Добавляем 1, так как индексация начинается с 0
        'user_id': col + 1,        # Добавляем 1, так как индексация начинается с 0
        'rating': ratings
    })

    # Сохраняем таблицу в CSV файл, чтобы загрузить в БД
    csv_file_path = r"C:\MISIS\Attractions_recommendation_system\ratings_table.csv"
    ratings_df.to_csv(csv_file_path, index=False)

    print(f"\nТаблица с координатами и значениями сохранена в файл {csv_file_path}")

    # Загружаем сохранённую разреженную матрицу для проверки
    print("\nСодержимое таблицы (для проверки):")
    print(ratings_df.head())
