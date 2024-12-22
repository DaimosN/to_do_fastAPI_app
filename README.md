Запуск локально
unicorn main:app --reload
Сборка докер образа
docker build -t ta <имя_образа>:<имя_тега>
Запуск контейра из образа
docker run -d -p 8000:80 -v todo_data:/app/data <имя_образа>
