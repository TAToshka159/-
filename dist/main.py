import sys
import re
import os
import sqlite3
from PyQt6.QtWidgets import (QApplication, QMainWindow, QVBoxLayout, QWidget,
                             QPushButton, QLineEdit, QLabel, QMessageBox,
                             QTableWidget, QTableWidgetItem, QFileDialog, QFormLayout, QDialog, QComboBox, QCheckBox)
from PyQt6.QtCore import Qt
import pandas as pd


def connect_db():
    connection = sqlite3.connect("warehouse.db")
    cursor = connection.cursor()
    return connection, cursor


def create_tables():
    connection, cursor = connect_db()

    cursor.execute('''CREATE TABLE IF NOT EXISTS Пользователи (
                        ID_пользователя INTEGER PRIMARY KEY,
                        Логин TEXT UNIQUE NOT NULL,
                        Пароль TEXT NOT NULL,
                        Роль TEXT NOT NULL
                     )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Товары (
                        ID_товара INTEGER PRIMARY KEY,
                        Наименование TEXT NOT NULL,
                        Вес TEXT NOT NULL,
                        Стоимость TEXT NOT NULL,
                        Количество INTEGER DEFAULT 0  -- Добавлено поле Количество
                     )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS Заказы (
                        ID_заказа INTEGER PRIMARY KEY,
                        ID_пользователя INTEGER,
                        ID_товара INTEGER,
                        Количество INTEGER,
                        Статус TEXT NOT NULL,
                        FOREIGN KEY(ID_пользователя) REFERENCES Пользователи(ID_пользователя),
                        FOREIGN KEY(ID_товара) REFERENCES Товары(ID_товара)
                     )''')

    cursor.execute('''CREATE TABLE IF NOT EXISTS ИсторияИзменений (
                        ID INTEGER PRIMARY KEY,
                        Описание TEXT NOT NULL
                     )''')

    connection.commit()
    connection.close()


create_tables()


def validate_password(password):
    return len(password) >= 6 and re.search(r"[!?:_\-+]", password)


def add_user_to_db(login, password, role="Пользователь"):
    if not validate_password(password):
        QMessageBox.warning(None, "Ошибка",
                            "Пароль должен быть не менее 6 символов и содержать хотя бы один специальный символ (!, ?, :, _, -, +)")
        return False

    connection, cursor = connect_db()
    try:
        cursor.execute("INSERT INTO Пользователи (Логин, Пароль, Роль) VALUES (?, ?, ?)", (login, password, role))
        connection.commit()
        return True
    except sqlite3.IntegrityError:
        QMessageBox.warning(None, "Ошибка", "Логин уже существует!")
        return False
    finally:
        connection.close()


def authenticate_user(login, password):
    if login == "admin" and password == "admin":
        return "Администратор"

    connection, cursor = connect_db()
    cursor.execute("SELECT Роль FROM Пользователи WHERE Логин = ? AND Пароль = ?", (login, password))
    result = cursor.fetchone()
    connection.close()
    return result[0] if result else None


def get_all_products():
    connection, cursor = connect_db()
    cursor.execute("SELECT * FROM Товары")
    products = cursor.fetchall()
    connection.close()
    return products if products else []


def get_all_orders():
    connection, cursor = connect_db()
    cursor.execute(
        "SELECT Заказы.ID_заказа, Пользователи.Логин, Товары.Наименование, Заказы.Количество, Заказы.Статус FROM Заказы "
        "JOIN Пользователи ON Заказы.ID_пользователя = Пользователи.ID_пользователя "
        "JOIN Товары ON Заказы.ID_товара = Товары.ID_товара")
    orders = cursor.fetchall()
    connection.close()
    return orders


def get_all_users():
    connection, cursor = connect_db()
    cursor.execute("SELECT ID_пользователя, Логин, Роль FROM Пользователи")
    users = cursor.fetchall()
    connection.close()
    return users if users else []


def update_user_role(user_id, new_role):
    connection, cursor = connect_db()
    cursor.execute("UPDATE Пользователи SET Роль = ? WHERE ID_пользователя = ?", (new_role, user_id))
    connection.commit()
    connection.close()


def record_change(description):
    connection, cursor = connect_db()
    cursor.execute("INSERT INTO ИсторияИзменений (Описание) VALUES (?)", (description,))
    connection.commit()
    connection.close()


class RegistrationWindow(QDialog):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Регистрация")
        self.setGeometry(760, 440, 300, 100)
        self.login_field = QLineEdit()
        self.login_field.setPlaceholderText("Логин")
        self.password_field = QLineEdit()
        self.password_field.setPlaceholderText("Пароль")
        self.password_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.register_button = QPushButton("Зарегистрироваться")
        self.register_button.clicked.connect(self.handle_registration)
        layout = QFormLayout()
        layout.addRow("Логин", self.login_field)
        layout.addRow("Пароль", self.password_field)
        layout.addWidget(self.register_button)
        self.setLayout(layout)

    def handle_registration(self):
        login = self.login_field.text()
        password = self.password_field.text()
        if login and password:
            if add_user_to_db(login, password):
                QMessageBox.information(self, "Успех", "Регистрация прошла успешно!")
                self.close()
        else:
            QMessageBox.warning(self, "Ошибка", "Заполните все поля")


class LoginWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Вход в систему")
        self.setGeometry(760, 440, 300, 200)
        self.login_field = QLineEdit(self)
        self.login_field.setPlaceholderText("Логин")
        self.password_field = QLineEdit(self)
        self.password_field.setPlaceholderText("Пароль")
        self.password_field.setEchoMode(QLineEdit.EchoMode.Password)
        self.login_button = QPushButton("Войти", self)
        self.login_button.clicked.connect(self.handle_login)
        self.register_button = QPushButton("Регистрация", self)
        self.register_button.clicked.connect(self.open_registration)
        layout = QVBoxLayout()
        layout.addWidget(QLabel("Логин"))
        layout.addWidget(self.login_field)
        layout.addWidget(QLabel("Пароль"))
        layout.addWidget(self.password_field)
        layout.addWidget(self.login_button)
        layout.addWidget(self.register_button)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def handle_login(self):
        login = self.login_field.text()
        password = self.password_field.text()
        role = authenticate_user(login, password)
        if role:
            QMessageBox.information(self, "Успех", f"Вход выполнен. Роль: {role}")
            self.main_window = MainWindow(role, login)
            self.main_window.show()
            self.close()
        else:
            QMessageBox.warning(self, "Ошибка", "Неверный логин или пароль")

    def open_registration(self):
        self.registration_window = RegistrationWindow()
        self.registration_window.exec()


class MainWindow(QMainWindow):
    def __init__(self, role, username):
        super().__init__()
        self.setWindowTitle("Система учета товаров на складе")
        self.setGeometry(560, 240, 800, 600)
        self.username = username
        self.user_id = None

        connection, cursor = connect_db()
        cursor.execute("SELECT ID_пользователя FROM Пользователи WHERE Логин = ?", (username,))
        user = cursor.fetchone()
        if user:
            self.user_id = user[0]
        connection.close()

        self.buttons_layout = QVBoxLayout()

        if role == "Администратор":
            self.product_table = QTableWidget()
            self.product_table.setColumnCount(4)
            self.product_table.setHorizontalHeaderLabels(["ID", "Наименование", "Вес", "Стоимость"])
            self.load_products(hide_id=False)
            self.load_products()
        elif role == "Сотрудник":
            self.product_table = QTableWidget()
            self.product_table.setColumnCount(5)
            self.product_table.setHorizontalHeaderLabels(["ID заказа", "Пользователь", "Товар", "Количество", "Статус"])
            self.load_orders()
        elif role == "Пользователь":
            self.product_table = QTableWidget()
            self.product_table.setColumnCount(4)
            self.product_table.setHorizontalHeaderLabels(["Наименование", "Вес", "Стоимость"])
            if role == "Пользователь":
                self.load_products(hide_id=True)
            else:
                self.load_products(hide_id=False)

        self.setup_buttons(role)

        layout = QVBoxLayout()
        layout.addWidget(self.product_table)
        layout.addLayout(self.buttons_layout)
        container = QWidget()
        container.setLayout(layout)
        self.setCentralWidget(container)

    def setup_buttons(self, role):
        if role == "Администратор":
            self.add_product_button = QPushButton("Добавить товар")
            self.add_product_button.clicked.connect(self.add_product)
            self.buttons_layout.addWidget(self.add_product_button)

            self.edit_product_button = QPushButton("Редактировать товар")
            self.edit_product_button.clicked.connect(self.edit_product)
            self.buttons_layout.addWidget(self.edit_product_button)

            self.delete_product_button = QPushButton("Удалить товар")
            self.delete_product_button.clicked.connect(self.delete_product)
            self.buttons_layout.addWidget(self.delete_product_button)

            self.manage_users_button = QPushButton("Управление пользователями")
            self.manage_users_button.clicked.connect(self.manage_users)
            self.buttons_layout.addWidget(self.manage_users_button)

            self.view_changes_button = QPushButton("Просмотр изменений")
            self.view_changes_button.clicked.connect(self.view_changes)
            self.buttons_layout.addWidget(self.view_changes_button)

            self.create_stock_report_button = QPushButton("Отчёт о состояние склада")
            self.create_stock_report_button.clicked.connect(self.generate_stock_report)
            self.buttons_layout.addWidget(self.create_stock_report_button)


        elif role == "Сотрудник":
            self.update_status_button = QPushButton("Обновить статус заказа")
            self.update_status_button.clicked.connect(self.update_order_status)
            self.generate_report_button = QPushButton("Сформировать отчет")
            self.generate_report_button.clicked.connect(self.generate_report)
            self.issue_receipt_button = QPushButton("Выдать чек")
            self.issue_receipt_button.clicked.connect(self.issue_receipt)

            self.buttons_layout.addWidget(self.update_status_button)
            self.buttons_layout.addWidget(self.generate_report_button)
            self.buttons_layout.addWidget(self.issue_receipt_button)


        elif role == "Пользователь":
            self.make_order_button = QPushButton("Сделать заказ")
            self.make_order_button.clicked.connect(self.make_order)
            self.view_my_orders_button = QPushButton("Мои заказы")
            self.view_my_orders_button.clicked.connect(self.view_my_orders)
            self.cancel_order_button = QPushButton("Отменить заказ")
            self.cancel_order_button.clicked.connect(self.cancel_order)

            self.buttons_layout.addWidget(self.make_order_button)
            self.buttons_layout.addWidget(self.view_my_orders_button)
            self.buttons_layout.addWidget(self.cancel_order_button)

        self.logout_button = QPushButton("Выйти из аккаунта")
        self.logout_button.clicked.connect(self.logout)
        self.buttons_layout.addWidget(self.logout_button)

    def load_products(self, hide_id=False):
        products = get_all_products()
        self.product_table.setColumnCount(5 if not hide_id else 4)
        headers = ["ID", "Наименование", "Вес, гр", "Стоимость, руб", "Количество, шт"] if not hide_id else ["Наименование", "Вес, гр", "Стоимость, руб", "Количество, шт"]
        self.product_table.setHorizontalHeaderLabels(headers)
        self.product_table.setRowCount(len(products))

        for row, product in enumerate(products):
            for column, item in enumerate(product):
                if hide_id and column == 0:
                    continue
                display_column = column if not hide_id else column - 1
                self.product_table.setItem(row, display_column, QTableWidgetItem(str(item)))

    def load_orders(self):
        orders = get_all_orders()
        self.product_table.setRowCount(len(orders))
        self.product_table.setColumnCount(5)
        self.product_table.setHorizontalHeaderLabels(["ID заказа", "Пользователь", "Товар", "Количество, шт", "Статус"])

        for row, order in enumerate(orders):
            for column, item in enumerate(order):
                self.product_table.setItem(row, column, QTableWidgetItem(str(item)))

    def manage_users(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Управление пользователями")
        layout = QVBoxLayout()
        users = get_all_users()
        self.user_checkboxes = []
        self.user_roles = {}
        for user in users:
            checkbox = QCheckBox(f"{user[1]} (ID: {user[0]})")
            checkbox.user_id = user[0]
            self.user_checkboxes.append(checkbox)
            layout.addWidget(checkbox)
            role_combo = QComboBox()
            role_combo.addItems(["Пользователь", "Сотрудник", "Администратор"])
            role_combo.setCurrentText(user[2])
            self.user_roles[user[0]] = role_combo
            layout.addWidget(role_combo)
        delete_button = QPushButton("Удалить выбранных пользователей")
        update_roles_button = QPushButton("Обновить роли пользователей")

        def handle_delete():
            to_delete = [cb.user_id for cb in self.user_checkboxes if cb.isChecked()]
            connection, cursor = connect_db()
            cursor.executemany("DELETE FROM Пользователи WHERE ID_пользователя = ?",
                               [(user_id,) for user_id in to_delete])
            connection.commit()
            connection.close()
            QMessageBox.information(self, "Успех", "Пользователи удалены")
            dialog.accept()

        def handle_update_roles():
            connection, cursor = connect_db()
            for user_id, role_combo in self.user_roles.items():
                new_role = role_combo.currentText()
                cursor.execute("UPDATE Пользователи SET Роль = ? WHERE ID_пользователя = ?", (new_role, user_id))
            connection.commit()
            connection.close()
            QMessageBox.information(self, "Успех", "Роли обновлены")
            dialog.accept()

        delete_button.clicked.connect(handle_delete)
        update_roles_button.clicked.connect(handle_update_roles)
        layout.addWidget(delete_button)
        layout.addWidget(update_roles_button)
        dialog.setLayout(layout)
        dialog.exec()

    def delete_product(self):
        connection, cursor = connect_db()
        cursor.execute("SELECT ID_товара, Наименование FROM Товары")
        products = cursor.fetchall()
        connection.close()

        if not products:
            QMessageBox.information(self, "Информация", "На складе нет товаров для удаления.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Удалить товар")
        dialog.setGeometry(760, 440, 400, 200)

        layout = QVBoxLayout()
        product_combo = QComboBox()

        for product_id, product_name in products:
            product_combo.addItem(f"{product_name} (ID: {product_id})", product_id)

        delete_button = QPushButton("Удалить")

        def handle_delete():
            selected_index = product_combo.currentIndex()
            if selected_index == -1:
                QMessageBox.warning(dialog, "Ошибка", "Выберите товар для удаления.")
                return

            selected_product_id = product_combo.itemData(selected_index)

            confirmation = QMessageBox.question(
                self,
                "Подтверждение",
                "Вы уверены, что хотите удалить выбранный товар?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )

            if confirmation == QMessageBox.StandardButton.Yes:
                connection, cursor = connect_db()
                try:
                    cursor.execute("DELETE FROM Товары WHERE ID_товара = ?", (selected_product_id,))
                    connection.commit()
                    QMessageBox.information(self, "Успех", "Товар успешно удалён.")
                    self.load_products(hide_id=False)
                    dialog.accept()
                except sqlite3.Error as e:
                    QMessageBox.warning(self, "Ошибка", f"Ошибка базы данных: {e}")
                finally:
                    connection.close()

        layout.addWidget(product_combo)
        layout.addWidget(delete_button)
        delete_button.clicked.connect(handle_delete)
        dialog.setLayout(layout)
        dialog.exec()

    def add_product(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Добавить товар")
        layout = QFormLayout()

        name_input = QLineEdit()
        weight_input = QLineEdit()
        price_input = QLineEdit()
        quantity_input = QLineEdit()
        submit_button = QPushButton("Добавить")

        def handle_submit():
            name = name_input.text()
            weight = weight_input.text()
            try:
                price = f"{float(price_input.text()):.2f}"
            except ValueError:
                QMessageBox.warning(self, "Ошибка", "Введите корректную цену в формате '100.00'")
                return
            quantity = quantity_input.text()

            if name and weight and price and quantity.isdigit():
                connection, cursor = connect_db()
                cursor.execute(
                    "INSERT INTO Товары (Наименование, Вес, Стоимость, Количество) VALUES (?, ?, ?, ?)",
                    (name, weight, price, int(quantity))
                )
                connection.commit()
                connection.close()
                record_change(f"Добавлен товар: {name} в количестве {quantity}")
                QMessageBox.information(self, "Успех", "Товар добавлен")
                self.load_products()
                dialog.accept()
            else:
                QMessageBox.warning(self, "Ошибка", "Заполните все поля")

        layout.addRow("Наименование:", name_input)
        layout.addRow("Вес, гр:", weight_input)
        layout.addRow("Стоимость, руб:", price_input)
        layout.addRow("Количество, шт:", quantity_input)
        layout.addWidget(submit_button)
        submit_button.clicked.connect(handle_submit)
        dialog.setLayout(layout)
        dialog.exec()

    def edit_product(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Редактировать товар")
        layout = QFormLayout()

        product_id_input = QLineEdit()
        name_input = QLineEdit()
        weight_input = QLineEdit()
        price_input = QLineEdit()
        quantity_input = QLineEdit()
        submit_button = QPushButton("Сохранить изменения")

        def handle_submit():
            product_id = product_id_input.text()
            name = name_input.text()
            weight = weight_input.text()
            try:
                price = f"{float(price_input.text()):.2f}" if price_input.text() else None
            except ValueError:
                QMessageBox.warning(self, "Ошибка", "Введите корректную цену в формате '100.00'")
                return
            quantity = quantity_input.text()

            if product_id and (name or weight or price or quantity.isdigit()):
                connection, cursor = connect_db()
                cursor.execute(
                    "UPDATE Товары SET Наименование = ?, Вес = ?, Стоимость = ?, Количество = ? WHERE ID_товара = ?",
                    (name, weight, price, int(quantity), product_id)
                )
                connection.commit()
                connection.close()
                record_change(f"Изменен товар с ID {product_id}")
                QMessageBox.information(self, "Успех", "Изменения сохранены")
                self.load_products()
                dialog.accept()
            else:
                QMessageBox.warning(self, "Ошибка", "Заполните ID товара и хотя бы одно поле для изменения")

        layout.addRow("ID товара:", product_id_input)
        layout.addRow("Новое наименование:", name_input)
        layout.addRow("Новый вес:", weight_input)
        layout.addRow("Новая стоимость:", price_input)
        layout.addRow("Новое количество:", quantity_input)
        layout.addWidget(submit_button)
        submit_button.clicked.connect(handle_submit)
        dialog.setLayout(layout)
        dialog.exec()

    def update_order_status(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Обновить статус заказа")
        layout = QVBoxLayout()

        orders = get_all_orders()
        order_combo = QComboBox()
        status_combo = QComboBox()
        status_combo.addItems(["Заказ принят", "Идет сбор заказа", "Готов к выдаче", "Выдан"])

        for order in orders:
            order_combo.addItem(
                f"Заказ ID: {order[0]}, Пользователь: {order[1]}, Товар: {order[2]}, Статус: {order[4]}")

        submit_button = QPushButton("Обновить статус")

        def handle_update():
            selected_order_index = order_combo.currentIndex()
            if selected_order_index == -1:
                QMessageBox.warning(self, "Ошибка", "Выберите заказ")
                return

            selected_order_id = orders[selected_order_index][0]
            new_status = status_combo.currentText()

            connection, cursor = connect_db()
            cursor.execute("UPDATE Заказы SET Статус = ? WHERE ID_заказа = ?", (new_status, selected_order_id))
            connection.commit()
            connection.close()

            QMessageBox.information(self, "Успех", "Статус заказа обновлён")

            self.load_orders()
            dialog.accept()

        layout.addWidget(order_combo)
        layout.addWidget(status_combo)
        layout.addWidget(submit_button)
        submit_button.clicked.connect(handle_update)
        dialog.setLayout(layout)
        dialog.exec()

    def issue_receipt(self):
        connection, cursor = connect_db()
        cursor.execute("SELECT DISTINCT Пользователи.ID_пользователя, Пользователи.Логин FROM Заказы "
                       "JOIN Пользователи ON Заказы.ID_пользователя = Пользователи.ID_пользователя")
        users = cursor.fetchall()
        connection.close()

        if not users:
            QMessageBox.information(self, "Информация", "Нет пользователей с заказами.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Выдать чек")
        dialog.setGeometry(760, 440, 400, 200)

        layout = QVBoxLayout()
        user_combo = QComboBox()

        for user_id, user_name in users:
            user_combo.addItem(user_name, user_id)

        confirm_button = QPushButton("Создать чек")

        def generate_receipt():
            selected_user_index = user_combo.currentIndex()
            if selected_user_index == -1:
                QMessageBox.warning(dialog, "Ошибка", "Выберите пользователя для чека.")
                return

            selected_user_id = user_combo.itemData(selected_user_index)

            connection, cursor = connect_db()
            cursor.execute(
                """SELECT Товары.Наименование, Заказы.Количество, Товары.Стоимость, 
                          (Заказы.Количество * Товары.Стоимость) AS Сумма_товара
                   FROM Заказы
                   JOIN Товары ON Заказы.ID_товара = Товары.ID_товара
                   WHERE Заказы.ID_пользователя = ?""",
                (selected_user_id,)
            )
            orders = cursor.fetchall()
            connection.close()

            if not orders:
                QMessageBox.information(dialog, "Информация", "У этого пользователя нет заказов.")
                return

            df_receipt = pd.DataFrame(orders,
                                      columns=["Товар", "Количество, шт", "Цена за единицу, руб", "Сумма товара, руб"])
            total_sum = df_receipt["Сумма товара, руб"].sum()

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить чек",
                "чек.xlsx",
                "Excel Files (*.xlsx);;All Files (*)"
            )

            if not file_path:
                QMessageBox.information(dialog, "Отмена", "Сохранение чека отменено.")
                return

            try:
                with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                    df_receipt.to_excel(writer, sheet_name="Чек", index=False)

                    workbook = writer.book
                    worksheet = workbook["Чек"]
                    worksheet.append(["Общая сумма заказа:", f"{total_sum:.2f} руб"])

                QMessageBox.information(dialog, "Успех", f"Чек успешно сохранён в: {file_path}")
                dialog.accept()
            except Exception as e:
                QMessageBox.warning(dialog, "Ошибка", f"Ошибка при сохранении чека: {str(e)}")

        layout.addWidget(user_combo)
        layout.addWidget(confirm_button)
        confirm_button.clicked.connect(generate_receipt)
        dialog.setLayout(layout)
        dialog.exec()

    def view_orders(self):
        orders = get_all_orders()
        dialog = QDialog(self)
        dialog.setWindowTitle("Список заказов")
        table = QTableWidget(len(orders), 5)
        table.setHorizontalHeaderLabels(["ID", "Пользователь", "Товар", "Количество, шт", "Статус"])
        for row, order in enumerate(orders):
            for column, item in enumerate(order):
                table.setItem(row, column, QTableWidgetItem(str(item)))
        layout = QVBoxLayout()
        layout.addWidget(table)
        dialog.setLayout(layout)
        dialog.exec()

    def make_order(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Сделать заказ")
        dialog.setGeometry(1260, 540, 400, 200)

        layout = QFormLayout()
        product_combo = QComboBox()
        products = get_all_products()
        product_ids = {}

        for product in products:
            product_ids[product[1]] = product[0]
            product_combo.addItem(f"{product[1]} ({product[2]} гр, {product[3]} руб)", product[0])

        quantity_input = QLineEdit()
        quantity_input.setPlaceholderText("Введите количество")

        submit_button = QPushButton("Оформить заказ")

        def handle_submit():
            product_index = product_combo.currentIndex()
            product_id = product_combo.itemData(product_index)
            quantity = quantity_input.text()

            if not quantity.isdigit() or int(quantity) <= 0:
                QMessageBox.warning(self, "Ошибка", "Количество товара должно быть больше 0!")
                return

            if product_id and quantity.isdigit():
                connection, cursor = connect_db()

                cursor.execute("SELECT Количество FROM Товары WHERE ID_товара = ?", (product_id,))
                available_quantity = cursor.fetchone()[0]
                if int(quantity) > available_quantity:
                    QMessageBox.warning(self, "Ошибка", "Недостаточно товара на складе!")
                    return

                cursor.execute(
                    "INSERT INTO Заказы (ID_пользователя, ID_товара, Количество, Статус) VALUES (?, ?, ?, ?)",
                    (self.user_id, product_id, int(quantity), "Заказ принят"))

                cursor.execute("UPDATE Товары SET Количество = Количество - ? WHERE ID_товара = ?",
                               (int(quantity), product_id))
                connection.commit()
                connection.close()

                QMessageBox.information(self, "Успех", "Заказ оформлен")
                self.load_products(hide_id=True)
                dialog.accept()
            else:
                QMessageBox.warning(self, "Ошибка", "Введите корректное количество")

        layout.addRow("Товар:", product_combo)
        layout.addRow("Количество, шт:", quantity_input)
        layout.addWidget(submit_button)
        submit_button.clicked.connect(handle_submit)
        dialog.setLayout(layout)
        dialog.exec()

    def view_my_orders(self):
        connection, cursor = connect_db()
        cursor.execute(
            """SELECT Заказы.ID_заказа, Товары.Наименование, Заказы.Количество, Товары.Стоимость, 
                      (Заказы.Количество * Товары.Стоимость) AS Общая_стоимость
               FROM Заказы
               JOIN Товары ON Заказы.ID_товара = Товары.ID_товара
               WHERE Заказы.ID_пользователя = ?""",
            (self.user_id,)
        )
        orders = cursor.fetchall()
        connection.close()

        dialog = QDialog(self)
        dialog.setWindowTitle("Мои заказы")
        dialog.setGeometry(760, 440, 700, 400)

        table = QTableWidget(len(orders), 5)
        table.setHorizontalHeaderLabels(
            ["ID заказа", "Наименование товара", "Количество, шт", "Цена за единицу, руб", "Стоимость заказа, руб"]
        )

        for row, order in enumerate(orders):
            for column, item in enumerate(order):
                table.setItem(row, column, QTableWidgetItem(str(item)))

        layout = QVBoxLayout()
        layout.addWidget(table)
        dialog.setLayout(layout)
        dialog.exec()

    def cancel_order(self):
        connection, cursor = connect_db()
        cursor.execute(
            """SELECT Заказы.ID_заказа, Товары.Наименование, Заказы.Количество 
               FROM Заказы 
               JOIN Товары ON Заказы.ID_товара = Товары.ID_товара 
               WHERE Заказы.ID_пользователя = ?""",
            (self.user_id,)
        )
        orders = cursor.fetchall()
        connection.close()

        if not orders:
            QMessageBox.information(self, "Информация", "У вас нет заказов для отмены.")
            return

        dialog = QDialog(self)
        dialog.setWindowTitle("Отменить заказ")
        dialog.setGeometry(760, 440, 500, 200)

        layout = QVBoxLayout()
        order_combo = QComboBox()

        for order in orders:
            order_combo.addItem(f"Заказ ID: {order[0]}, Товар: {order[1]}, Количество, шт: {order[2]}")

        confirm_button = QPushButton("Отменить заказ")

        def handle_cancel():
            selected_index = order_combo.currentIndex()
            if selected_index == -1:
                QMessageBox.warning(dialog, "Ошибка", "Выберите заказ для отмены.")
                return

            selected_order_id = orders[selected_index][0]
            selected_product_name = orders[selected_index][1]
            selected_quantity = orders[selected_index][2]

            confirmation = QMessageBox.question(
                self,
                "Подтверждение",
                f"Вы уверены, что хотите отменить заказ '{selected_product_name}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if confirmation == QMessageBox.StandardButton.Yes:
                connection, cursor = connect_db()

                try:
                    cursor.execute(
                        """UPDATE Товары 
                           SET Количество = Количество + ? 
                           WHERE Наименование = ?""",
                        (selected_quantity, selected_product_name)
                    )

                    cursor.execute("DELETE FROM Заказы WHERE ID_заказа = ?", (selected_order_id,))
                    connection.commit()

                    QMessageBox.information(self, "Успех", "Заказ отменен")

                    self.load_products(hide_id=self.user_id is not None)

                except sqlite3.Error as e:
                    QMessageBox.warning(self, "Ошибка", f"Ошибка базы данных: {e}")
                finally:
                    connection.close()

                dialog.accept()

        layout.addWidget(order_combo)
        layout.addWidget(confirm_button)
        confirm_button.clicked.connect(handle_cancel)
        dialog.setLayout(layout)
        dialog.exec()


    def generate_stock_report(self):
        try:
            products = get_all_products()
            if not products:
                QMessageBox.information(self, "Информация", "На складе нет товаров. Отчёт не создан.")
                return

            df = pd.DataFrame(products, columns=["ID", "Наименование", "Вес, гр", "Стоимость, руб", "Количество, шт"])

            df["Стоимость, руб"] = pd.to_numeric(df["Стоимость, руб"], errors="coerce")
            df["Количество, шт"] = pd.to_numeric(df["Количество, шт"], errors="coerce")

            df["Сумма товара, руб"] = (df["Стоимость, руб"] * df["Количество, шт"]).round(2)

            total_sum = df["Сумма товара, руб"].sum()

            report_file, _ = QFileDialog.getSaveFileName(self, "Сохранить отчёт", "Склад_товаров.xlsx",
                                                         "Excel Files (*.xlsx)")

            if not report_file:
                QMessageBox.information(self, "Отмена", "Сохранение отчёта отменено.")
                return

            with pd.ExcelWriter(report_file, engine="openpyxl") as writer:
                df.to_excel(writer, sheet_name="Склад", index=False)

                workbook = writer.book
                summary_sheet = workbook.create_sheet(title="Общая сумма")
                summary_sheet.append(["Общая сумма всех товаров на складе", f"{total_sum:.2f} руб."])

            QMessageBox.information(self, "Успех", f"Отчёт успешно сохранён в {report_file}")

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при создании отчёта: {str(e)}")

    def generate_report(self):
        try:
            orders = get_all_orders()
            if not orders:
                QMessageBox.information(self, "Информация", "Нет заказов для отчёта.")
                return

            df_orders = pd.DataFrame(orders, columns=["ID", "Пользователь", "Товар", "Количество, шт", "Статус"])

            df_orders["Сумма заказа"] = df_orders["Количество, шт"] * df_orders["Товар"].map(
                lambda name: self.get_product_price(name))

            total_sum = df_orders["Сумма заказа"].sum()

            summary = df_orders.groupby(["Пользователь", "Товар"]).agg({
                "Количество, шт": "sum",
                "Сумма заказа": "sum"
            }).reset_index()
            summary.columns = ["Пользователь", "Товар", "Общее количество", "Общая сумма"]

            file_path, _ = QFileDialog.getSaveFileName(
                self,
                "Сохранить отчёт",
                "заказы.xlsx",
                "Excel Files (*.xlsx);;All Files (*)"
            )

            if not file_path:
                QMessageBox.information(self, "Отмена", "Сохранение отчёта отменено.")
                return

            with pd.ExcelWriter(file_path, engine="openpyxl") as writer:
                df_orders.to_excel(writer, sheet_name="Заказы", index=False)
                summary.to_excel(writer, sheet_name="Итоги", index=False)

                workbook = writer.book
                worksheet = workbook.create_sheet(title="Общая сумма")
                worksheet.append(["Общая сумма всех заказов", total_sum])

            QMessageBox.information(self, "Отчёт", f"Отчёт успешно сохранён в: {file_path}")

        except Exception as e:
            QMessageBox.warning(self, "Ошибка", f"Ошибка при создании отчёта: {str(e)}")

    def get_product_price(self, product_name):
        connection, cursor = connect_db()
        cursor.execute("SELECT Стоимость FROM Товары WHERE Наименование = ?", (product_name,))
        result = cursor.fetchone()
        connection.close()
        return float(result[0]) if result else 0

    def view_changes(self):
        connection, cursor = connect_db()
        cursor.execute("SELECT * FROM ИсторияИзменений")
        changes = cursor.fetchall()
        connection.close()
        dialog = QDialog(self)
        dialog.setWindowTitle("История изменений")
        dialog.resize(400, 200)

        table = QTableWidget(len(changes), 2)
        table.setHorizontalHeaderLabels(["ID", "Описание"])
        for row, change in enumerate(changes):
            for column, item in enumerate(change):
                table.setItem(row, column, QTableWidgetItem(str(item)))
        layout = QVBoxLayout()
        layout.addWidget(table)
        dialog.setLayout(layout)
        dialog.exec()

    def logout(self):
        self.close()
        self.login_window = LoginWindow()
        self.login_window.show()


app = QApplication(sys.argv)
login_window = LoginWindow()
login_window.show()
app.exec()
