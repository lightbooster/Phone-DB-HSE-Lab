import sqlite3
import keyboard
from os import system, name
from tabulate import tabulate as tb
import datetime
from dateutil.relativedelta import relativedelta


def try_except_decorator(func):
    def wrapper(*args, **kwargs):
        try:
            return func(*args, *kwargs)
        except Exception as e:
            print(" *** ERROR *** : ", e, " in ", func.__name__)
            print("P.s. You may need to press [q] for exit\n")
            return -1
    return wrapper


class ContactsDB:
    """
    Low-level api for work with the Contacts Data Base
    """

    def __init__(self, db_name="phones_db.sqlite", auto_save=True):
        """
        :param db_name: name of DB file
        :param auto_save: should PhoneDB save changes on destroy
        """
        self._auto_save = auto_save
        self._search_params_keys = ("person_ID", "first_name", "last_name", "birthday", "is_favourite",
                                    "phone_ID", "phone_owner_ID", "phone_number", "phone_description",
                                    "age_from", "age_to", "is_nearest_birthday")

        self.SQL_connection = sqlite3.connect(db_name, check_same_thread=False)
        self.SQL_coursor = self.SQL_connection.cursor()
        self._clean_db()

        if self._create_tables() == -1:
            print("System: can not create DB")
            exit()

    def __del__(self):
        if self._auto_save:
            self._save()
        self.SQL_connection.close()

    @try_except_decorator
    def _save(self) -> int:
        """
        Save changes to DB file
        :return 1 - success, (-1) - error
        """
        self.SQL_connection.commit()
        print("System: DB saved")
        return 1

    @try_except_decorator
    def _create_tables(self) -> int:
        """
        Creates two tables Persons and Phone
        which are related by an phone owner id (one to many)
        :return None (void):
        """
        self.SQL_coursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS Persons 
            (id INTEGER PRIMARY KEY,
            first_name TEXT,
            last_name TEXT,
            birthday TEXT,
            is_favourite INTEGER)
            ''')
        self.SQL_coursor.execute(
            '''
            CREATE TABLE IF NOT EXISTS Phones 
            (id INTEGER PRIMARY KEY,
            owner INTEGER,
            number TEXT,
            description TEXT,
            foreign key (owner) references Persons(id))
            '''
        )
        return 1

    @try_except_decorator
    def _read(self, search_params: dict):
        """
        Read information from joined Persons and Phones tables
        :param search_params: dict where only necessary search params are
        keys: person_ID (INT), first_name (STR), last_name (STR), birthday(day/month) (STR),
        is_favourite (BOOL), phone_ID (INT), phone_owner_ID (INT), phone_number (STR), phone_description (STR),
        age_from (INT), age_to (INT), is_nearest_birthday (BOOL)

        :return: Iterable Object of Tuples (table rows) or 0 in error case
        """
        sql_search = self.__create_search_tuple(search_params)
        sql_result = self.SQL_coursor.execute(
            '''
            SELECT * FROM Persons, Phones
            WHERE Persons.id = Phones.owner
            AND (? IS NULL OR Persons.id = ?)
            AND (? IS NULL OR Persons.first_name = ?)
            AND (? IS NULL OR Persons.last_name = ?)
            AND (? IS NULL OR Persons.birthday LIKE ?)
            AND (? IS NULL OR Persons.is_favourite = ?)
            AND (? IS NULL OR Phones.id = ?)
            AND (? IS NULL OR Phones.owner = ?)
            AND (? IS NULL OR Phones.number = ?)
            AND (? IS NULL OR Phones.description = ?)
            ORDER BY Persons.first_name, Persons.last_name
            ''', sql_search[:18]
        ).fetchall()

        # filter by date of birthday
        today = datetime.datetime.now()
        filtered_data = list()
        for record in sql_result:
            if record[3] is None:
                if sql_search[18] is None and sql_search[20] is None:
                    filtered_data.append(record)
                continue
            record_birthday = datetime.datetime.strptime(record[3] + " 00:00:00", '%d-%m-%Y %H:%M:%S')
            this_year_birthday = datetime.datetime.strptime(record[3][:-4] +
                                                            str(today.year) + " 00:00:00", '%d-%m-%Y %H:%M:%S')
            difference_in_years = abs(relativedelta(record_birthday, today).years)
            difference_in_days = this_year_birthday - today
            # by the age
            if sql_search[18] is not None and sql_search[19] is not None \
                    and not (sql_search[18] <= difference_in_years <= sql_search[19]):
                continue

            # by the nearest birthday
            if sql_search[20] and (difference_in_days.days > 30 or difference_in_days.days < 0):
                continue

            # add age value
            changed_record = list(record)
            changed_record[3] += "\n(" + str(difference_in_years) + " years)"
            filtered_data.append(tuple(changed_record))
        return filtered_data

    @try_except_decorator
    def __create_search_tuple(self, search_params: dict) -> tuple:
        """
        Create tuple with fixed length from the dict of search parameters
        :param search_params: dict where only necessary search params are
        :return: suitable for use in SQL code tuple
        """
        new_search_list = list()
        for param in self._search_params_keys:
            element = search_params[param] if param in search_params.keys() else None
            new_search_list.append(element)
            # need double values because there are 2 '?' in SQL search condition
            if self._search_params_keys.index(param) < 9:
                new_search_list.append(element)
        return tuple(new_search_list)

    @try_except_decorator
    def _is_name_exist(self, first_name: str, last_name: str):
        """
        Check the uniqueness of Person Name
        :param first_name: first Person name
        :param last_name: last Person name
        :return: 1 - name exists, 0 - name doesn't exist, (-1) - error
        """

        return len(self._read({'first_name': first_name, 'last_name': last_name})) > 0

    @try_except_decorator
    def _insert_record(self, person_info: tuple, phone_info: tuple):
        """
        Create a new record about the person and his/her first contact
        :param person_info: person_info - a row of data for Persons table EXCEPT person_ID
        :param phone_info: phone_info - a row of data for Phones table EXCEPT phone_ID and owner_ID
        :return: tuple(new person id, new phone id) - success, (-1) - error
        """
        new_person_id = self.__insert_person(person_info)
        new_phone_info = tuple([new_person_id] + list(phone_info[:]))
        new_phone_id = self._insert_phone(new_phone_info)
        return new_person_id, new_phone_id

    @try_except_decorator
    def __insert_person(self, person_info: tuple) -> int:
        """
        Insert person information to the DB
        Private method to except the case of adding a person without a phone number
        :param person_info - a row of data for Persons table EXCEPT id
        :return: inserted person ID - success, (-1) - error
        """
        self.SQL_coursor.execute(
            '''
            INSERT INTO Persons
            VALUES ((SELECT MAX(id) from Persons) + 1, ?, ?, ?, ?)
            ''', person_info
        )
        return self.__persons_max_index()

    @try_except_decorator
    def _insert_phone(self, phone_info: tuple) -> int:
        """
        Insert phone information to the DB
        :param phone_info - a row of data for Phones table EXCEPT id
        :return: inserted phone ID - success, (-1) - error
        """
        self.SQL_coursor.execute(
            '''
            INSERT INTO Phones
            VALUES ((SELECT MAX(id) from Phones) + 1, ?, ?, ?)
            ''', phone_info
        )
        return self.__phones_max_index()

    @try_except_decorator
    def _update_person(self, person_info: tuple) -> int:
        """
        Update person information to the DB
        :param person_info - a row of data for Persons table with new info; None if no changes are in need
        :return: 1 - success, (-1) - error
        """
        if person_info[1] is not None:
            self.SQL_coursor.execute(
                '''
                UPDATE Persons
                SET first_name = ?
                WHERE Persons.id = ?
                ''', (person_info[1], person_info[0])
            )
        if person_info[2] is not None:
            self.SQL_coursor.execute(
                '''
                UPDATE Persons
                SET last_name = ?
                WHERE Persons.id = ?
                ''', (person_info[2], person_info[0])
            )
        if person_info[3] is not None:
            self.SQL_coursor.execute(
                '''
                UPDATE Persons
                SET birthday = ?
                WHERE Persons.id = ?
                ''', (person_info[3], person_info[0])
            )
        if person_info[4] is not None:
            self.SQL_coursor.execute(
                '''
                UPDATE Persons
                SET is_favourite = ?
                WHERE Persons.id = ?
                ''', (person_info[4], person_info[0])
            )
        self._clean_db()
        return 1

    @try_except_decorator
    def _update_phone(self, phone_info: tuple) -> int:
        """
        Update phone information to the DB
        :param phone_info - a row of data for Phones table with new info; None if no changes are in need
        :return: 1 - success, (-1) - error
        """
        if phone_info[1] is not None:
            self.SQL_coursor.execute(
                '''
                UPDATE Phones
                SET owner = ?
                WHERE id = ?
                ''', (phone_info[1], phone_info[0])
            )
        if phone_info[2] is not None:
            self.SQL_coursor.execute(
                '''
                UPDATE Phones
                SET number = ?
                WHERE id = ?
                ''', (phone_info[2], phone_info[0])
            )
        if phone_info[3] is not None:
            self.SQL_coursor.execute(
                '''
                UPDATE Phones
                SET description = ?
                WHERE id = ?
                ''', (phone_info[3], phone_info[0])
            )
        self._clean_db()
        return 1

    @try_except_decorator
    def _delete_person(self, person_id) -> int:
        """
        Delete the person information by the column and its value
        + delete all phones of this person
        :param person_id: the person to delete
        :return: 1 - success, (-1) - error
        """
        self.SQL_coursor.execute(
            '''
            DELETE FROM Persons
            WHERE id = ?;
            
            ''', (person_id,)
        )
        self.SQL_coursor.execute(
            '''
            DELETE FROM Phones
            WHERE owner = ?
            ''', (person_id,)
        )
        return 1

    @try_except_decorator
    def _delete_phone(self, phone_id) -> int:
        """
        Delete the phone information by the column and its value

        :param phone_id: the phone to delete
        :return: 1 - success, (-1) - error
        """
        self.SQL_coursor.execute(
            '''
            DELETE FROM Phones
            WHERE id = ?
            ''', (phone_id,)
        )

        # if we deleted the only one phone number of a person we should delete a person too
        self._clean_db()
        return 1

    @try_except_decorator
    def _clean_db(self) -> int:
        """
        Delete persons without phone numbers from the table
        :return: 1 - success, (-1) - error
        """
        self.SQL_coursor.execute(
            '''
            DELETE FROM Persons
            WHERE Persons.id NOT IN (
            SELECT Persons.id FROM Persons, Phones
            WHERE Persons.id = Phones.owner
            )

            ''')
        return 1

    @try_except_decorator
    def __persons_length(self) -> int:
        """
        function to calculate the length of Persons table
        :return: number of rows in the table
        """
        self.SQL_coursor.execute(
            '''
            SELECT COUNT(id) from Persons
            '''
        )
        return int(self.SQL_coursor.fetchone()[0])

    @try_except_decorator
    def __phones_length(self) -> int:
        """
        function to calculate the length of Phones table
        :return: number of rows in the table
        """
        self.SQL_coursor.execute(
            '''
            SELECT COUNT(id) from Phones
            '''
        )
        return int(self.SQL_coursor.fetchone()[0])

    @try_except_decorator
    def __persons_max_index(self) -> int:
        """
        function to calculate new index for Persons table
        :return: new index
        """
        self.SQL_coursor.execute(
            '''
            SELECT MAX(id) from Persons
            '''
        )
        return int(self.SQL_coursor.fetchone()[0])

    @try_except_decorator
    def __phones_max_index(self) -> int:
        """
        function to calculate new index for Phones table
        :return: new index
        """
        self.SQL_coursor.execute(
            '''
            SELECT MAX(id) from Phones
            '''
        )
        return int(self.SQL_coursor.fetchone()[0])

    def _read_all_persons(self):
        return self.SQL_coursor.execute(
            '''
            SELECT * FROM Persons
            '''
        )

    def _read_all_phones(self):
        return self.SQL_coursor.execute(
            '''
            SELECT * FROM Phones
            '''
        )


class ContactsDBInterface(ContactsDB):
    """
    Interface for work with the Contacts Data Base
    """

    def __init__(self, db_name="phones_db.sqlite", auto_save=True):
        super().__init__(db_name=db_name, auto_save=auto_save)
        self.Format = FormatChecker()

        self.__selected_hor = 0
        self.__selected_ver = 0
        self.__max_hor = 0
        self.__max_ver = 0

        """
        mode = 0 - table screen
        mode = 1 - editor window
        mode = 2 - only input
        mode = 3 - Birthday screen
        """
        self.__mode = 0

        """
        edit_mode = 0 - search
        edit_mode = 1 - insert record
        edit_mode = 2 - insert phone
        edit_mode = 3 - update person
        edit_mode = 4 - update phone
        """
        self.__edit_mode = 0

        self.__table_headers = {
            "main":  ("ID", "First Name", "Last Name", "Birthday", "Favourite", "Phone", "Description", "Selection"),
            "search": ("ID", "First Name", "Last Name", "Birthday (day-month)", "Age", "Favourite", "Phone", "Description"),
            "new_record": ("First Name(*)", "Last Name(*)", "Birthday", "Favourite", "Phone(*)", "Description"),
            "new_phone": ("Phone(*)", "Description"),
            "update_person": ("First Name", "Last Name", "Birthday", "Favourite"),
            "update_phone": ("Owner ID", "Phone", "Description")
        }
        self.__format_headers = {
            'search': (self.Format.check_int, self.Format.check_name, self.Format.check_name,
                       self.Format.check_short_birthday, self.Format.check_age, self.Format.check_bool,
                       self.Format.check_number, self.Format.check_skip),
            'new_record': (self.Format.check_name, self.Format.check_name, self.Format.check_full_birthday,
                           self.Format.check_bool, self.Format.check_number, self.Format.check_skip),
            'new_phone': (self.Format.check_number, self.Format.check_skip),
            'update_person': (self.Format.check_name, self.Format.check_name, self.Format.check_full_birthday,
                              self.Format.check_bool),
            'update_phone': (self.Format.check_int, self.Format.check_number, self.Format.check_skip),

        }

        self.__editor_table = list()
        self.__last_table = list()

        self.__saved_search_params = dict()
        self.__input_search_params = ["" for x in range(len(self.__table_headers['search']))]

        self.__filled_params = tuple()

        self._exit_flag = False

        # Prints
        self.__name_to_print = "________________________________\n" \
                               "|  *   CONTACTS DATA BASE   *  |\n" \
                               "|______________________________|\n" \
                               "| made by Sapozhnikov Andrey   |\n" \
                               "|==============================|\n" \
                               " auto save ="
        self.__main_window_instructions = " [q] - to exit, [s] - to search, [c] - to clear search\n" \
                                          " [d] - to delete person, [shift]+[d] - to delete phone\n" \
                                          " [u] - to update person, [shift]+[u] - to update phone\n" \
                                          " [n] - to create record, [shift]+[n] - to insert phone\n" \
                                          " [b] - to see nearest birthdays\n" \
                                          " [shift] + [s] - to save Data Base\n" \
                                          " use arrows to navigate - [up], [down]\n"
        self.__search_window_instructions = " [q] - to save and exit, [c] - to clear search\n" \
                                            "    [e] then [ENTER] - to edit search param   \n" \
                                            "     use arrows to navigate - [<-], [->]    \n" \
                                            "\n SEARCH PARAMS: \n"
        self.__edit_window_instructions = " [q] - to save and exit                  \n" \
                                          " [e] then [ENTER] - to edit search param \n" \
                                          "   use arrows to navigate - [<-], [->] \n" \
                                          "\n EDIT VALUES: \n"
        self.__birthday_window_instructions = " [q] - to exit\n" \
                                              "\n NEAREST BIRTHDAYS (in 30 days): \n"
        self.__instructions_label = " Use keyboard to control the interface: "

    def start(self):
        """
        Function that enables interface communication
        Communication is build during inf. loop
        __del__ calls after the end of function
        :return: None
        """
        # arrows hot keys
        keyboard.add_hotkey('left', self.__arrow_left)
        keyboard.add_hotkey('right', self.__arrow_right)
        keyboard.add_hotkey('up', self.__arrow_up)
        keyboard.add_hotkey('down', self.__arrow_down)
        keyboard.add_hotkey('d', self.__delete_person_bt)
        keyboard.add_hotkey('shift + d', self.__delete_phone_bt)
        keyboard.add_hotkey('q', self.__exit)
        keyboard.add_hotkey('e', self.__get_input)
        keyboard.add_hotkey('s', self.__read_search_params)
        keyboard.add_hotkey('c', self.__clear_search_params)
        keyboard.add_hotkey('n', self.__read_edit_params, (1,))
        keyboard.add_hotkey('shift + n', self.__read_edit_params, (2,))
        keyboard.add_hotkey('u', self.__read_edit_params, (3,))
        keyboard.add_hotkey('shift + u', self.__read_edit_params, (4,))
        keyboard.add_hotkey('shift + s', self._save)
        keyboard.add_hotkey('b', self.__draw_birthday_window)

        self.__reload_main_window()

        while True:
            if self._exit_flag and self.__mode == 0:
                """
                Exit from the program
                """
                break
            if self._exit_flag and self.__mode == 1:
                """
                Exit from editor window
                """
                self._exit_flag = False
                if self.__edit_mode == 0:
                    # search mode
                    self.__input_search_params = self.__editor_table[1]
                    if self.__handle_search(self.__input_search_params) == -1:
                        continue
                else:
                    self.__filled_params = self.__editor_table[1]
                    if self.__edit_mode == 1:
                        # new record
                        if self.__handle_new_record(self.__filled_params) == -1:
                            continue
                    if self.__edit_mode == 2:
                        # new phone
                        if self.__handle_new_phone(self.__filled_params) == -1:
                            continue
                    if self.__edit_mode == 3:
                        # update person
                        if self.__handle_update_person(self.__filled_params) == -1:
                            continue
                    if self.__edit_mode == 4:
                        # update phone
                        if self.__handle_update_phone(self.__filled_params) == -1:
                            continue

                self.__mode = 0
                self.__reload_main_window()
            if self._exit_flag and self.__mode == 3:
                """
                Exit from Birthday window
                """
                self._exit_flag = False
                self.__mode = 0
                self.__reload_main_window()
            continue

        self.__del__()

    """
    Handlers
    """
    @try_except_decorator
    def __handle_search(self, input_params: tuple):
        """
        Makes a search request to the ContactsDB class based on user input
        :param input_params: params to handle for search
        :return: 1 - success, (-1) - error
        """
        conformity_list = ("person_ID", "first_name", "last_name", None, None, "is_favourite",
                           "phone_number", "phone_description")
        temp_dict = dict()
        for input_value_index in range(len(input_params)):
            if conformity_list[input_value_index] and input_params[input_value_index]:
                temp_dict[conformity_list[input_value_index]] = input_params[input_value_index]

        if input_params[3]:
            temp_dict['birthday'] = input_params[3] + '%'

        if input_params[4]:
            age = input_params[4].split('-')
            temp_dict['age_from'] = int(age[0])
            temp_dict['age_to'] = int(age[1]) if len(age) > 1 else int(age[0])

        self.__saved_search_params = temp_dict
        return 1

    @try_except_decorator
    def __handle_new_record(self, input_params: tuple):
        """
        Makes a record (person + phone) insert request to the ContactsDB class based on user input
        :param input_params: params to handle for insert
        :return: 1 - success, (-1) - error
        """
        input_list = list(input_params)
        if self._is_name_exist(input_list[0], input_list[1]):
            print(" *** ERROR *** : this Person name already exists")
            return -1
        if not (input_list[0] and input_list[1] and input_list[4]):
            print(" *** ERROR *** : make sure to fill necessary fields (*)")
            return -1

        new_person_data = tuple([x if x else None for x in input_list[:4]])
        new_phone_data = tuple([x if x else None for x in input_list[4:]])
        return self._insert_record(new_person_data, new_phone_data)

    @try_except_decorator
    def __handle_new_phone(self, input_params: tuple):
        """
        Makes a phone insert request to the ContactsDB class based on user input and selected person (record)
        :param input_params: params to handle for insert
        :return: 1 - success, (-1) - error
        """
        input_list = list(input_params)
        if not input_list[0]:
            print(" *** ERROR *** : make sure to fill necessary fields (*)")
            return -1
        owner_id = int(self.__last_table[self.__selected_hor][0])
        input_list.insert(0, owner_id)
        new_phone_data = tuple([x if x else None for x in input_list])
        return self._insert_phone(new_phone_data)

    @try_except_decorator
    def __handle_update_person(self, input_params: tuple):
        """
       Makes a person update request to the ContactsDB class based on user input and selected person (record)
       :param input_params: params to handle for insert
       :return: 1 - success, (-1) - error
       """
        input_list = list(input_params)
        if (input_list[0] or input_list[1]) and self._is_name_exist(str(input_list[0]), str(input_list[1])):
            print(" *** ERROR *** : such Person name already exists")
            return -1
        person_id = int(self.__last_table[self.__selected_hor][0])
        input_list.insert(0, person_id)
        new_person_data = tuple([x if x else None for x in input_list])
        return self._update_person(new_person_data)

    @try_except_decorator
    def __handle_update_phone(self, input_params: tuple):
        """
       Makes a person update request to the ContactsDB class based on user input and selected person (record)
       :param input_params: params to handle for insert
       :return: 1 - success, (-1) - error
       """
        input_list = list(input_params)
        if input_list[0] and len(self._read({'person_ID': input_list[0]})) == 0:
            print(" *** ERROR *** : such Person does not exist")
            return -1
        phone_id = int(self.__last_table[self.__selected_hor][5])
        input_list.insert(0, phone_id)
        new_phone_data = tuple([x if x else None for x in input_list])
        return self._update_phone(new_phone_data)

    """
    Hot key functions:
    """
    def __arrow_left(self):
        if self.__mode == 1:
            if self.__selected_ver > 0:
                self.__selected_ver -= 1

            self._clear_screen()
            self.__draw_editor_window()

    def __arrow_right(self):
        if self.__mode == 1:
            if self.__selected_ver < self.__max_ver:
                self.__selected_ver += 1

            self._clear_screen()
            self.__draw_editor_window()

    def __arrow_up(self):
        if self.__mode == 0:
            if self.__selected_hor > 0:
                self.__selected_hor -= 1
            self._clear_screen()
            self.__draw_main_window()

    def __arrow_down(self):
        if self.__mode == 0:
            if self.__selected_hor < self.__max_hor:
                self.__selected_hor += 1
            # self._clear_screen()
            self.__draw_main_window()

    @try_except_decorator
    def __delete_person_bt(self):
        """
        Hot key function for person delete
        :return: None
        """
        if self.__mode == 0 and len(self.__last_table) > 0:
            person_id = self.__last_table[self.__selected_hor][0]
            self._delete_person(person_id)
            self.__reload_main_window()
            return 1

    @try_except_decorator
    def __delete_phone_bt(self):
        """
        Hot key function for phone delete
        :return: None
        """
        if self.__mode == 0 and len(self.__last_table) > 0:
            phone_id = self.__last_table[self.__selected_hor][5]
            self._delete_phone(phone_id)
            self.__reload_main_window()
            return 1

    @try_except_decorator
    def __read_search_params(self, forced=False):
        """
        Hot key function for enabling the search edit screen
        :return: None
        """
        if self.__mode and not forced:
            return
        self.__mode = 1
        self.__edit_mode = 0
        self.__editor_table = [
            self.__table_headers['search'],
            tuple(self.__input_search_params)]

        self.__draw_editor_window()

    @try_except_decorator
    def __read_edit_params(self, edit_mode: int):
        """
        Hot key function for enabling the edit screen depends on edit_mode
        :param edit_mode: which edit screen want to enable
        :return: None
        """
        if self.__mode or (self.__mode != 1 and edit_mode != 1 and len(self.__last_table) == 0):
            return

        self.__mode = 1
        self.__edit_mode = edit_mode
        header_name = list(self.__format_headers.keys())[edit_mode]
        selected_row = list()
        if len(self.__last_table) > 0:
            selected_row = list(self.__last_table[self.__selected_hor] )
        before_update_values = list()
        if edit_mode == 3:
            before_update_values = selected_row[1:5]
        elif edit_mode == 4:
            before_update_values = selected_row[6:9]

        self.__editor_table = [
            self.__table_headers[header_name],
            tuple(['' for x in range(len(self.__table_headers[header_name]))]),
            before_update_values
        ]

        self.__draw_editor_window()

    @try_except_decorator
    def __clear_search_params(self):
        """
        Clear search params and reload main screen if it is displayed
        :return: None
        """
        self.__input_search_params = ["" for x in range(len(self.__table_headers['search']))]
        self.__saved_search_params = dict()

        if self.__mode == 0:
            self.__reload_main_window()
        elif self.__mode == 1:
            self.__read_search_params(forced=True)

    def __get_input(self):
        """
        Handle the input during edit mode
        :return:
        """
        if self.__mode == 1:
            self.__mode = 2
            input(" \nSystem: PRESS ENTER PLEASE\n")
            self.__draw_editor_window()
            cell = input("Your value: ")
            edit_name = list(self.__format_headers.keys())[self.__edit_mode]
            correct_cell = self.__format_headers[edit_name][self.__selected_ver](cell) if cell else ""
            if correct_cell == -1:
                self.__mode = 1
                return
            last_values = list(self.__editor_table[1])
            last_values[self.__selected_ver] = correct_cell
            self.__editor_table[1] = tuple(last_values)
            self.__draw_editor_window()
            self.__mode = 1

    """
    Draw functions
    """
    @staticmethod
    def _clear_screen():
        # for windows
        if name == 'nt':
            system('cls')
        # for mac and linux(here, os.name is 'posix')
        else:
            system('clear')

    @try_except_decorator
    def __draw_editor_window(self):
        """
        Draw the editor window
        :return: None
        """
        rows = self.__editor_table[:]
        self.__max_ver = len(rows[0]) - 1
        if self.__selected_ver > self.__max_ver:
            self.__selected_ver = self.__max_ver
        arrow = ["" for x in range(len(rows[0]))]
        arrow[self.__selected_ver] = "^\n|"

        self._clear_screen()
        print(self.__name_to_print, self._auto_save, "\n")
        print(self.__instructions_label)
        print(self.__search_window_instructions if self.__edit_mode == 0 else self.__edit_window_instructions)
        print(tb(rows + [tuple(arrow)], headers='firstrow', tablefmt='grid'))

    @try_except_decorator
    def __draw_main_window(self):
        """
        Draw the main window
        :return: None
        """
        self.__max_hor = len(self.__last_table) - 1
        if self.__selected_hor > self.__max_hor:
            self.__selected_hor = self.__max_hor
        if self.__selected_hor < 0:
            self.__selected_hor = 0

        rows = self.__last_table[:]
        values = list()
        for row_i in range(len(rows)):
            repeated_person = rows[row_i - 1][0] == rows[row_i][0] if row_i else False
            new_row = [rows[row_i][index] if not repeated_person else "" for index in range(4)]
            new_row.append("*" if not repeated_person and rows[row_i][4] else "")
            new_row.append(rows[row_i][7])
            new_row.append(rows[row_i][8])
            new_row.append("<--" if row_i == self.__selected_hor else "")
            values.append(tuple(new_row))

        self._clear_screen()
        print(self.__name_to_print, self._auto_save, "\n")
        print(self.__instructions_label)
        print(self.__main_window_instructions)
        print(tb([self.__table_headers['main']] + values, headers='firstrow', tablefmt='grid'))

    @try_except_decorator
    def __draw_birthday_window(self):
        self.__mode = 3
        result = self._read({"is_nearest_birthday": True})
        edited_result = [tuple(list(record)[1:4]) for record in result]
        headers = ("First name", "Last name", "Birthday")
        self._clear_screen()
        print(self.__name_to_print, self._auto_save, "\n")
        print(self.__instructions_label)
        print(self.__birthday_window_instructions)
        print(tb([headers] + edited_result, headers='firstrow', tablefmt='grid'))

    def __reload_main_window(self):
        """
        Refresh data by new request to the SQLite DB and draw reloaded screen
        :return: None
        """
        read_result = self._read(self.__saved_search_params)
        if read_result != -1:
            self.__last_table = read_result
        self.__draw_main_window()

    def __exit(self):
        """
        Sets the flag for exit - necessary for keyboard interaction
        :return: None
        """
        self._exit_flag = True


class FormatChecker:

    def __init__(self):
        pass

    @staticmethod
    def check_name(input_name: str):
        """
        Check the name format
        :param input_name: birthday you want to check
        :return: the correct name (str) - success, (-1) - input_name is fully incorrect
        """
        correct_name = input_name.strip()
        for x in correct_name.split(' '):
            if not (x.isalnum() or x == ''):
                print(" *** FORMAT ERROR *** : please use only alphabet, numeric symbols or SPACEs! ")
                return -1
        correct_name = correct_name[0].upper() + correct_name[1:]
        return correct_name

    @staticmethod
    def check_number(input_number: str):
        """
        Check the number format
        :param input_number: number you want to check
        :return: the correct number (str) - success, (-1) - input_number is fully incorrect
        """
        correct_number = "" + input_number.strip()
        while True:
            if len(correct_number) not in (11, 12):
                break

            if len(correct_number) == 12:
                if correct_number[:2] == "+7":
                    correct_number = "8" + correct_number[2:]
                else:
                    break

            if not correct_number.isnumeric():
                break

            return correct_number

        print(" *** FORMAT ERROR *** : please enter the correct phone number (11 digits or 12 digits with '+' start)! ")
        return -1

    def check_full_birthday(self, input_birthday: str):
        return self.__check_birthday(input_birthday)

    def check_short_birthday(self, input_birthday: str):
        return self.__check_birthday(input_birthday, full_date=False)

    @staticmethod
    def __check_birthday(input_birthday: str, full_date=True):
        """
        Check the birthday format
        :param input_birthday: birthday you want to check
        :param full_date: True - {dd-mm-yyyy}, False - {dd-mm}
        :return: the correct birthday (str) - success, (-1) - input_birthday is fully incorrect
        """
        correct_birthday = input_birthday.strip()
        try:
            birthday_format = '%d-%m-%Y' if full_date else '%d-%m'
            datetime.datetime.strptime(correct_birthday, birthday_format)
            return correct_birthday
        except Exception as e:
            format_message = "dd-mm-yyyy" if full_date else "dd-mm"
            print(" *** FORMAT ERROR *** : please enter birth date in a format " + format_message)
            return -1

    @staticmethod
    def check_int(input_integer: str):
        """
        Check the string is an integer number
        :param input_integer: string number you want to check
        :return: integer number (int) - success, (-1) - input_integer is fully incorrect
        """
        correct_integer = input_integer.strip()
        try:
            correct_integer = int(correct_integer)
            return correct_integer
        except Exception as e:
            print(" *** FORMAT ERROR *** : please enter the integer number! ")
            return -1

    @staticmethod
    def check_bool(input_bool: str):
        """
        Check the string is an bool value
        :param input_bool: string bool you want to check
        :return: True/False (bool) - success, (-1) - input_integer is fully incorrect
        """
        correct_bool = input_bool.strip()
        try:
            if correct_bool == '0':
                return False
            correct_bool = bool(correct_bool)
            return correct_bool
        except Exception as e:
            print(" *** FORMAT ERROR *** : please enter something for True or left empty for False! ")
            return -1

    @staticmethod
    def check_age(input_age: str):
        """
        Check if the input string can be converted to the age interval
        :param input_age: age as string
        :return: 1 - success, (-1) - input_age is fully incorrect
        """
        correct_age = input_age.strip()
        splitted = correct_age.split('-')
        while True:
            if len(splitted) > 2:
                break
            if len(splitted) == 2 and splitted[0] > splitted[1]:
                break
            for x in splitted:
                if not x.isnumeric():
                    break
            else:
                return correct_age
            break

        print(" *** FORMAT ERROR *** : please enter one age as an integer number\n"
              "or an age interval in format {age1}-{age2} where age1 <= age2 ! ")
        return -1

    @staticmethod
    def check_skip(input_value):
        return input_value


"""
Just create a class copy and call start() function
"""
ui = ContactsDBInterface(auto_save=False)
ui.start()
