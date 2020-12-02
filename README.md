# Phone-DB-HSE-Lab
phonebook app made by Sapozhnikov Andrey

<br />Code overview (video): 
<br />https://www.loom.com/share/619d365e8d3b4d76b826947aa9479ba5?sharedAppSource=personal_library
<br />Interface overview (video):
<br />https://www.loom.com/share/0b973c8c4a434dc289b328db604bfdce?sharedAppSource=personal_library
<br />Contacts: 
<br />@sapozhnikovandrey - Telegram
<br />amsapozhnikov@edu.hse.ru / sand.developer@gmail.com - Mail
### Stack: Python, SQLite, CLI, python.Keyboard
## Особенности:
* Пользователю доступен графиеский интерфейс (в терминале) и возможность управления им с помощью горячих клавиш
* Реализована реляционная БД на основе SQLite. БД содержит 2 таблицы Persons и Phones, связанные отношением one-to-many т.е. один человек может иметь множество телефонов. Весь поиск и фильтрация выполнены средством SQL запросов (за исключением подсчета возраста).
* Работа приложения разделена на 2 класс ContactsDB и ContactsDBInterface(ContactsDB) с наследованием. Первый класс отвечает за работу с БД и SQL запросами, второй за отрисовку интерфейса, обработку входящих данных от пользователя и вызов функций класса ContactsDB.
* Класс FormatChecker содержит функции для проверки формата вводимых пользователем данных
* Код самодокументируемый - каждый класс и функция имеют док-стринг с полным описанием функции параметров и выходных данных
* Соблюден Python Code Style
* Большинство функций возвращают резульат работы: 1 или возвращаемый набор данных в случае успеха, -1 в случае возникновения ошибки
## Возможности:
* Поиск записей по любому из существующих полей и их комбинаций, а также по возрасту (конкретное число или заданный промежуток)
* Сохранение параметров поиска, а также возможность сбросить их все сразу
* Выбор любой записи для дальнейшей работы с ней посредством гибкого поиска и нажатия стрелок
* Изменение данных человека
* Изменение данных телефонного номера
* Добавления новой записи (человек + номер телефона)
* Добавление безграничного количества телефонов человеку
* Удаление человека (+ все его номера)
* Удаление номера телефона (если он у человека последний, то и запись человека удаляется)
* Просмотр записей людей с днем рождения в ближайшие 30 дней
* Все возможные действия указаны выше таблицы в виде описания горячих клавиш
* Отдельные окна для отображения БД и редактирования
### Для преподавателя: 
были реализованы все базовые и дополнительные функции, указанные в задании. Большинство возможностей, таких как удаление записи по имени и т.д. реализованы средством ввода гибких параметров поиска и последующим выбором определенной записи. Поменялся лишь формат работы с данными - функционал тот же, что и в задании
<img src=BD%20Structure.jpg height=400>
<img src=screenshots/main%20window.jpg height=400>
