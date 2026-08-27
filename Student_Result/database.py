import mysql.connector


def get_connection():
    connection = mysql.connector.connect(
        host="localhost",
        user="root",
        password="",
        database="student_result"
    )

    return connection


connection = get_connection()

print("Database connected successfully!")

connection.close()